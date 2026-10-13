"""간단한 지수 백오프 재시도 헬퍼."""
from __future__ import annotations

import functools
import logging
import time
from typing import Callable, TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


def retry(
    attempts: int = 3,
    base_delay: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """실패 시 base_delay * 2^n 초씩 기다리며 최대 attempts번 시도한다."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        log.error("%s 실패 (%d/%d): %s", func.__qualname__, attempt, attempts, exc)
                        raise
                    delay = getattr(exc, "retry_after", None) or base_delay * 2 ** (attempt - 1)
                    log.warning(
                        "%s 실패 (%d/%d): %s — %.0f초 후 재시도",
                        func.__qualname__, attempt, attempts, exc, delay,
                    )
                    time.sleep(delay)
            raise AssertionError("unreachable")

        return wrapper

    return decorator
