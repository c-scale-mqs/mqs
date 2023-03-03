"""Item crud client."""

import json
import logging
import operator
from datetime import datetime
from operator import attrgetter, itemgetter
from typing import List, Optional, Set, Type, Union
from urllib.parse import urlencode, urljoin

import attr
from fastapi import HTTPException
from pydantic import ValidationError
from stac_fastapi.types.core import AsyncBaseCoreClient, BaseCoreClient
from stac_fastapi.types.stac import (
    Collection,
    Collections,
    Item,
    ItemCollection,
    LandingPage,
)
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes, Provider

from mqs import serializers
from mqs.client import request_all, request_collection, request_search
from mqs.config import settings
from mqs.types.search import MqsSTACSearch

logger = logging.getLogger(__name__)

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

        # Privacy Policy URL
        lp["links"].append(
            {
                "rel": "privacy-policy",
                "type": MimeTypes.html.value,
                "title": "EODC Privacy Policy",
                "href": "https://eodc.eu/dataprotection",
            }
        )

        return lp

    def all_collections(self, **kwargs) -> Collections:
        """Read all collections from the data providers."""
        response = request_all(fastapi_request=kwargs["request"])
        base_url = str(kwargs["request"].base_url)
        serialized_collections = []
        for provider, collections in response.items():
            for collection in collections.json()["collections"]:
                serialized_collections.append(
                    self.collection_serializer.response_to_stac(
                        stac_collection=collection,
                        base_url=base_url,
                        provider_id=provider,
                    )
                )

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
        collection_list = Collections(
            collections=serialized_collections or [], links=links
        )
        return collection_list

    def get_collection(self, **kwargs) -> Collection:
        """Read all collections from the data providers."""
        base_url = str(kwargs["request"].base_url)
        response = request_collection(fastapi_request=kwargs["request"])
        for provider, collection in response.items():  # only one collection is returned
            if collection.status_code == 404:
                raise HTTPException(status_code=404, detail="Collection not found")
            return self.collection_serializer.response_to_stac(
                stac_collection=collection.json(),
                base_url=base_url,
                provider_id=provider,
            )

    def item_collection(
        self, collection_id: str, limit: int = 10, **kwargs
    ) -> ItemCollection:
        """Read an item collection from the data providers."""
        response = request_collection(fastapi_request=kwargs["request"])
        base_url = str(kwargs["request"].base_url)
        serialized_items = []
        for (
            provider,
            itemcollection,
        ) in response.items():  # only one item collection is returned
            for feature in itemcollection.json()["features"]:
                serialized_items.append(
                    self.item_serializer.response_to_stac(
                        stac_item=feature,
                        base_url=base_url,
                        provider_id=provider,
                    )
                )
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

            context_obj = (
                None
                if "context" not in itemcollection.json().keys()
                or not self.extension_is_enabled("ContextExtension")
                else itemcollection.json()["context"]
            )

            return ItemCollection(
                type="FeatureCollection",
                features=serialized_items,
                links=links,
                context=context_obj,
            )

    def get_item(self, **kwargs) -> Item:
        """Read an item from the data providers."""
        response = request_collection(fastapi_request=kwargs["request"])
        base_url = str(kwargs["request"].base_url)
        for provider, item in response.items():  # only one item is returned
            return self.item_serializer.response_to_stac(
                stac_item=item.json(),
                base_url=base_url,
                provider_id=provider,
            )

    def get_search(
        self,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[List[NumType]] = None,
        datetime: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = 10,
        query: Optional[str] = None,
        token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        **kwargs,
    ) -> ItemCollection:
        """GET search catalog."""
        # Parse request parameters

        base_args = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "limit": limit,
            "token": token,
            "query": json.loads(query) if query else query,
        }

        if datetime:
            base_args["datetime"] = datetime

        if sortby:
            # https://github.com/radiantearth/stac-api-spec/tree/master/item-search#sort
            sort_param = []
            for s in sortby:
                sort = "+" + s if not s[0] in ("+", "-") else s
                sort_param.append(
                    {
                        "field": sort[1:],
                        "direction": "asc" if sort[0] == "+" else "desc",
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

        # Do the request
        # validate model
        try:
            search_request = MqsSTACSearch(**base_args)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid parameters provided")

        # convert GET to POST request
        resp = self.post_search(search_request, request=kwargs["request"])

        # Pagination
        page_links = []
        for link in resp["links"]:
            if link["rel"] == Relations.next or link["rel"] == Relations.previous:
                query_params = dict(kwargs["request"].query_params)
                if link["body"] and link["merge"]:
                    query_params.update(
                        {k: v for k, v in link["body"].items() if k == "token"}
                    )
                link["method"] = "GET"
                link["href"] = "?".join(
                    [f"{kwargs['request'].base_url}search?{urlencode(query_params)}"]
                )
                link["body"] = None
                link["merge"] = False
                page_links.append(link)
            else:
                page_links.append(link)
        resp["links"] = page_links

        return resp

    def post_search(self, search_request: MqsSTACSearch, **kwargs) -> ItemCollection:
        """POST search catalog."""
        # remove data provider from collection ids
        collections_stac = []
        if search_request.collections:
            for c in search_request.collections:
                if settings.collection_delimiter in c:
                    collections_stac.append(c.split(settings.collection_delimiter)[1])
                else:
                    collections_stac.append(c)
        search_request.collections = collections_stac

        # simplify request to core functions for now, i.e.,
        # - ignore query, sortby, fields, (filter?), token
        kwargs["request"]._json = {
            k: v
            for k, v in search_request.dict().items()
            if v
            and k in ("collections", "ids", "bbox", "datetime", "intersects", "limit")
        }

        response = request_search(fastapi_request=kwargs["request"])

        base_url = str(kwargs["request"].base_url)

        serialized_items = []
        total_count = 0
        for provider, itemcollection in response.items():
            if not "features" in itemcollection.json():
                continue
            returned = 0
            for feature in itemcollection.json()["features"]:
                serialized_items.append(
                    self.item_serializer.response_to_stac(
                        stac_item=feature,
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
            for sort in search_request.sortby:
                sort_param.append(
                    (sort.field, True if sort.direction == "desc" else False)
                )
        else:
            # Default sort is date
            sort_param.append(("properties.datetime", True))
        sort_param.reverse()
        for sort in sort_param:
            if sort[0].split(".")[0] == "properties":
                serialized_items.sort(
                    key=lambda e: e["properties"][sort[0].split(".")[1]],
                    reverse=sort[1],
                )
            else:
                serialized_items.sort(key=lambda e: e[sort[0]], reverse=sort[1])

        # Pagination
        token = 0
        if search_request.token:
            try:
                token = int(search_request.token)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Non-integer tokens not supported, use page numbers.",
                )

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
        except IndexError:
            raise HTTPException(
                status_code=404,
                detail="Page not found.",
            )

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
                    "href": f"{kwargs['request'].base_url}search",
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
                    "href": f"{kwargs['request'].base_url}search",
                    "method": "POST",
                    "body": body,
                    "merge": True,
                }
            )

        return ItemCollection(
            type="FeatureCollection",
            features=results,
            links=links,
            context=context_obj,
        )
