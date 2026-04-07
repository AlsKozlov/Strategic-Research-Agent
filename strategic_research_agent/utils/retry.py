from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def run_with_retries(
    fn: Callable[[], T],
    *,
    attempts: int,
    base_delay_sec: float,
    label: str = "call",
) -> T:
    last: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            return fn()
        except Exception as e:
            last = e
            if i + 1 >= attempts:
                break
            delay = base_delay_sec * (2**i)
            logger.warning("%s failed (%s/%s): %s; retry in %.2fs", label, i + 1, attempts, e, delay)
            time.sleep(delay)
    assert last is not None
    raise last
