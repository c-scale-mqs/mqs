"""MQS STAC-FastAPI application"""
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.extensions.core import (
    # ContextExtension,
    SortExtension,
    TokenPaginationExtension,
    FieldsExtension,
    FilterExtension,
    QueryExtension,
)

from mqs.config import settings
from mqs.core import CoreCrudClient
from mqs.routers.data_providers import router as gocdb_router
from mqs.types.search import MqsSTACSearch
from mqs.utils import custom_openapi
from mqs.version import __version__ as mqs_version

extensions = [
    SortExtension(),
    TokenPaginationExtension(),
    # ContextExtension(),  # Note: deprecated in January 2023,
    FieldsExtension(),
    FilterExtension(),
    QueryExtension(),
]
get_request_model = create_get_request_model(extensions)
post_request_model = create_post_request_model(extensions, base_model=MqsSTACSearch)

api = StacApi(
    settings=settings,
    api_version=mqs_version,
    title=settings.title,
    description=settings.description,
    extensions=extensions,
    client=CoreCrudClient(post_request_model=post_request_model),
    response_class=ORJSONResponse,
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    app=FastAPI(
        root_path=settings.root_path,
        openapi_url=settings.openapi_url,
        servers=[{"url": settings.root_path}],
    ),
)

app = api.app
app.openapi = custom_openapi(api)
app.include_router(gocdb_router)


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "mqs.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()


def create_handler(app):
    """Create a handler to use with AWS Lambda if mangum available."""
    try:
        from mangum import Mangum

        return Mangum(app)
    except ImportError:
        return None


handler = create_handler(app)
