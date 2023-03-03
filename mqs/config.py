"""API configuration."""
from typing import List

from stac_fastapi.types.config import ApiSettings

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


settings = MqsSettings()
