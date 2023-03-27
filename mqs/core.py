"""Item crud client."""

import logging
import re
from datetime import datetime as pydatetime
from typing import List, Optional, Type, Union
from urllib.parse import unquote_plus, urlencode, urljoin

import attr
import orjson
from fastapi import HTTPException
from pydantic import ValidationError
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_text import parse as parse_cql2_text
from shapely import box
from stac_fastapi.pgstac.utils import filter_fields
from stac_fastapi.types.core import BaseCoreClient
from stac_fastapi.types.stac import (
    Collection,
    Collections,
    Item,
    ItemCollection,
    LandingPage,
)
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes

from mqs import serializers
from mqs.client import (
    ResponseDictType,
    request_all,
    request_collection,
    request_search_post,
    request_search_get,
)
from mqs.config import settings
from mqs.types.search import MqsSTACSearch
from mqs.utils import (
    filter_spatially,
    filter_temporally,
    filter_collections,
    filter_ids,
    fix_duplicate_slashes,
    make_valid_collection,
    make_valid_item,
    remove_provider_from_collection_ids,
)

logger = logging.getLogger(__name__)
logger.setLevel(20)

NumType = Union[float, int]

# TODO: use async client
@attr.s
class CoreCrudClient(BaseCoreClient):
    """Client for core endpoints defined by stac."""

    item_serializer: Type[serializers.Serializer] = attr.ib(
        default=serializers.ItemSerializer
    )
    collection_serializer: Type[serializers.Serializer] = attr.ib(
        default=serializers.CollectionSerializer
    )

    def landing_page(self, **kwargs) -> LandingPage:
        lp = super().landing_page(**kwargs)

        # Add custom links
        lp["links"] += settings.links

        return lp

    def all_collections(self, **kwargs) -> Collections:
        """Read all collections from the data providers."""
        response = request_all(fastapi_request=kwargs["request"])
        base_url = fix_duplicate_slashes(str(kwargs["request"].base_url))
        serialized_collections = []
        n_returned = 0
        for provider, collections in response.items():
            try:
                provider_collections = collections.json()["collections"]
            except (AttributeError, KeyError) as ex:
                logger.warning(
                    "Could not fetch collections from data provider %s: %s",
                    provider,
                    ex,
                )
                continue
            for collection in provider_collections:
                mod_collection = make_valid_collection(collection)
                if not mod_collection:
                    logger.warning(
                        "Could not validate STAC Collection (skipping): %s, %s",
                        provider,
                        collection,
                    )
                    continue
                collection = mod_collection
                serialized_collections.append(
                    self.collection_serializer.response_to_stac(
                        stac_collection=collection,
                        base_url=base_url,
                        provider_id=provider,
                    )
                )
                n_returned += 1

        links = [
            {
                "rel": Relations.root.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.parent.value,
                "type": MimeTypes.json,
                "href": base_url,
            },
            {
                "rel": Relations.self.value,
                "type": MimeTypes.json,
                "href": urljoin(base_url, "collections"),
            },
        ]

        # Clean links
        clean_links = []
        for link in links:
            clean = {}
            for k, v in link.items():
                if k == "href":
                    clean[k] = fix_duplicate_slashes(v)
                else:
                    clean[k] = v
            clean_links.append(clean)

        if self.extension_is_enabled("ContextExtension"):
            collection_list = Collections(
                collections=serialized_collections or [],
                links=clean_links,
                context={"returned": n_returned},
            )
        else:
            collection_list = Collections(
                collections=serialized_collections or [],
                links=links,
            )

        return collection_list

    def get_collection(self, **kwargs) -> Collection:
        """Read a specific collection from a data provider."""
        base_url = fix_duplicate_slashes(str(kwargs["request"].base_url))
        response = request_collection(fastapi_request=kwargs["request"])
        for provider, collection in response.items():  # only one collection is returned
            mod_collection = make_valid_collection(collection.json())
            if not mod_collection:
                logger.warning(
                    "Could not validate STAC Collection: %s, %s",
                    provider,
                    collection,
                )
                raise HTTPException(
                    status_code=500, detail="Cannot validate STAC Collection."
                )
            collection = mod_collection

            return self.collection_serializer.response_to_stac(
                stac_collection=collection,
                base_url=base_url,
                provider_id=provider,
            )

    def item_collection(
        self,
        collection_id: str,
        limit: int = 10,
        bbox: Optional[List[NumType]] = None,
        datetime: Optional[Union[str, pydatetime]] = None,
        **kwargs,
    ) -> ItemCollection:
        """Read an item collection from the data providers."""

        base_args = {
            "bbox": bbox,
            "limit": limit,
            "datetime": datetime,
        }

        # Remove None values from dict
        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        # validate model
        try:
            search_request = self.post_request_model(**clean)
        except ValidationError as ex:
            logger.warning(ex)
            raise HTTPException(
                status_code=400, detail="Invalid parameters provided"
            ) from ex

        # Do the request
        request = kwargs["request"]
        base_url = fix_duplicate_slashes(str(request.base_url))
        response = request_collection(fastapi_request=request)

        # Filter and serialize
        filter_geom = None
        if search_request.bbox:
            filter_geom = box(*search_request.bbox)

        filter_start_date = None
        filter_end_date = None
        if search_request.datetime:
            filter_start_date = search_request.start_date
            filter_end_date = search_request.end_date

        serialized_items = []

        for (
            provider,
            itemcollection,
        ) in response.items():  # only one item collection is returned

            if not "features" in itemcollection.json():
                continue

            returned = 0
            for feature in itemcollection.json()["features"]:

                mod_feature = make_valid_item(feature)

                if not mod_feature:
                    continue

                if not filter_temporally(
                    mod_feature, start_date=filter_start_date, end_date=filter_end_date
                ):
                    continue

                if not filter_spatially(mod_feature, filter_geom):
                    continue

                serialized_items.append(
                    self.item_serializer.response_to_stac(
                        stac_item=mod_feature,
                        base_url=base_url,
                        provider_id=provider,
                    )
                )

            stac_links = []
            if "links" in itemcollection.json():
                stac_links = itemcollection.json()["links"]

            next = (
                True
                if any([l["rel"] in (Relations.next.value, "next") for l in stac_links])
                else False
            )

            previous = (
                True
                if any(
                    [l["rel"] in (Relations.previous.value, "prev") for l in stac_links]
                )
                else False
            )

            links = []

            if next:
                next_href = [
                    l["href"]
                    for l in stac_links
                    if l["rel"] in (Relations.next.value, "next")
                ][0]
                next_query = next_href.split("?")[1]
                links.append(
                    {
                        "rel": Relations.next.value,
                        "type": "application/geo+json",
                        "href": "?".join(
                            [
                                f"{kwargs['request'].base_url}collections/{collection_id}/items",
                                next_query,
                            ]
                        ),
                        "method": "GET",
                    }
                )

            if previous:
                previous_href = [
                    l["href"]
                    for l in stac_links
                    if l["rel"] in (Relations.previous.value, "prev")
                ][0]
                previous_query = previous_href.split("?")[1]
                links.append(
                    {
                        "rel": Relations.previous.value,
                        "type": "application/geo+json",
                        "href": "?".join(
                            [
                                f"{kwargs['request'].base_url}collections/{collection_id}/items",
                                previous_query,
                            ]
                        ),
                        "method": "GET",
                    }
                )

            # Clean links
            clean_links = []
            for link in links:
                clean = {}
                for k, v in link.items():
                    if k == "href":
                        clean[k] = fix_duplicate_slashes(v)
                    else:
                        clean[k] = v
                clean_links.append(clean)

            context_obj = (
                None
                if "context" not in itemcollection.json().keys()
                or not self.extension_is_enabled("ContextExtension")
                else itemcollection.json()["context"]
            )

            return ItemCollection(
                type="FeatureCollection",
                features=serialized_items,
                links=clean_links,
                context=context_obj,
            )

    def get_item(self, **kwargs) -> Item:
        """Read an item from the data providers."""
        response = request_collection(fastapi_request=kwargs["request"])
        base_url = fix_duplicate_slashes(str(kwargs["request"].base_url))
        for provider, item in response.items():  # only one item is returned
            mod_feature = make_valid_item(item.json())
            if not mod_feature:
                logger.warning(
                    "Could not validate STAC Item (skipping): %s, %s",
                    provider,
                    item,
                )
                raise HTTPException(
                    status_code=500, detail="Cannot validate STAC Item."
                )
            feature = mod_feature
            return self.item_serializer.response_to_stac(
                stac_item=feature,
                base_url=base_url,
                provider_id=provider,
            )

    def get_search(
        self,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[List[NumType]] = None,
        datetime: Optional[Union[str, pydatetime]] = None,
        limit: Optional[int] = 10,
        query: Optional[str] = None,
        token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        filter: Optional[str] = None,
        filter_lang: Optional[str] = None,
        intersects: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        """GET search catalog."""
        # Parse request parameters

        # only bbox or intersects must be provided
        if bbox and intersects:
            raise HTTPException(
                status_code=400, detail="Only bbox or intersects should be specified."
            )

        # get request
        request = kwargs["request"]
        query_params = request.query_params

        # Kludgy fix because using factory does not allow alias for filter-lang
        if filter_lang is None:
            match = re.search(
                r"filter-lang=([a-z0-9-]+)", str(query_params), re.IGNORECASE
            )
            if match:
                filter_lang = match.group(1)

        # Parse request parameters
        base_args = {
            "collections": remove_provider_from_collection_ids(collections),
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
            "query": orjson.loads(unquote_plus(query)) if query else query,
        }

        if filter:
            if filter_lang == "cql2-text":
                ast = parse_cql2_text(filter)
                base_args["filter"] = orjson.loads(to_cql2(ast))
                base_args["filter-lang"] = "cql2-json"

        if datetime:
            base_args["datetime"] = datetime

        if intersects:
            base_args["intersects"] = orjson.loads(unquote_plus(intersects))

        if sortby:
            # https://github.com/radiantearth/stac-spec/tree/master/api-spec/extensions/sort#http-get-or-post-form
            sort_param = []
            for sort in sortby:
                sortparts = re.match(r"^([+-]?)(.*)$", sort)
                if sortparts:
                    sort_param.append(
                        {
                            "field": sortparts.group(2).strip(),
                            "direction": "desc" if sortparts.group(1) == "-" else "asc",
                        }
                    )
            base_args["sortby"] = sort_param

        if fields:
            includes = set()
            excludes = set()
            for field in fields:
                if field[0] == "-":
                    excludes.add(field[1:])
                elif field[0] == "+":
                    includes.add(field[1:])
                else:
                    includes.add(field)
            base_args["fields"] = {"include": includes, "exclude": excludes}

        # Remove None values from dict
        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        # validate model
        try:
            search_request = self.post_request_model(**clean)
        except ValidationError as ex:
            logger.warning(ex)
            raise HTTPException(
                status_code=400, detail="Invalid parameters provided"
            ) from ex

        # Do the request
        response = request_search_get(fastapi_request=kwargs["request"])

        base_url = fix_duplicate_slashes(str(kwargs["request"].base_url))

        resp = self._parse_search(
            response=response, base_url=base_url, search_request=search_request
        )

        # Pagination
        page_links = []
        if "links" in resp.keys():
            for link in resp["links"]:
                if link["rel"] == Relations.next or link["rel"] == Relations.previous:
                    query_params = dict(query_params)
                    if link["body"] and link["merge"]:
                        query_params.update(
                            {k: v for k, v in link["body"].items() if k == "token"}
                        )

                    link["method"] = "GET"
                    link["href"] = "?".join(
                        [f"{base_url}search?{urlencode(query_params)}"]
                    )
                    link["body"] = None
                    link["merge"] = False
                    page_links.append(link)
                else:
                    page_links.append(link)

        # Clean links
        clean_links = []
        for link in page_links:
            clean = {}
            for k, v in link.items():
                if k == "href":
                    clean[k] = fix_duplicate_slashes(v)
                else:
                    clean[k] = v
            clean_links.append(clean)

        resp["links"] = clean_links

        return resp

    def post_search(self, search_request: MqsSTACSearch, **kwargs) -> ItemCollection:
        """POST search catalog."""
        search_request.collections = remove_provider_from_collection_ids(
            search_request.collections
        )

        response = request_search_post(fastapi_request=kwargs["request"])

        base_url = fix_duplicate_slashes(str(kwargs["request"].base_url))

        return self._parse_search(
            response=response, base_url=base_url, search_request=search_request
        )

    def _parse_search(
        self,
        response: ResponseDictType,
        base_url: str,
        search_request: MqsSTACSearch,
        **kwargs,
    ) -> ItemCollection:

        serialized_items = []
        total_count = 0

        filter_geom = None
        if search_request.intersects:
            filter_geom = search_request.intersects
        elif search_request.bbox:
            filter_geom = box(*search_request.bbox)

        filter_start_date = None
        filter_end_date = None
        if search_request.datetime:
            filter_start_date = search_request.start_date
            filter_end_date = search_request.end_date

        for provider, itemcollection in response.items():
            if not "features" in itemcollection.json():
                continue
            returned = 0
            for feature in itemcollection.json()["features"]:
                mod_feature = make_valid_item(feature)
                if not mod_feature:
                    continue
                if not filter_temporally(
                    mod_feature, start_date=filter_start_date, end_date=filter_end_date
                ):
                    continue
                if not filter_spatially(mod_feature, filter_geom):
                    continue
                if not filter_collections(mod_feature, search_request.collections):
                    continue
                if not filter_ids(mod_feature, search_request.ids):
                    continue
                serialized_items.append(
                    self.item_serializer.response_to_stac(
                        stac_item=mod_feature,
                        base_url=base_url,
                        provider_id=provider,
                    )
                )
                returned += 1
            if "numberMatched" in itemcollection.json().keys():
                total_count += itemcollection.json()["numberMatched"]
            elif "context" in itemcollection.json().keys():
                if "matched" in itemcollection.json()["context"].keys():
                    total_count += itemcollection.json()["context"]["matched"]
                else:
                    total_count += returned
            else:
                total_count += returned

        # Sorting
        sort_param = []
        if search_request.sortby:
            for sort_val in search_request.sortby:
                sort_param.append(
                    (sort_val.field, True if sort_val.direction == "desc" else False)
                )
        else:
            # Default sort is date
            sort_param.append(("properties.datetime", True))
        sort_param.reverse()

        for sort_val in sort_param:
            if sort_val[0].split(".")[0] == "properties":
                serialized_items.sort(
                    key=lambda e: e["properties"][sort_val[0].split(".")[1]],
                    reverse=sort_val[1],
                )
            else:
                serialized_items.sort(key=lambda e: e[sort_val[0]], reverse=sort_val[1])

        # Pagination
        token = 0
        if search_request.token:
            try:
                token = int(search_request.token)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Non-integer tokens not supported, use page numbers.",
                ) from exc

        paginated_results = []
        for offset in range(0, len(serialized_items), search_request.limit):
            ix1 = offset
            ix2 = (
                search_request.limit + offset
                if search_request.limit is not None
                else None
            )
            paginated_results.append(serialized_items[ix1:ix2])

        try:
            results = paginated_results[token]
        except IndexError as exc:
            raise HTTPException(status_code=404, detail="Page not found.") from exc

        if search_request.fields:
            cleaned_features: List[Item] = []
            for feature in results:
                clean_feature = feature
                try:
                    _clean_feature = filter_fields(
                        feature,
                        search_request.fields.include,
                        search_request.fields.exclude,
                    )
                except Exception as exc:
                    logger.warning("Cannot filter fields!")
                    logger.warning(exc)
                else:
                    clean_feature = _clean_feature
                cleaned_features.append(clean_feature)
            results = cleaned_features

        context_obj = None
        if self.extension_is_enabled("ContextExtension"):
            context_obj = {
                "returned": len(results),
                "limit": search_request.limit,
                # "matched": total_count,             # removed for now, might be misleading if not real total count is returned
            }

        # Links
        previous_page = None if token - 1 < 0 else token - 1
        next_page = None if token + 1 >= len(paginated_results) else token + 1

        links = []
        body = {
            k: v for k, v in search_request.dict().items() if v and not k == "token"
        }
        if next_page is not None:
            body["token"] = str(next_page)
            links.append(
                {
                    "rel": Relations.next.value,
                    "type": "application/geo+json",
                    "href": f"{base_url}search",
                    "method": "POST",
                    "body": body,
                    "merge": True,
                }
            )
        if previous_page is not None:
            body["token"] = str(previous_page)
            links.append(
                {
                    "rel": Relations.previous.value,
                    "type": "application/geo+json",
                    "href": f"{base_url}search",
                    "method": "POST",
                    "body": body,
                    "merge": True,
                }
            )

        # Clean links
        clean_links = []
        for link in links:
            clean = {}
            for k, v in link.items():
                if k == "href":
                    clean[k] = fix_duplicate_slashes(v)
                else:
                    clean[k] = v
            clean_links.append(clean)

        return ItemCollection(
            type="FeatureCollection",
            features=results,
            links=clean_links,
            context=context_obj,
        )
