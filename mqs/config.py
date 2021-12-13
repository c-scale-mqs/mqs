"""API configuration."""
from typing import List, Optional

from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl
from stac_fastapi.types.config import ApiSettings


class DataProvider(BaseModel):
    identifier: str
    name: str
    stac_url: AnyHttpUrl
    limit: Optional[int] = None


class MqsSettings(ApiSettings):
    """MQS-specific API settings.

    Attributes:
        data_providers: list of C-SCALE data providers.
    """

    collection_delimiter: str = "|"

    # TODO: use actual CSCALE data providers
    data_providers: List[DataProvider] = [
        {
            "identifier": "earth-search",
            "name": "Earth Search",
            "stac_url": "https://earth-search.aws.element84.com/v0",
            "limit": 748,
        },
        {
            "identifier": "resto",
            "name": "resto STAC",
            "stac_url": "https://tamn.snapplanet.io",
            "limit": 500,
        },
        {
            "identifier": "ch",
            "name": "Data Catalog of the Swiss Federal Spatial Data Infrastructure",
            "stac_url": "https://data.geo.admin.ch/api/stac/v0.9",
            "limit": 100,
        },
    ]


settings = MqsSettings()
