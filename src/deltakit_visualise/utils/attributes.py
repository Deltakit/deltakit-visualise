# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Utility functions for attribute handling in deltakit-visualise."""

from deltakit_compile.dialects.logical_assembly import (
    OrientationAttr,
    SurfaceCodeBasePatch,
)
from xdsl.dialects.builtin import ArrayAttr, NoneAttr, StringAttr
from xdsl.ir import Operation

from deltakit_visualise.constants import (
    IN_BRIDGE_PATCHES_ID,
    IN_LOGICAL_PATCHES_ID,
    OUT_BRIDGE_PATCHES_ID,
    OUT_LOGICAL_PATCHES_ID,
)


def get_attr_str(op: Operation, key: str, default: str = "") -> str:
    """Get a string attribute value from an operation, returning the raw string data."""
    attr = op.attributes.get(key)
    if isinstance(attr, StringAttr):
        return attr.data
    return default


def get_string_list_attr(op: Operation, key: str) -> list[str]:
    """Get a list of strings from an ArrayAttr[StringAttr] attribute."""
    attr = op.attributes.get(key)
    if attr is None:
        return []
    assert isinstance(attr, ArrayAttr)
    return [item.data for item in attr]


def get_in_logical_patch_ids(op: Operation) -> list[str]:
    """Get the input logical patch IDs from an operation."""
    return get_string_list_attr(op, IN_LOGICAL_PATCHES_ID)


def get_out_logical_patch_ids(op: Operation) -> list[str]:
    """Get the output logical patch IDs from an operation."""
    return get_string_list_attr(op, OUT_LOGICAL_PATCHES_ID)


def get_in_bridge_patch_ids(op: Operation) -> list[str]:
    """Get the input bridge patch IDs from an operation."""
    return get_string_list_attr(op, IN_BRIDGE_PATCHES_ID)


def get_out_bridge_patch_ids(op: Operation) -> list[str]:
    """Get the output bridge patch IDs from an operation."""
    return get_string_list_attr(op, OUT_BRIDGE_PATCHES_ID)


def get_patch_location(patch_type: SurfaceCodeBasePatch) -> tuple[float, float]:
    """Get the location from a surface code patch type."""
    placement = patch_type.placement
    if isinstance(placement, NoneAttr):
        msg = f"Patch placement data is not available for {patch_type}"
        raise NotImplementedError(msg)
    return (
        placement.location.data[0].value.data,
        placement.location.data[1].value.data,
    )


def get_patch_size(
    patch_type: SurfaceCodeBasePatch,
) -> tuple[int, int]:
    """Get the size from a surface code patch type."""
    return (patch_type.size.data[0].data, patch_type.size.data[1].data)


def get_patch_orientation(
    patch_type: SurfaceCodeBasePatch,
) -> OrientationAttr:
    """Get the orientation from a surface code patch type."""
    placement = patch_type.placement
    if isinstance(placement, NoneAttr):
        msg = f"Patch placement data is not available for {patch_type}"
        raise NotImplementedError(msg)
    return placement.orientation
