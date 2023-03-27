"""http client management"""
import logging
from functools import lru_cache, wraps
from time import monotonic_ns
from typing import Dict, Optional
from urllib.parse import urlunparse

import httpx
from fastapi import Request
from fastapi.exceptions import HTTPException
from pydantic.networks import AnyHttpUrl
from starlette.datastructures import QueryParams

from mqs.config import settings
from mqs.routers.data_providers import read_data_providers
from mqs.types.data_provider import DataProvider
from mqs.utils import (
    fix_duplicate_slashes,
    remove_provider_from_collection_ids,
    skip_provider_if_all_specified,
)
from mqs.utils_httpx import send_httpx_request

logger = logging.getLogger(__name__)
logger.setLevel(20)

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

    url = fix_duplicate_slashes(urlunparse(api_url.values()))

    return send_httpx_request(method=method, url=url, json=json_data)


def request_all(fastapi_request: Request) -> ResponseDictType:
    """This function calls the /collections endpoint of every registered data provider.

    Args:
        fastapi_request (Request): a FastaPI Request object.

    Returns:
        ResponseDictType: All collected responses stored in a dict.
    """
    all_responses = {}
    for data_provider in read_data_providers():
        if data_provider.is_online():
            response = stac_request(
                fastapi_request=fastapi_request,
                external_stac_url=data_provider.stac_url,
                alternative_path="/collections",
            )
            if not response or not (response.status_code == httpx.codes.OK):
                continue
            all_responses[data_provider.identifier] = response
    return all_responses


def request_collection(fastapi_request: Request) -> ResponseDictType:
    """This function calls the collections/{collection_id} endpoint.

    Args:
        fastapi_request (Request): a FastaPI Request object.

    Raises:
        HTTPException: Throws an HTTPException if the data provider does not exist.

    Returns:
        ResponseDictType: A dictionary of collection JSON, where each key represents a unique data provider ID.
    """
    provider_id = ""
    data_providers = read_data_providers()
    try:
        _provider_id, _ = fastapi_request.path_params["collection_id"].split(
            settings.collection_delimiter
        )
    except ValueError:
        logger.warning(
            "collection_ids should be provided in the format dataproviderId%scollection_id",
            settings.collection_delimiter,
        )
    else:
        provider_id = _provider_id

    if provider_id != "":
        try:
            data_providers = [
                dp for dp in read_data_providers() if dp.identifier == provider_id
            ]
            data_providers[0].is_online()
        except IndexError as ex:
            raise HTTPException(
                status_code=404, detail=f"Unknown data provider with id {provider_id}"
            ) from ex

    data_provider = None
    response = {}
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

        if response is None:  # Timeout occurred
            continue

        if response.status_code == httpx.codes.OK:
            logger.info(
                "Collection or item found for data provider with id %s",
                data_provider.identifier,
            )
            break  # break the loop as soon as the first occurrence of collection_id is found among the data providers
        else:
            logger.warning(
                "Collection or item not found for data provider with id %s",
                data_provider.identifier,
            )

    if not isinstance(data_provider, DataProvider):
        raise HTTPException(status_code=500, detail="No DataProvider instance.")
    elif response is None:
        raise HTTPException(status_code=408, detail="Request timed out.")
    elif response.status_code == 404:
        raise HTTPException(status_code=404, detail="Collection not found")
    elif not (response.status_code == httpx.codes.OK):
        raise HTTPException(
            status_code=response.status_code,
            detail="Request failed for some other reason.",
        )

    return {data_provider.identifier: response}


def request_search_get(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    all_responses = {}
    request_query_params = dict(fastapi_request.query_params)
    for data_provider in read_data_providers():

        if "collections" in request_query_params.keys():
            if skip_provider_if_all_specified(
                data_provider.identifier,
                collections=request_query_params["collections"],
            ):
                continue

        if data_provider.is_online():

            exclude_params = [
                "token",  # always excluded
                "fields",  # always excluded
                "sortby",  # always excluded
                "query",
                "filter",
                # "intersects", # part of the core
                # "limit",
                # "collections",
                # "ids",
                # "bbox",
                # "datetime",
            ]

            for ix in range(2, len(exclude_params) + 1):

                query_params = {
                    k: v
                    for k, v in request_query_params.items()
                    if k not in exclude_params[0:ix]
                }

                if "collections" in query_params.keys():
                    query_params["collections"] = ",".join(
                        remove_provider_from_collection_ids(query_params["collections"])
                    )

                response = stac_request(
                    fastapi_request=fastapi_request,
                    external_stac_url=data_provider.stac_url,
                    alternative_path="/search",
                    alternative_query=str(QueryParams(query_params)),
                )

                if response and response.status_code == httpx.codes.OK:
                    break

            if not response or not (response.status_code == httpx.codes.OK):
                continue

            all_responses[data_provider.identifier] = response

    return all_responses


def request_search_post(fastapi_request: Request) -> ResponseDictType:
    """Iterate through all data providers"""
    all_responses = {}
    request_query_params = dict(fastapi_request._json)
    for data_provider in read_data_providers():

        if "collections" in request_query_params.keys():
            if skip_provider_if_all_specified(
                data_provider.identifier,
                collections=request_query_params["collections"],
            ):
                continue

        if data_provider.is_online():

            exclude_params = [
                "token",  # always excluded
                "fields",  # always excluded
                "sortby",  # always excluded
                "query",
                "filter",
                # "intersects", # part of the core
                # "limit",
                # "collections",
                # "ids",
                # "bbox",
                # "datetime",
            ]

            for ix in range(2, len(exclude_params) + 1):

                query_params = {
                    k: v
                    for k, v in request_query_params.items()
                    if k not in exclude_params[0:ix]
                }

                if "collections" in query_params.keys():
                    query_params["collections"] = remove_provider_from_collection_ids(
                        query_params["collections"]
                    )

                response = stac_request(
                    fastapi_request=fastapi_request,
                    external_stac_url=data_provider.stac_url,
                    alternative_path="/search",
                    alternative_query="",
                    alternative_method="POST",
                    alternative_json=query_params,
                )

                if response and (
                    response.status_code == httpx.codes.OK
                    or response.status_code == httpx.codes.METHOD_NOT_ALLOWED
                ):
                    break

            if not response or not (response.status_code == httpx.codes.OK):
                continue

            all_responses[data_provider.identifier] = response

    return all_responses


# def request_search(
#     fastapi_request: Request, recursive: bool = False
# ) -> ResponseDictType:
#     """Iterate through all data providers"""
#     if recursive:
#         return _recursive_search(fastapi_request=fastapi_request)
#     all_responses = {}
#     for data_provider in read_data_providers():
#         if not data_provider.is_online():
#             continue
#         alternative_json = {k: v for k, v in fastapi_request._json.items()}
#         if data_provider.limit and not "limit" in alternative_json.keys():
#             alternative_json["limit"] = data_provider.limit
#         response = stac_request(
#             fastapi_request=fastapi_request,
#             external_stac_url=data_provider.stac_url,
#             alternative_path="/search",
#             alternative_query="",
#             alternative_method="POST",
#             alternative_json=alternative_json,
#         )

#         if not response or not (response.status_code == httpx.codes.OK):
#             continue

#         all_responses[data_provider.identifier] = response
#     return all_responses


# def _recursive_search(fastapi_request: Request) -> ResponseDictType:
#     """Further iterate through all links"""
#     all_responses = {}
#     for data_provider in read_data_providers():
#         if not data_provider.is_online():
#             continue
#         # initial response
#         alternative_json = {k: v for k, v in fastapi_request._json.items()}
#         if data_provider.limit:
#             alternative_json["limit"] = data_provider.limit
#         response = stac_request(
#             fastapi_request=fastapi_request,
#             external_stac_url=data_provider.stac_url,
#             alternative_query="",
#             alternative_method="POST",
#             alternative_json=alternative_json,
#         )

#         if not response or not (response.status_code == httpx.codes.OK):
#             continue

#         initial_response = response

#         features = []
#         while any(
#             [
#                 link["rel"] in ("next", Relations.next.value)
#                 for link in response.json()["links"]
#             ]
#         ):
#             features.extend(response.json()["features"])
#             next_link = next(
#                 link
#                 for link in response.json()["links"]
#                 if link["rel"] in ("next", Relations.next.value)
#             )
#             alternative_json = {k: v for k, v in next_link["body"].items()}
#             for k, v in fastapi_request._json.items():
#                 if not k in alternative_json.keys():
#                     alternative_json[k] = v
#             if data_provider.limit:
#                 alternative_json["limit"] = data_provider.limit
#             # next response
#             response = stac_request(
#                 fastapi_request=fastapi_request,
#                 external_stac_url=data_provider.stac_url,
#                 alternative_query="",
#                 alternative_method="POST",
#                 alternative_json=alternative_json,
#             )

#             if not response or not (response.status_code == httpx.codes.OK):
#                 break

#         final_response = {
#             k: v for k, v in initial_response.json().items() if not k == "features"
#         }
#         final_response["features"] = features
#         all_responses[data_provider.identifier] = httpx.Response(
#             status_code=initial_response.status_code, json=final_response
#         )
#     return all_responses
