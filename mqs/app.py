"""MQS STAC-FastAPI application"""
from fastapi import FastAPI
from stac_fastapi.api.app import StacApi
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    QueryExtension,
    SortExtension,
)

from mqs.config import settings
from mqs.core import CoreCrudClient
from mqs.types.search import MqsSTACSearch
from mqs.utils import custom_openapi
from mqs.version import __version__ as mqs_version

extensions = [
    SortExtension(),
    ContextExtension(),
    # currently FieldsExtension and QueryExtension are not implemented
]

api = StacApi(
    settings=settings,
    title=settings.title,
    description=settings.description,
    extensions=extensions,
    client=CoreCrudClient(),
    search_request_model=MqsSTACSearch,
    app=FastAPI(
        root_path=settings.root_path,
        openapi_url=settings.openapi_url,
        servers=[{"url": settings.root_path}],
    ),
)

app = api.app
app.openapi = custom_openapi(api)


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
