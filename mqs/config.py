"""API configuration."""
from typing import Any, Dict, List

from stac_fastapi.types.config import ApiSettings
from stac_pydantic.shared import MimeTypes

from mqs import gocdb
from mqs.types import data_provider


class MqsSettings(ApiSettings):
    """MQS-specific API settings.

    Attributes:
        data_providers: list of C-SCALE data providers.
    """

    title: str = "C-SCALE Earth Observation Metadata Query Service (EO-MQS)"
    description: str = "The Earth Observation Metadata Query Service (EO-MQS) is the central entry point to query for metadata across the C-SCALE federation."
    root_path: str = "/stac/v1"
    collection_delimiter: str = "|"
    data_providers: List[data_provider.DataProvider] = gocdb.get_data_providers()
    links: List[Dict[str, Any]] = [
        {
            "rel": "privacy-policy",
            "type": MimeTypes.html.value,
            "title": "EODC Privacy Policy",
            "href": "https://eodc.eu/dataprotection",
        }
    ]
    reload: bool = True


settings = MqsSettings()
