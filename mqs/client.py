"""http client management"""
import asyncio
import logging
import typing
from datetime import datetime
from typing import Dict, List, Optional, Set, Type, Union
from urllib.parse import urlparse, urlunparse

import attr
import httpx
from fastapi import Request
from fastapi.exceptions import HTTPException
from pydantic.networks import AnyHttpUrl
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations

from mqs.config import settings
from mqs import gocdb

logger = logging.getLogger(__name__)

ResponseDictType = Dict[str, httpx.Response]

# TODO: use async client


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

    httpx_request = httpx.Request(
        method=method,
        url=urlunparse(api_url.values()),
        json=json_data,
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
            alternative_path="/collections",
        )
        all_responses[data_provider.identifier] = response
    return all_responses


def request_collection(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    provider_id = ""
    data_providers = settings.data_providers
    try:
        provider_id, _ = fastapi_request.path_params["collectionId"].split(
            settings.collection_delimiter
        )
    except ValueError:
        logger.warn(
            f"collectionIds should be provided in the format dataproviderId{settings.collection_delimiter}collectionId"
        )
        # raise HTTPException(
        #     status_code=400,
        #     detail=f"collectionIds must be provided in the format dataproviderId{settings.collection_delimiter}collectionId",
        # )

    if provider_id != "":
        try:
            data_providers = [
                dp for dp in settings.data_providers if dp.identifier == provider_id
            ]
            data_providers[0]
        except IndexError:
            raise HTTPException(
                status_code=404, detail=f"Unknown data provider with id {provider_id}"
            )

    for data_provider in data_providers:
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
    for data_provider in settings.data_providers:
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
        if not response.status_code == 200:
            continue
        all_responses[data_provider.identifier] = response
    return all_responses


def _recursive_search(fastapi_request: Request) -> ResponseDictType:
    """Further iterate through all links"""
    all_responses = {}
    for data_provider in settings.data_providers:
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
