# (c) Copyright Riverlane 2020-2025.
from pathlib import Path

from deltakit_visualise.utils.decorators import simple_file_cache


def test_simple_file_cache_creates_cache_file(tmp_path: Path):
    """Test that the cache file is created after function call."""
    # control
    assert len(list(tmp_path.iterdir())) == 0
    calls = []

    @simple_file_cache(cache_dir=tmp_path)
    def dummy_func(x, y):
        calls.append((x, y))

    dummy_func(1, 2)
    # Should have created a cache file
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    # Second call should not call function again (cache hit)
    dummy_func(1, 2)
    assert len(calls) == 1


def test_simple_file_cache_different_args(tmp_path: Path):
    """Test that different arguments create different cache files."""

    @simple_file_cache(cache_dir=tmp_path)
    def dummy_func(x):
        pass

    dummy_func(1)
    dummy_func(2)
    assert len(list(tmp_path.iterdir())) == 2
