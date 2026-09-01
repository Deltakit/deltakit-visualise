# (c) Copyright Riverlane 2025-2026. All rights reserved.
import hashlib
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar

from deltakit_visualise.constants import CACHE_DIR

from .logging import _stream_handler

# logging
logger = logging.Logger(__name__)
logger.addHandler(_stream_handler)


P = ParamSpec("P")
RetType = TypeVar("RetType")


def simple_file_cache(
    cache_dir: Path = CACHE_DIR / ".vis_cache",
) -> Callable[[Callable[P, RetType]], Callable[P, None]]:
    """Cache decorator that persists name and operand values of wrapped function as a hashed file.

    Function's return value is ignored.

    Args:
        cache_dir: Local cache directory

    Returns:
        A decorator that wraps the given function with file-based caching
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            """Logic for wrapped function."""
            # create cache directory if it doesn't exist
            cache_dir.mkdir(exist_ok=True, parents=True)

            # create unique cache key from function name and arguments
            key_data = f"{func.__name__}{args}{kwargs}"
            # MD5 is used only to derive a cache filename, not for security.
            cache_key = hashlib.md5(
                key_data.encode(), usedforsecurity=False
            ).hexdigest()
            cache_file = cache_dir / cache_key

            # check if cache exists
            if cache_file.exists():
                return

            # execute function without caching result
            func(*args, **kwargs)
            with cache_file.open("w") as f:
                f.write("")
            return

        return wrapper

    return decorator
