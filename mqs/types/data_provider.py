from pydantic import BaseModel
from typing import Optional
from pydantic.networks import AnyHttpUrl


class DataProvider(BaseModel):
    identifier: str
    name: str
    stac_url: AnyHttpUrl
    limit: Optional[int] = None
