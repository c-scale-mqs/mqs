"""http client management"""
import asyncio
import logging
import typing
from datetime import datetime
from typing import List, Optional, Set, Type, Union, Dict
from urllib.parse import urlparse, urlunparse

import attr
from fastapi.exceptions import HTTPException
import httpx
from fastapi import Request
from pydantic.networks import AnyHttpUrl
from stac_fastapi.types.stac import Collection, Collections, Item, ItemCollection
from stac_pydantic.links import Relations

from mqs.config import settings

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

    api_url = {
        "scheme": external_stac_url.scheme,
        "netloc": external_stac_url.host
        if not external_stac_url.path
        else external_stac_url.host + external_stac_url.path,
        "path": fastapi_request.url.path if not alternative_path else alternative_path,
        "params": "",
        "query": fastapi_request.url.query
        if not (alternative_query or alternative_query == "")
        else alternative_query,
        "fragment": fastapi_request.url.fragment,
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
        )
        all_responses[data_provider.identifier] = response
    return all_responses


def request_collection(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    try:
        provider_id, _ = fastapi_request.path_params["collectionId"].split(
            settings.collection_delimiter
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"collectionIds must be provided in the format dataproviderId{settings.collection_delimiter}collectionId",
        )
    try:
        data_provider = [
            dp for dp in settings.data_providers if dp.identifier == provider_id
        ][0]
    except IndexError:
        raise HTTPException(
            status_code=404, detail=f"Unknown data provider with id {provider_id}"
        )

    response = stac_request(
        fastapi_request=fastapi_request,
        external_stac_url=data_provider.stac_url,
        alternative_path=fastapi_request.url.path.replace(
            provider_id + settings.collection_delimiter, ""
        ),
    )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Collection or item not found")

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
