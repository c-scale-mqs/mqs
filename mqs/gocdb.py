"""gocdb client management"""
import logging
from collections import OrderedDict
import os
from typing import List, Optional

import httpx
import xmltodict
from fastapi import HTTPException
from pydantic.networks import AnyHttpUrl
import yaml

from mqs.types import data_provider
from mqs.utils_httpx import send_httpx_request

logger = logging.getLogger(__name__)
logger.setLevel(20)


def get_site_list() -> OrderedDict:
    """Get the list of sites registered within the C-SCALE scope.

    Returns:
        OrderedDict: list of sites.
    """
    httpx_request = httpx.Request(
        method="GET",
        url="https://goc.egi.eu/gocdbpi/public/?method=get_site_list&scope=C-SCALE",
    )

    site_list = {}
    try:
        response = send_httpx_request(method="GET", url=httpx_request.url, json=None)
        _site_list = xmltodict.parse(response.text)
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(status_code=503, detail="Error querying the GOCDB.") from ex
    else:
        site_list = _site_list
    return site_list


def get_site_names() -> List[str]:
    """Extract names from the list of registered sites.

    Returns:
        List[str]: Site names.
    """
    sites = []
    response = get_site_list()
    has_results = "results" in response.keys()
    if has_results:
        has_sites = (
            _is_dict(response["results"]) and "SITE" in response["results"].keys()
        )
        if has_sites:
            for site in response["results"]["SITE"]:
                site_name = None
                try:
                    _site_name = site["@NAME"]
                except KeyError as ex:
                    logger.warning("Cannot determine site name: %s", site)
                    logger.warning(ex)
                else:
                    site_name = _site_name
                if site_name:
                    sites.append(site_name)
    return sites


def get_service_endpoint(site: str) -> OrderedDict:
    """Finds the service endpoints for a particular site.

    Args:
        site (str): site name.

    Returns:
        OrderedDict: service endpoints regeistered for site.
    """
    url = f"https://goc.egi.eu/gocdbpi/public/?method=get_service_endpoint&sitename={site}"

    httpx_request = httpx.Request(
        method="GET",
        url=url,
    )

    endpoint_list = {}
    try:
        response = send_httpx_request(method="GET", url=httpx_request.url, json=None)
        _endpoint_list = xmltodict.parse(response.text)
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(status_code=503, detail="Error querying the GOCDB.") from ex
    else:
        endpoint_list = _endpoint_list
    return endpoint_list


def get_stac_endpoint(site: str) -> AnyHttpUrl:
    """Extract STAC endpoint for provided site name.

    Args:
        site (str): site name.

    Returns:
        AnyHttpUrl: Full URL to STAC endpoint.
    """
    stac_endpoint = None

    response = get_service_endpoint(site)

    service_endpoints = []
    has_results = "results" in response.keys()
    if has_results:
        has_service_endpoint = (
            _is_dict(response["results"])
            and "SERVICE_ENDPOINT" in response["results"].keys()
        )
        if has_service_endpoint:
            try:
                _service_endpoints = _dict2list(response["results"]["SERVICE_ENDPOINT"])
            except TypeError as ex:
                logger.warning(ex)
            else:
                service_endpoints = _service_endpoints

    for endpoints in service_endpoints:

        has_endpoints = _is_dict(endpoints) and "ENDPOINTS" in endpoints.keys()

        if has_endpoints:

            if not endpoints["ENDPOINTS"]:
                continue

            has_endpoint_key = (
                _is_dict(endpoints["ENDPOINTS"])
                and "ENDPOINT" in endpoints["ENDPOINTS"].keys()
            )
            if not has_endpoint_key:
                continue

            all_endpoints = []
            try:
                _all_endpoints = _dict2list(endpoints["ENDPOINTS"]["ENDPOINT"])
            except TypeError as ex:
                logger.warning(ex)
            else:
                all_endpoints = _all_endpoints

            for endpoint in all_endpoints:
                has_name = _is_dict(endpoint) and "NAME" in endpoint.keys()
                if not has_name:
                    continue
                if (
                    endpoint["NAME"].lower() == "stac"
                ):  # this is why data providers need to register their endpoint using the name "STAC"
                    has_url = "URL" in endpoint.keys()
                    if has_url:
                        stac_endpoint = endpoint["URL"]
                        break
    return stac_endpoint


def _is_dict(value) -> bool:
    """Helper function to check if data type is a dict.

    Args:
        value (_type_): any input value.

    Returns:
        bool: True if dict or OrderedDict
    """
    return isinstance(value, OrderedDict) or isinstance(value, dict)


def _dict2list(dic: OrderedDict) -> List[OrderedDict]:
    """Helper function to convert OrderedDicts into Lists of OrderedDicts.

    Args:
        dic (OrderedDict): input dictionary.

    Returns:
        List[OrderedDict]: converted list of dicts.
    """
    return [dic] if _is_dict(dic) else dic


def load_config(config_file_path: Optional[str] = None) -> dict:
    """
    Load additional data provider configurations from the specified YAML file or a default file path.

    Parameters:
        config_file_path (str, optional): Path to the YAML config file. Defaults to None.

    Returns:
        dict: Dictionary containing whitelist, blacklist, and all data providers as instances of DataProvider.
    """
    # Get the YAML file location from the provided path or environment variable
    yaml_file_path = config_file_path or os.getenv("DATA_PROVIDERS_CONFIG_FILE_PATH", "/opt/data_providers.yaml")

    try:
        # Load the YAML configuration
        with open(yaml_file_path, 'r') as file:
            data_provider_config = yaml.safe_load(file)
    except (yaml.YAMLError, FileNotFoundError) as e:
        logger.warning(f"Error loading Data Providers YAML config: {e}")
        return {'whitelist': [], 'blacklist': [], 'data_providers': []}  # Return empty lists on error

    # Access the white-listed, black-listed, and all data providers
    white_listed_providers = data_provider_config.get('whitelist', [])
    black_listed_providers = data_provider_config.get('blacklist', [])
    all_providers = [data_provider.DataProvider(**data) for data in data_provider_config.get('data_providers', [])]

    # Call is_online for each data provider
    for provider in all_providers:
        provider.is_online()

    return {
        'whitelist': white_listed_providers,
        'blacklist': black_listed_providers,
        'data_providers': all_providers
    }


def get_data_providers() -> List[data_provider.DataProvider]:
    """Function to collect all registered data providers and STAC endpoints.

    Returns:
        List[data_provider.DataProvider]: each data provider is stored as a DataProvider class instance.
    """
    data_providers = []

    # Query the GOCDB
    sites = get_site_names()
    for site in sites:
        stac_url = get_stac_endpoint(site)
        if stac_url:
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

    # Load the local configuration
    config_data = load_config()
    all_providers = config_data['data_providers']
    blacklist_providers = config_data['blacklist']
    whitelist_providers = config_data['whitelist']

    # Concatenate the list of all data providers considering only white-listed data providers
    all_data_providers = data_providers + [provider for provider in all_providers if provider.identifier in whitelist_providers]

    # Remove black-listed data providers
    filtered_data_providers = [provider for provider in all_data_providers if provider.identifier not in blacklist_providers]

    return filtered_data_providers
