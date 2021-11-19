"""Item crud client."""

import json
import logging
import operator
from datetime import datetime
from typing import List, Optional, Set, Type, Union
from urllib.parse import urlencode, urljoin

import attr
from stac_fastapi.types.core import AsyncBaseCoreClient, BaseCoreClient
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes, Provider

from mqs.client import request_all, request_collection
from mqs.types.search import MqsSTACSearch
from mqs import serializers

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
        for provider, collection in response.items():
            return self.collection_serializer.response_to_stac(
                stac_collection=collection.json(),
                base_url=base_url,
                provider_id=provider,
            )

    # TODO: serialize
    def item_collection(self, **kwargs) -> ItemCollection:
        """Read an item collection from the database."""
        response = request_all(fastapi_request=kwargs["request"])
        # return ItemCollection(json.dumps([ob.json() for ob in response]))
        return ItemCollection(response[0].json())

    # TODO: serialize
    def get_item(self, **kwargs) -> Item:
        """Get item by id."""
        response = request_all(fastapi_request=kwargs["request"])
        return Item(response[0].json())

    # TODO: serialize, develop
    def get_search(self, **kwargs) -> ItemCollection:
        """GET search catalog."""
        response = request_all(fastapi_request=kwargs["request"])
        return ItemCollection(response[0].json())

    # TODO: serialize, develop
    def post_search(self, search_request: MqsSTACSearch, **kwargs) -> ItemCollection:
        """POST search catalog."""
        response = request_all(fastapi_request=kwargs["request"])
        return ItemCollection(response[0].json())
