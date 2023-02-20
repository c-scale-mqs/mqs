import datetime
from pydantic import BaseModel
from typing import Optional
from pydantic.networks import AnyHttpUrl
import httpx


class DataProvider(BaseModel):
    identifier: str
    name: str
    stac_url: AnyHttpUrl
    limit: Optional[int] = None
    online: Optional[bool] = False
    last_checked: Optional[datetime.datetime] = None

    def is_online(self, max_response_time=30) -> bool:
        response = httpx.get(url=self.stac_url)
        status_code = response.status_code
        response_time = response.elapsed.total_seconds()
        self.online = status_code == 200 and response_time <= max_response_time
        self.last_checked = datetime.datetime.now()
        return self.online
