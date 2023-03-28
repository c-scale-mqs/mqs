import datetime
from typing import Optional
import httpx

from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl

from mqs.utils_httpx import send_httpx_request


class DataProvider(BaseModel):
    identifier: str
    name: str
    stac_url: AnyHttpUrl
    limit: Optional[int] = None
    online: Optional[bool] = False
    last_checked: Optional[datetime.datetime] = None

    def is_online(self, max_response_time=30) -> bool:
        response = send_httpx_request(method="GET", url=self.stac_url, json=None)
        if isinstance(response, httpx.Response):
            status_code = response.status_code
            response_time = response.elapsed.total_seconds()
            self.online = status_code == 200 and response_time <= max_response_time
            self.last_checked = datetime.datetime.now()
        else:
            self.online = False
        return self.online
