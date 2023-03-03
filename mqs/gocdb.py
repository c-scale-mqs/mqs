"""gocdb client management"""
import logging
from collections import OrderedDict
from typing import List

import httpx
import xmltodict
from pydantic.networks import AnyHttpUrl

from mqs.types import data_provider

logger = logging.getLogger(__name__)


def get_site_list() -> OrderedDict:
    httpx_request = httpx.Request(
        method="GET",
        url="https://goc.egi.eu/gocdbpi/public/?method=get_site_list&scope=C-SCALE",
    )

    with httpx.Client() as client:
        response = client.send(httpx_request)
        return xmltodict.parse(response.text)


def get_site_names() -> List[str]:
    sites = []
    r = get_site_list()
    for site in r["results"]["SITE"]:
        sites.append(site["@NAME"])
    return sites


def get_service_endpoint(site: str) -> OrderedDict:
    url = f"https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint&sitename={site}"

    httpx_request = httpx.Request(
        method="GET",
        url=url,
    )

    with httpx.Client() as client:
        response = client.send(httpx_request)
        return xmltodict.parse(response.text)


def get_stac_endpoint(site: str) -> AnyHttpUrl:
    r = get_service_endpoint(site)

    try:
        results = _dict2list(r["results"]["SERVICE_ENDPOINT"])
    except TypeError as ex:
        logger.warn(ex)
        return None

    for endpoints in results:
        if not endpoints["ENDPOINTS"]:
            continue
        for endpoint in _dict2list(endpoints["ENDPOINTS"]["ENDPOINT"]):
            if endpoint["NAME"].lower() == "stac":
                return endpoint["URL"]


def _dict2list(d: OrderedDict) -> List[OrderedDict]:
    return [d] if isinstance(d, OrderedDict) else d


def get_data_providers() -> List[data_provider.DataProvider]:
    data_providers = []
    sites = get_site_names()
    for site in sites:
        stac_url = get_stac_endpoint(site)
        if stac_url:
            # stac_url_strip = (
            #     stac_url.rstrip("/") if stac_url.endswith("/") else stac_url
            # )
            data_providers.append(
                data_provider.DataProvider(
                    **{
                        "identifier": site,
                        "name": site,
                        "stac_url": stac_url,
                    }
                )
            )
            data_providers[-1].is_online()
    return data_providers
