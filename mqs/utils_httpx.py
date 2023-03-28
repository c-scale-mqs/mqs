"""httpx client utils"""
import logging
from functools import lru_cache, wraps
from time import monotonic_ns

import httpx

logger = logging.getLogger(__name__)
logger.setLevel(20)

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


@timed_lru_cache(seconds=300)
def _send_httpx_request_get(
    url, headers, timeout=httpx.Timeout(180.0, connect=30.0)
) -> httpx.Response:
    try:
        with httpx.Client() as client:
            response = client.get(
                url=url,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Request timed out")
        return None
    except httpx.HTTPStatusError as ex:
        logger.warning("Request failed with status code %s", ex.response.status_code)
        return ex.response
    except httpx.ConnectError as ex:
        logger.warning("Request connect error: %s", str(ex))
        return ex.request
    except httpx.RequestError as ex:
        logger.warning("Request failed for some other reason")
        return ex.request
    else:
        return response


def _send_httpx_request_post(
    url, headers, json, timeout=httpx.Timeout(180.0, connect=30.0)
) -> httpx.Response:
    try:
        with httpx.Client() as client:
            response = client.post(
                url=url,
                headers=headers,
                timeout=timeout,
                json=json,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Request timed out")
        return None
    except httpx.HTTPStatusError as ex:
        logger.warning("Request failed with status code %s", ex.response.status_code)
        return ex.response
    except httpx.RequestError as ex:
        logger.warning("Request failed for some other reason")
        return ex.request
    else:
        return response


def _send_httpx_request_other(httpx_request: httpx.Request) -> httpx.Response:
    try:
        with httpx.Client() as client:
            response = client.send(httpx_request)
            response.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Request timed out")
        return None
    except httpx.HTTPStatusError as ex:
        logger.warning("Request failed with status code %s", ex.response.status_code)
        return ex.response
    except httpx.RequestError as ex:
        logger.warning("Request failed for some other reason")
        return ex.request
    else:
        return response


def send_httpx_request(method, url, json) -> httpx.Response:

    httpx_request = httpx.Request(
        method=method,
        url=url,
        json=json,
        headers=httpx.Headers({"Connection": "close"}),
    )

    timeout = 300.0

    if method.lower() == "get":
        return _send_httpx_request_get(
            url=httpx_request.url,
            headers=tuple(sorted(httpx_request.headers.items())),
            timeout=timeout,
        )
    if method.lower() == "post":
        return _send_httpx_request_post(
            url=httpx_request.url,
            headers=tuple(sorted(httpx_request.headers.items())),
            timeout=timeout,
            json=json,
        )
    else:
        return _send_httpx_request_other(httpx_request)
