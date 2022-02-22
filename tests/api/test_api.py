from datetime import datetime, timedelta

from ..conftest import MockStarletteRequest

STAC_CORE_ROUTES = [
    "GET /",
    "GET /collections",
    "GET /collections/{collectionId}",
    "GET /collections/{collectionId}/items",
    "GET /collections/{collectionId}/items/{itemId}",
    "GET /conformance",
    "GET /search",
    "POST /search",
]


def test_core_router(api_client):
    core_routes = set(STAC_CORE_ROUTES)
    api_routes = set(
        [f"{list(route.methods)[0]} {route.path}" for route in api_client.app.routes]
    )
    assert not core_routes - api_routes


def test_api_headers(app_client):
    resp = app_client.get("/api")
    assert resp.headers["content-type"] == "application/json"
    assert resp.status_code == 200


def test_conformance(app_client):
    response = app_client.get("/conformance")
    assert response.status_code == 200
    assert list(response.json().keys())[0] == "conformsTo"


