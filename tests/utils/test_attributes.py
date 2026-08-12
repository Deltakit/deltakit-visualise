# (c) Copyright Riverlane 2020-2026.
"""Tests for attribute utility functions."""

import pytest
from deltakit_compile.dialects.logical_assembly import (
    OrientationEnum,
    PatchDeclarationOp,
    PlacementAttr,
    RotatedPlanarPatchType,
)
from xdsl.dialects.builtin import NoneAttr

from deltakit_visualise.utils.attributes import (
    get_attr_str,
    get_patch_location,
    get_patch_orientation,
    get_string_list_attr,
)
from tests.conftest import make_size


def test_get_attr_str_returns_default_when_missing():
    """Test that get_attr_str returns default when attribute is not present."""
    patch_type = RotatedPlanarPatchType(
        make_size(3, 3), PlacementAttr([0, 0], OrientationEnum.VERTICAL_Z)
    )
    op = PatchDeclarationOp(patch_type)

    assert get_attr_str(op, "nonexistent_key") == ""
    assert get_attr_str(op, "nonexistent_key", "fallback") == "fallback"


def test_get_string_list_attr_returns_empty_when_missing():
    """Test that get_string_list_attr returns empty list when attribute is not present."""
    patch_type = RotatedPlanarPatchType(
        make_size(3, 3), PlacementAttr([0, 0], OrientationEnum.VERTICAL_Z)
    )
    op = PatchDeclarationOp(patch_type)

    assert get_string_list_attr(op, "nonexistent_key") == []


def test_get_patch_location_raises_for_none_placement():
    """Test that get_patch_location raises NotImplementedError for NoneAttr placement."""
    patch_type = RotatedPlanarPatchType(make_size(3, 3), NoneAttr())

    with pytest.raises(NotImplementedError, match="Patch placement data is not available"):
        get_patch_location(patch_type)


def test_get_patch_orientation_raises_for_none_placement():
    """Test that get_patch_orientation raises NotImplementedError for NoneAttr placement."""
    patch_type = RotatedPlanarPatchType(make_size(3, 3), NoneAttr())

    with pytest.raises(NotImplementedError, match="Patch placement data is not available"):
        get_patch_orientation(patch_type)
