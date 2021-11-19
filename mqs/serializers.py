"""Serializers."""
import abc
import json
from datetime import datetime
from typing import TypedDict

import attr
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.config import Settings
from stac_fastapi.types.links import CollectionLinks, ItemLinks, resolve_links
from stac_pydantic.shared import DATETIME_RFC339


@attr.s  # type:ignore
class Serializer(abc.ABC):
    """Defines serialization methods between the API and the data model."""

    @classmethod
    @abc.abstractmethod
    def response_to_stac(cls, base_url: str, provider_id: str) -> TypedDict:
        pass


class CollectionSerializer(Serializer):
    """Serialization methods for STAC collections."""

    @classmethod
    def response_to_stac(
        cls, stac_collection: stac_types.Collection, base_url: str, provider_id: str
    ) -> TypedDict:
        """Transform (external) stac collection to cscale stac collection."""
        collection_links = CollectionLinks(
            collection_id=stac_collection["id"], base_url=base_url
        ).create_links()

        stac_links = stac_collection["links"]
        if stac_links:
            collection_links += resolve_links(stac_links, base_url)

        stac_extensions = stac_collection["stac_extensions"] or []

        return stac_types.Collection(
            type="Collection",
            id="|".join([provider_id, stac_collection["id"]]),
            stac_extensions=stac_extensions,
            stac_version=stac_collection["stac_version"],
            title=stac_collection["title"],
            description=stac_collection["description"],
            keywords=stac_collection["keywords"],
            license=stac_collection["license"],
            providers=stac_collection["providers"],
            summaries=stac_collection["summaries"],
            extent=stac_collection["extent"],
            links=collection_links,
        )


class ItemSerializer(Serializer):
    """Serialization methods for STAC items."""

    pass
