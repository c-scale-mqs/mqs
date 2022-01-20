from fastapi import FastAPI
from stac_fastapi.api.app import StacApi
from fastapi.openapi import utils

# This is to include servers in the openapi.json
def custom_openapi(api: StacApi):
    app = api.app
    def wrapper():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = utils.get_openapi(
            title=api.title,
            description=api.description,
            version=api.api_version,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return wrapper
