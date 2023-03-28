"""mqs.types.search module.

"""

import logging
from typing import List, Optional

from pydantic import conint
from stac_pydantic.api import Search

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class MqsSTACSearch(Search):
    """Search model."""

    # Make collections optional, default to searching all collections if none are provided
    collections: Optional[List[str]] = None

    token: Optional[str] = None
    limit: Optional[conint(ge=0, le=10000)] = 10
