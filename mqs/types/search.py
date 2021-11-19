"""mqs.types.search module.

"""

import logging
import operator
from dataclasses import dataclass
from enum import auto
from types import DynamicClassAttribute
from typing import Any, Callable, Dict, List, Optional, Set, Union

import sqlalchemy as sa
from pydantic import Field, ValidationError, conint, root_validator
from pydantic.error_wrappers import ErrorWrapper
from stac_fastapi.types.config import Settings
from stac_pydantic.api import Search
from stac_pydantic.api.extensions.fields import FieldsExtension as FieldsBase
from stac_pydantic.utils import AutoValueEnum

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class MqsSTACSearch(Search):
    """Search model."""

    # Make collections optional, default to searching all collections if none are provided
    collections: Optional[List[str]] = None
