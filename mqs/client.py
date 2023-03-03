"""http client management"""
import asyncio
import logging
from turtle import ht
import typing
from functools import lru_cache, wraps
from time import monotonic_ns
from typing import Dict, Optional, Set, Type, Union
from urllib.parse import urlparse, urlunparse

import attr
import httpx
from fastapi import Request
from fastapi.exceptions import HTTPException
from pydantic.networks import AnyHttpUrl
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations

from mqs.config import settings
from mqs.routers.data_providers import read_data_providers
from mqs import gocdb

logger = logging.getLogger(__name__)

ResponseDictType = Dict[str, httpx.Response]

# TODO: use async client


# taken from https://gist.github.com/Morreski/c1d08a3afa4040815eafd3891e16b945
def timed_lru_cache(
    _func=None, *, seconds: int = 600, maxsize: int = 128, typed: bool = False
):
    """Extension of functools lru_cache with a timeout

    Parameters:
    seconds (int): Timeout in seconds to clear the WHOLE cache, default = 10 minutes
    maxsize (int): Maximum Size of the Cache
    typed (bool): Same value of different type will be a different entry

    """

    def wrapper_cache(f):
        f = lru_cache(maxsize=maxsize, typed=typed)(f)
        f.delta = seconds * 10**9
        f.expiration = monotonic_ns() + f.delta

        @wraps(f)
        def wrapped_f(*args, **kwargs):
            if monotonic_ns() >= f.expiration:
                f.cache_clear()
                f.expiration = monotonic_ns() + f.delta
            return f(*args, **kwargs)

        wrapped_f.cache_info = f.cache_info
        wrapped_f.cache_clear = f.cache_clear
        return wrapped_f

    # To allow decorator to be used without arguments
    if _func is None:
        return wrapper_cache
    else:
        return wrapper_cache(_func)


def stac_request(
    fastapi_request: Request,
    external_stac_url: AnyHttpUrl,
    alternative_path: Optional[str] = None,
    alternative_query: Optional[str] = None,
    alternative_method: Optional[str] = None,
    alternative_json: Optional[dict] = None,
) -> httpx.Response:
    api_scheme = external_stac_url.scheme
    api_netloc = (
        external_stac_url.host
        if not external_stac_url.path
        else external_stac_url.host + external_stac_url.path
    )
    api_path = fastapi_request.url.path if not alternative_path else alternative_path

    if api_path.startswith(settings.root_path) and settings.root_path == "/":
        api_path = api_path[1:]
    elif api_path.startswith(settings.root_path):
        api_path = api_path.split(settings.root_path)[1]

    api_params = ""
    api_query = (
        fastapi_request.url.query
        if not (alternative_query or alternative_query == "")
        else alternative_query
    )
    api_fragment = fastapi_request.url.fragment

    api_netloc = (
        api_netloc.rstrip("/")
        if (api_netloc.endswith("/") and api_path.startswith("/"))
        else api_netloc
    )

    api_url = {
        "scheme": api_scheme,
        "netloc": api_netloc,
        "path": api_path,
        "params": api_params,
        "query": api_query,
        "fragment": api_fragment,
    }

    if alternative_json:
        json_data = alternative_json
    elif "_json" in dir(fastapi_request):
        json_data = fastapi_request._json
    else:
        json_data = None

    method = fastapi_request.method if not alternative_method else alternative_method
    return _send_httpx_request(
        method=method, url=urlunparse(api_url.values()), json=json_data
    )


# @timed_lru_cache(seconds=900)
def _send_httpx_request(method, url, json) -> httpx.Response:
    # print(_send_httpx_request.cache_info())
    httpx_request = httpx.Request(
        method=method,
        url=url,
        json=json,
        headers=httpx.Headers({"Connection": "close"}),
    )
    try:
        with httpx.Client() as client:
            response = client.send(httpx_request)
            return response
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error while requesting {exc.request.url!r}.",
        )


def request_all(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    all_responses = {}
    for data_provider in read_data_providers():
        if data_provider.is_online():
            response = stac_request(
                fastapi_request=fastapi_request,
                external_stac_url=data_provider.stac_url,
                alternative_path="/collections",
            )
            all_responses[data_provider.identifier] = response
    return all_responses


def request_collection(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    provider_id = ""
    data_providers = read_data_providers()
    try:
        provider_id, _ = fastapi_request.path_params["collection_id"].split(
            settings.collection_delimiter
        )
    except ValueError:
        logger.warn(
            f"collection_ids should be provided in the format dataproviderId{settings.collection_delimiter}collection_id"
        )
        # raise HTTPException(
        #     status_code=400,
        #     detail=f"collection_ids must be provided in the format dataproviderId{settings.collection_delimiter}collection_id",
        # )

    if provider_id != "":
        try:
            data_providers = [
                dp for dp in read_data_providers() if dp.identifier == provider_id
            ]
            data_providers[0].is_online()
        except IndexError:
            raise HTTPException(
                status_code=404, detail=f"Unknown data provider with id {provider_id}"
            )

    for data_provider in data_providers:
        if not data_provider.is_online():
            continue
        response = stac_request(
            fastapi_request=fastapi_request,
            external_stac_url=data_provider.stac_url,
            alternative_path=fastapi_request.url.path.replace(
                provider_id + settings.collection_delimiter, ""
            ),
        )

        if response.status_code != 404:
            logger.info(
                f"Collection or item found for data provider with id {data_provider.identifier}"
            )
            break
        else:
            logger.warn(
                f"Collection or item not found for data provider with id {data_provider.identifier}"
            )

    return {data_provider.identifier: response}


def request_search(
    fastapi_request: Request, recursive: bool = False
) -> ResponseDictType:
    """Iterate through all data providers"""
    if recursive:
        return _recursive_search(fastapi_request=fastapi_request)
    all_responses = {}
    for data_provider in read_data_providers():
        if not data_provider.is_online():
            continue
        alternative_json = {k: v for k, v in fastapi_request._json.items()}
        if data_provider.limit and not "limit" in alternative_json.keys():
            alternative_json["limit"] = data_provider.limit
        response = stac_request(
            fastapi_request=fastapi_request,
            external_stac_url=data_provider.stac_url,
            alternative_query="",
            alternative_method="POST",
            alternative_json=alternative_json,
        )
        if not response.status_code == 200:
            continue
        all_responses[data_provider.identifier] = response
    return all_responses


def _recursive_search(fastapi_request: Request) -> ResponseDictType:
    """Further iterate through all links"""
    all_responses = {}
    for data_provider in read_data_providers():
        if not data_provider.is_online():
            continue
        # initial response
        alternative_json = {k: v for k, v in fastapi_request._json.items()}
        if data_provider.limit:
            alternative_json["limit"] = data_provider.limit
        response = stac_request(
            fastapi_request=fastapi_request,
            external_stac_url=data_provider.stac_url,
            alternative_query="",
            alternative_method="POST",
            alternative_json=alternative_json,
        )
        initial_response = response
        if not response.status_code == 200:
            continue
        features = []
        while any(
            [
                link["rel"] in ("next", Relations.next.value)
                for link in response.json()["links"]
            ]
        ):
            features.extend(response.json()["features"])
            next_link = next(
                link
                for link in response.json()["links"]
                if link["rel"] in ("next", Relations.next.value)
            )
            alternative_json = {k: v for k, v in next_link["body"].items()}
            for k, v in fastapi_request._json.items():
                if not k in alternative_json.keys():
                    alternative_json[k] = v
            if data_provider.limit:
                alternative_json["limit"] = data_provider.limit
            # next response
            response = stac_request(
                fastapi_request=fastapi_request,
                external_stac_url=data_provider.stac_url,
                alternative_query="",
                alternative_method="POST",
                alternative_json=alternative_json,
            )
            if not response.status_code == 200:
                break
        final_response = {
            k: v for k, v in initial_response.json().items() if not k == "features"
        }
        final_response["features"] = features
        all_responses[data_provider.identifier] = httpx.Response(
            status_code=initial_response.status_code, json=final_response
        )
    return all_responses
