"""API configuration."""
from stac_fastapi.types.config import ApiSettings
from typing import List
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl


class DataProvider(BaseModel):
    identifier: str
    name: str
    stac_url: AnyHttpUrl


class MqsSettings(ApiSettings):
    """MQS-specific API settings.

    Attributes:
        data_providers: list of C-SCALE data providers.
    """

    # TODO: use actual CSCALE data providers
    data_providers: List[DataProvider] = [
        {
            "identifier": "earth-search",
            "name": "Earth Search",
            "stac_url": "https://earth-search.aws.element84.com/v0",
        },
        {
            "identifier": "resto",
            "name": "resto STAC",
            "stac_url": "https://tamn.snapplanet.io",
        },
    ]


settings = MqsSettings()
