"""gocdb endpoint management"""
import datetime
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks

from fastapi_utils.tasks import repeat_every

from mqs.gocdb import get_data_providers
from mqs.types import data_provider


logger = logging.getLogger(__name__)

background_tasks = BackgroundTasks()
router = APIRouter()


data_providers: List[data_provider.DataProvider] = []


def update_data_providers():
    global data_providers
    data_providers = get_data_providers()


@router.on_event("startup")
@repeat_every(seconds=3600)
def startup_event():
    update_data_providers()


@router.get(
    "/data-providers",
    response_model=List[data_provider.DataProvider],
)
def read_data_providers():
    return data_providers
