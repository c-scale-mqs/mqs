"""Serializers."""
import abc
from typing import TypedDict

import attr
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.links import CollectionLinks, ItemLinks, resolve_links

from mqs.config import settings


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
            collection_id=settings.collection_delimiter.join(
                [provider_id, stac_collection["id"]]
            ),
            base_url=base_url,
        ).create_links()

        stac_links = (
            [] if "links" not in stac_collection.keys() else stac_collection["links"]
        )

        if stac_links:
            no_items_links = [l for l in stac_links if not l["rel"] == "items"]
            collection_links += resolve_links(no_items_links, base_url)

        stac_extensions = (
            []
            if "stac_extensions" not in stac_collection.keys()
            else stac_collection["stac_extensions"]
        )

        keywords = (
            []
            if "keywords" not in stac_collection.keys()
            else stac_collection["keywords"]
        )

        providers = (
            []
            if "providers" not in stac_collection.keys()
            else stac_collection["providers"]
        )

        id = (
            []
            if "id" not in stac_collection.keys()
            else settings.collection_delimiter.join(
                [provider_id, stac_collection["id"]]
            )
        )

        stac_version = (
            []
            if "stac_version" not in stac_collection.keys()
            else stac_collection["stac_version"]
        )

        title = (
            [] if "title" not in stac_collection.keys() else stac_collection["title"]
        )

        description = (
            []
            if "description" not in stac_collection.keys()
            else stac_collection["description"]
        )

        license = (
            []
            if "license" not in stac_collection.keys()
            else stac_collection["license"]
        )

        summaries = (
            []
            if "summaries" not in stac_collection.keys()
            else stac_collection["summaries"]
        )

        extent = (
            [] if "extent" not in stac_collection.keys() else stac_collection["extent"]
        )

        return stac_types.Collection(
            type="Collection",
            id=id,
            stac_extensions=stac_extensions,
            stac_version=stac_version,
            title=title,
            description=description,
            keywords=keywords,
            license=license,
            providers=providers,
            summaries=summaries,
            extent=extent,
            links=collection_links,
        )


class ItemSerializer(Serializer):
    """Serialization methods for STAC items."""

    @classmethod
    def response_to_stac(
        cls, stac_item: stac_types.Item, base_url: str, provider_id: str
    ) -> stac_types.Item:
        """Transform (external) stac item to cscale stac item."""

        item_id = [] if "id" not in stac_item.keys() else stac_item["id"]

        collection_id = (
            []
            if "collection" not in stac_item.keys()
            else settings.collection_delimiter.join(
                [provider_id, stac_item["collection"]]
            )
        )

        item_links = ItemLinks(
            collection_id=collection_id, item_id=item_id, base_url=base_url
        ).create_links()

        stac_links = [] if "links" not in stac_item.keys() else stac_item["links"]

        if stac_links:
            item_links += resolve_links(stac_links, base_url)

        stac_extensions = (
            []
            if "stac_extensions" not in stac_item.keys()
            else stac_item["stac_extensions"]
        )

        stac_version = (
            [] if "stac_version" not in stac_item.keys() else stac_item["stac_version"]
        )

        geometry = [] if "geometry" not in stac_item.keys() else stac_item["geometry"]

        bbox = [] if "bbox" not in stac_item.keys() else stac_item["bbox"]

        properties = (
            [] if "properties" not in stac_item.keys() else stac_item["properties"]
        )

        assets = [] if "assets" not in stac_item.keys() else stac_item["assets"]

        return stac_types.Item(
            type="Feature",
            stac_version=stac_version,
            stac_extensions=stac_extensions,
            id=item_id,
            collection=collection_id,
            geometry=geometry,
            bbox=bbox,
            properties=properties,
            links=item_links,
            assets=assets,
        )
