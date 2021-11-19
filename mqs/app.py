"""MQS STAC-FastAPI application"""
from stac_fastapi.api.app import StacApi

from mqs.config import settings
from mqs.core import CoreCrudClient
from mqs.types.search import MqsSTACSearch


api = StacApi(
    settings=settings,
    client=CoreCrudClient(),
    search_request_model=MqsSTACSearch,
)
app = api.app


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
