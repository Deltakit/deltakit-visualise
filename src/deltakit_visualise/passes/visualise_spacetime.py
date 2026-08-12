# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""
This is a compiler pass that walks the AST to make it ready for visualisation.
using the xDSL framework patterns for visualisation purposes.
"""

import json
from dataclasses import dataclass
from functools import singledispatch
from typing import cast

from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    PatchDeclarationOp,
    PrepareOp,
    SurfaceCodeBasePatch,
)
from deltakit_compile.dialects.qstruct import OutputOp, ParallelOp, YieldOp
from xdsl.dialects.builtin import FloatAttr as FloatAttr  # noqa: PLC0414
from xdsl.dialects.builtin import IntAttr, ModuleOp, StringAttr
from xdsl.ir import Operation
from xdsl.passes import ModulePass

from deltakit_visualise.constants import (
    END_HEIGHT_ATTR,
    IN_OP_ID,
    OUT_OP_ID,
    START_HEIGHT_ATTR,
    VISUALISE_SPACETIME_DATA,
)
from deltakit_visualise.types import (
    SideColour,
    SidesData,
    SpaceTimeVisualisationItem,
    SurfaceColour,
    SurfaceData,
)
from deltakit_visualise.utils.attributes import (
    get_attr_str,
    get_in_bridge_patch_ids,
    get_in_logical_patch_ids,
    get_out_bridge_patch_ids,
    get_out_logical_patch_ids,
    get_patch_location,
    get_patch_orientation,
    get_patch_size,
)
from deltakit_visualise.utils.patch_geometry import get_visible_sides


def get_start_height(op: Operation) -> float:
    """Get the start_height attribute from an operation."""
    attr = op.attributes.get(START_HEIGHT_ATTR)
    if isinstance(attr, IntAttr):
        return float(attr.data)
    if isinstance(attr, FloatAttr):
        return attr.value.data
    msg = f"Operation {op.name} is missing a valid {START_HEIGHT_ATTR} attribute"
    raise ValueError(msg)


def get_end_height(op: Operation) -> float:
    """Get the end_height attribute from an operation."""
    attr = op.attributes.get(END_HEIGHT_ATTR)
    if isinstance(attr, IntAttr):
        return float(attr.data)
    if isinstance(attr, FloatAttr):
        return attr.value.data
    msg = f"Operation {op.name} is missing a valid {END_HEIGHT_ATTR} attribute"
    raise ValueError(msg)


@singledispatch
def handle_operation(_op: Operation, _visualisation_data: list[SpaceTimeVisualisationItem]) -> None:
    """
    Generic operation handler using single dispatch.
    This function dispatches to specific handlers based on the type of the operation.
    If no specific handler is registered for an operation type, it raises NotImplementedError.
    """
    msg = f"Operation {_op.name} is not handled"
    raise NotImplementedError(msg)


@handle_operation.register
def handle_parallel_operation(
    op: ParallelOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Parallel op has no effect on visualisation."""


@handle_operation.register
def handle_yield_operation(
    op: YieldOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Yield op has no effect on visualisation."""


@handle_operation.register
def handle_output_operation(
    op: OutputOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Output terminator has no effect on visualisation."""


@handle_operation.register
def handle_patch_declaration(
    op: PatchDeclarationOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle PatchDeclarationOp for visualisation."""
    patch_type = cast(SurfaceCodeBasePatch, op.res.type)
    location = get_patch_location(patch_type)
    size = get_patch_size(patch_type)
    data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, IN_OP_ID),
        "op_name": op.name,
        "location": location,
        "colour": SurfaceColour.GREY,
        "size": size,
        "startHeight": get_start_height(op),
    }
    visualisation_data.append(data)


@handle_operation.register
def handle_prepare_operation(
    op: PrepareOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle PrepareOp for visualisation."""
    patch_type = cast(SurfaceCodeBasePatch, op.patch.type)
    location = get_patch_location(patch_type)
    size = get_patch_size(patch_type)
    data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, IN_OP_ID),
        "op_name": op.name,
        "location": location,
        "colour": SurfaceColour.set_colour_scheme(op.basis),
        "size": size,
        "startHeight": get_start_height(op),
    }
    visualisation_data.append(data)


@handle_operation.register
def handle_measure_stabiliser(
    op: MeasStabOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle MeasStabOp for visualisation."""
    patch_type = cast(SurfaceCodeBasePatch, op.patch.type)
    location = get_patch_location(patch_type)
    size = get_patch_size(patch_type)
    orientation = get_patch_orientation(patch_type)

    # NONE surface at the start to show the gap before measurement begins
    # (sequential height tracking).
    # IN_OP_ID is a fresh ID (not chained from previous op) so this surface stands alone.
    start_gap_data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, IN_OP_ID),
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": location,
        "size": size,
        "startHeight": get_start_height(op),
    }

    surface_data: SidesData = {
        "type": "side",
        "op_name": op.name,
        "colourScheme": SideColour.set_colour_scheme(orientation),
        "sides": {"+X": True, "-X": True, "+Y": True, "-Y": True},
        "fromSurfaceId": get_attr_str(op, IN_OP_ID),
        "toSurfaceId": get_attr_str(op, OUT_OP_ID),
    }
    end_gap_data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, OUT_OP_ID),
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": location,
        "size": size,
        "startHeight": get_end_height(op),
    }
    visualisation_data.append(start_gap_data)
    visualisation_data.append(surface_data)
    visualisation_data.append(end_gap_data)


@handle_operation.register
def handle_measure_operation(
    op: MeasureOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle MeasureOp for visualisation."""
    patch_type = cast(SurfaceCodeBasePatch, op.patch.type)
    location = get_patch_location(patch_type)
    size = get_patch_size(patch_type)
    data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, OUT_OP_ID),
        "op_name": op.name,
        "location": location,
        "colour": SurfaceColour.set_colour_scheme(op.basis),
        "size": size,
        "startHeight": get_start_height(op),
    }
    visualisation_data.append(data)


@handle_operation.register
def handle_multi_pauli_measurement(
    op: MultiPauliMeasOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle MultiPauliMeasOp for visualisation."""
    results: list[SpaceTimeVisualisationItem] = []
    basis = op.basis

    logical_patches = [cast(SurfaceCodeBasePatch, patch.type) for patch in op.logical_patches]
    bridge_patches = [cast(SurfaceCodeBasePatch, patch.type) for patch in op.bridge_patches]
    logical_sides, bridge_sides = get_visible_sides(logical_patches, bridge_patches)

    # Process all logical patches
    # IN_LOGICAL_PATCHES_ID holds fresh IDs (not chained) so each start surface stands alone.
    in_logical_patch_ids = get_in_logical_patch_ids(op)
    out_logical_patch_ids = get_out_logical_patch_ids(op)
    for logical_patch, logical_side, in_logical_patch_id, out_logical_patch_id in zip(
        op.logical_patches,
        logical_sides,
        in_logical_patch_ids,
        out_logical_patch_ids,
        strict=True,
    ):
        patch_type = cast(SurfaceCodeBasePatch, logical_patch.type)
        location = get_patch_location(patch_type)
        size = get_patch_size(patch_type)
        orientation = get_patch_orientation(patch_type)

        # NONE surface at the start — IN_LOGICAL_PATCHES_ID is fresh so it stands alone.
        logical_surface_result_start: SurfaceData = {
            "type": "surface",
            "id": in_logical_patch_id,
            "op_name": op.name,
            "colour": SurfaceColour.NONE,
            "location": location,
            "size": size,
            "startHeight": get_start_height(op),
        }
        logical_sides_result: SidesData = {
            "type": "side",
            "op_name": op.name,
            "colourScheme": SideColour.set_colour_scheme(orientation),
            "sides": {
                "+X": logical_side.right,
                "-X": logical_side.left,
                "+Y": logical_side.top,
                "-Y": logical_side.bottom,
            },
            "fromSurfaceId": in_logical_patch_id,
            "toSurfaceId": out_logical_patch_id,
        }
        logical_surface_result_end: SurfaceData = {
            "type": "surface",
            "id": out_logical_patch_id,
            "op_name": op.name,
            "colour": SurfaceColour.NONE,
            "location": location,
            "size": size,
            "startHeight": get_end_height(op),
        }
        results.append(logical_surface_result_start)
        results.append(logical_sides_result)
        results.append(logical_surface_result_end)

    # Process all bridge patches
    in_bridge_patch_ids = get_in_bridge_patch_ids(op)
    out_bridge_patch_ids = get_out_bridge_patch_ids(op)
    for bridge_patch, bridge_side, in_bridge_patch_id, out_bridge_patch_id in zip(
        op.bridge_patches,
        bridge_sides,
        in_bridge_patch_ids,
        out_bridge_patch_ids,
        strict=True,
    ):
        patch_type = cast(SurfaceCodeBasePatch, bridge_patch.type)
        location = get_patch_location(patch_type)
        size = get_patch_size(patch_type)
        orientation = get_patch_orientation(patch_type)

        bridge_surface_result_start: SurfaceData = {
            "type": "surface",
            "id": in_bridge_patch_id,
            "op_name": op.name,
            "colour": SurfaceColour.set_colour_scheme_in_multi_pauli(basis),
            "location": location,
            "size": size,
            "startHeight": get_start_height(op),
        }
        # Add sides
        bridge_sides_result: SidesData = {
            "type": "side",
            "op_name": op.name,
            "colourScheme": SideColour.set_colour_scheme(orientation),
            "sides": {
                "+X": bridge_side.right,
                "-X": bridge_side.left,
                "+Y": bridge_side.top,
                "-Y": bridge_side.bottom,
            },
            "fromSurfaceId": in_bridge_patch_id,
            "toSurfaceId": out_bridge_patch_id,
        }
        bridge_surface_result_end: SurfaceData = {
            "type": "surface",
            "id": out_bridge_patch_id,
            "op_name": op.name,
            "colour": SurfaceColour.set_colour_scheme_in_multi_pauli(basis),
            "location": location,
            "size": size,
            "startHeight": get_end_height(op),
        }
        results.append(bridge_surface_result_start)
        results.append(bridge_sides_result)
        results.append(bridge_surface_result_end)

    visualisation_data.extend(results)


@handle_operation.register
def handle_module_operation(
    op: ModuleOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle ModuleOp - ignored in visualisation."""
    # ModuleOp is the top-level container and does not directly contribute to visualisation,
    # so we can choose to ignore it or handle it as needed.


# Pass implementation
@dataclass(frozen=True)
class VisualiseSpacetime(ModulePass):
    """Deltakit-visualise pass that walks the AST and collects visualisation data."""

    name = "visualise-spacetime"

    def apply(self, _context, op: ModuleOp) -> None:
        """Apply the deltakit-visualise pass to the module using single dispatch."""
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        for child in op.walk():
            handle_operation(child, visualisation_data)
        # Store the visualisation_data on the module for later retrieval
        op.attributes[VISUALISE_SPACETIME_DATA] = StringAttr(json.dumps(visualisation_data))
