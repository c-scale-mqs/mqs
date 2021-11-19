"""http client management"""
import asyncio
import logging
import typing
from datetime import datetime
from typing import List, Optional, Set, Type, Union, Dict
from urllib.parse import urlparse, urlunparse

import attr
import httpx
from fastapi import Request
from pydantic.networks import AnyHttpUrl
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection

from mqs.config import settings

logger = logging.getLogger(__name__)

ResponseDictType = Dict[str, httpx.Response]

# TODO: use async client


def stac_request(
    fastapi_request: Request,
    external_stac_url: AnyHttpUrl,
    alternative_path: Optional[str] = None,
) -> httpx.Response:

    api_url = {
        "scheme": external_stac_url.scheme,
        "netloc": external_stac_url.host
        if not external_stac_url.path
        else external_stac_url.host + external_stac_url.path,
        "path": fastapi_request.url.path if not alternative_path else alternative_path,
        "params": "",
        "query": fastapi_request.url.query,
        "fragment": fastapi_request.url.fragment,
    }

    json_data = None if not "_json" in dir(fastapi_request) else fastapi_request._json
    httpx_request = httpx.Request(
        method=fastapi_request.method, url=urlunparse(api_url.values()), json=json_data
    )

    with httpx.Client() as client:
        response = client.send(httpx_request)
        return response


def request_all(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    all_responses = {}
    for data_provider in settings.data_providers:
        response = stac_request(
            fastapi_request=fastapi_request,
            external_stac_url=data_provider.stac_url,
        )
        all_responses[data_provider.identifier] = response
    return all_responses


def request_collection(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    provider_id, collection_id = fastapi_request.path_params["collectionId"].split("|")
    data_provider = [
        dp for dp in settings.data_providers if dp.identifier == provider_id
    ][0]
    response = stac_request(
        fastapi_request=fastapi_request,
        external_stac_url=data_provider.stac_url,
        alternative_path=fastapi_request.url.path.replace(provider_id, "").replace(
            "|", ""
        ),
    )
    return {data_provider.identifier: response}
