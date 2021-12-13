import json
import os
from typing import Callable, Dict

import pytest
from mqs.config import MqsSettings
from mqs.core import CoreCrudClient
from mqs.types.search import MqsSTACSearch
from stac_fastapi.api.app import StacApi
from stac_fastapi.extensions.core import (ContextExtension, FieldsExtension,
                                          QueryExtension, SortExtension,
                                          TransactionExtension)
from stac_fastapi.types.config import Settings
from starlette.testclient import TestClient

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class TestSettings(MqsSettings):
    class Config:
        env_file = ".env.test"


settings = TestSettings()
Settings.set(settings)


@pytest.fixture
def load_test_data() -> Callable[[str], Dict]:
    def load_file(filename: str) -> Dict:
        with open(os.path.join(DATA_DIR, filename)) as file:
            return json.load(file)

    return load_file


class MockStarletteRequest:
    base_url = "http://test-server"


@pytest.fixture
def api_client():
    settings = MqsSettings()
    return StacApi(
        settings=settings,
        client=CoreCrudClient(),
        extensions=[ContextExtension(), SortExtension()],
        search_request_model=MqsSTACSearch,
    )


@pytest.fixture
def app_client(api_client):

    with TestClient(api_client.app) as test_app:
        yield test_app
