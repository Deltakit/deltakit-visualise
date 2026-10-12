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
    GrowOp,
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    OrientationAttr,
    OrientationEnum,
    PatchDeclarationOp,
    PrepareOp,
    RotateOp,
    ShrinkOp,
    StepOp,
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
    RotateColour,
    RotateData,
    SideColour,
    SidesData,
    SideVisibility,
    SpaceTimeVisualisationItem,
    StepData,
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
from deltakit_visualise.utils.patch_geometry import VisibleSides, get_visible_sides


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


def get_rotation_direction(
    start_location: tuple[float, float], end_location: tuple[float, float]
) -> str:
    """Get the signed axis ("+x", "-x", "+y" or "-y") along which a rotated patch is displaced."""
    dx = end_location[0] - start_location[0]
    dy = end_location[1] - start_location[1]
    if dx != 0 and dy == 0:
        return "+x" if dx > 0 else "-x"
    if dy != 0 and dx == 0:
        return "+y" if dy > 0 else "-y"
    msg = (
        "RotateOp must move the patch along exactly one axis, "
        f"but moved from {start_location} to {end_location}"
    )
    raise ValueError(msg)


def to_side_visibility(*visible: VisibleSides) -> SideVisibility:
    """Combine visible sides; a side is shown only if visible in all inputs."""
    return {
        "+X": all(v.right for v in visible),
        "-X": all(v.left for v in visible),
        "+Y": all(v.top for v in visible),
        "-Y": all(v.bottom for v in visible),
    }


def get_rotate_colour_scheme(
    orientation: OrientationAttr,
    rotation_direction: str,
) -> tuple[RotateColour, RotateColour, RotateColour, RotateColour]:
    """Get the rotate colour scheme, swapping positions 3/4 for x and 1/2 for y."""
    return RotateColour.set_colour_scheme(
        orientation=orientation, rotation_direction=rotation_direction
    )


def get_rotate_surface_colours(
    orientation: OrientationAttr, rotation_direction: str
) -> tuple[SurfaceColour | None, SurfaceColour | None]:
    """Get top and bottom surface colours for a patch rotation."""
    direction = rotation_direction.lstrip("+-")

    surface_colours = {
        (OrientationEnum.HORIZONTAL_Z, "x"): (
            SurfaceColour.RED,
            SurfaceColour.BLUE,
        ),
        (OrientationEnum.VERTICAL_Z, "y"): (
            SurfaceColour.RED,
            SurfaceColour.BLUE,
        ),
        (OrientationEnum.HORIZONTAL_Z, "y"): (
            SurfaceColour.BLUE,
            SurfaceColour.RED,
        ),
        (OrientationEnum.VERTICAL_Z, "x"): (
            SurfaceColour.BLUE,
            SurfaceColour.RED,
        ),
    }

    return surface_colours.get((orientation.data, direction), (None, None))


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
    colour_scheme = SideColour.set_colour_scheme(get_patch_orientation(patch_type))
    data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, IN_OP_ID),
        "op_name": op.name,
        "location": location,
        "colour": (
            SurfaceColour.BLUE if colour_scheme[1] == SideColour.BLUE else SurfaceColour.RED
        ),
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
    colour_scheme = SideColour.set_colour_scheme(get_patch_orientation(patch_type))

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
        "colourScheme": colour_scheme,
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
def handle_grow_operation(op: GrowOp, visualisation_data: list[SpaceTimeVisualisationItem]) -> None:
    """Handle GrowOp for visualisation."""
    from_patch = cast(SurfaceCodeBasePatch, op.patch.type)
    to_patch = cast(SurfaceCodeBasePatch, op.res.type)
    source_id = get_attr_str(op, IN_OP_ID)
    initial_to_patch_id = get_attr_str(op, OUT_OP_ID)
    final_to_patch_id = f"{initial_to_patch_id}_end"
    start_height = get_start_height(op)
    end_height = get_end_height(op)

    visualisation_data.extend(
        [
            # Create a transparent surface with the smaller size
            {
                "type": "surface",
                "id": source_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(from_patch),
                "size": get_patch_size(from_patch),
                "startHeight": start_height,
            },
            # Create a transparent surface with the bigger size
            {
                "type": "surface",
                "id": initial_to_patch_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(to_patch),
                "size": get_patch_size(to_patch),
                "startHeight": start_height,
            },
            # Create a resize operation connecting the smaller and bigger surfaces
            {
                "type": "resize",
                "op_name": op.name,
                "fromSurfaceId": source_id,
                "toSurfaceId": initial_to_patch_id,
            },
            # Create a transparent surface at the end height of the grown surface
            {
                "type": "surface",
                "id": final_to_patch_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(to_patch),
                "size": get_patch_size(to_patch),
                "startHeight": end_height,
            },
            # Create the sides connecting the initial and final surfaces of the grown patch
            {
                "type": "side",
                "op_name": op.name,
                "colourScheme": SideColour.set_colour_scheme(get_patch_orientation(to_patch)),
                "sides": {"+X": True, "-X": True, "+Y": True, "-Y": True},
                "fromSurfaceId": initial_to_patch_id,
                "toSurfaceId": final_to_patch_id,
            },
        ]
    )


@handle_operation.register
def handle_shrink_operation(
    op: ShrinkOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle ShrinkOp for visualisation."""
    from_patch = cast(SurfaceCodeBasePatch, op.patch.type)
    to_patch = cast(SurfaceCodeBasePatch, op.res.type)
    source_id = get_attr_str(op, IN_OP_ID)
    initial_to_patch_id = get_attr_str(op, OUT_OP_ID)
    final_to_patch_id = f"{initial_to_patch_id}_end"
    start_height = get_start_height(op)
    end_height = get_end_height(op)

    visualisation_data.extend(
        [
            # Create the initial surface of the patch being shrunk
            {
                "type": "surface",
                "id": source_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(from_patch),
                "size": get_patch_size(from_patch),
                "startHeight": start_height,
            },
            # Create the initial surface of the patch after shrinking
            {
                "type": "surface",
                "id": initial_to_patch_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(to_patch),
                "size": get_patch_size(to_patch),
                "startHeight": start_height,
            },
            # Create a resize operation connecting the initial and final surfaces
            {
                "type": "resize",
                "op_name": op.name,
                "fromSurfaceId": source_id,
                "toSurfaceId": initial_to_patch_id,
            },
            # Create the final surface of the patch after shrinking
            {
                "type": "surface",
                "id": final_to_patch_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": get_patch_location(to_patch),
                "size": get_patch_size(to_patch),
                "startHeight": end_height,
            },
            # Create the sides connecting the initial and final surfaces of the shrunk patch
            {
                "type": "side",
                "op_name": op.name,
                "colourScheme": SideColour.set_colour_scheme(get_patch_orientation(to_patch)),
                "sides": {"+X": True, "-X": True, "+Y": True, "-Y": True},
                "fromSurfaceId": initial_to_patch_id,
                "toSurfaceId": final_to_patch_id,
            },
        ]
    )


@handle_operation.register
def handle_step_operation(op: StepOp, visualisation_data: list[SpaceTimeVisualisationItem]) -> None:
    """Handle StepOp for visualisation."""
    start_patch_type = cast(SurfaceCodeBasePatch, op.patch.type)
    end_patch_type = cast(SurfaceCodeBasePatch, op.res.type)
    start_location = get_patch_location(start_patch_type)
    end_location = get_patch_location(end_patch_type)
    size = get_patch_size(start_patch_type)
    orientation = get_patch_orientation(start_patch_type)
    colour_scheme = SideColour.set_colour_scheme(orientation)
    surface_colour = (
        SurfaceColour.BLUE if colour_scheme[1] == SideColour.BLUE else SurfaceColour.RED
    )

    # Neutral surfaces show the patch before and after the step.
    # IN_OP_ID is a fresh ID (not chained from previous op) so this surface stands alone.
    start_gap_data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, IN_OP_ID),
        "op_name": op.name,
        "colour": surface_colour,
        "location": start_location,
        "size": size,
        "startHeight": get_start_height(op),
    }

    surface_data: StepData = {
        "type": "step",
        "op_name": op.name,
        "colourScheme": colour_scheme,
        "sides": {"+X": True, "-X": True, "+Y": True, "-Y": True},
        "fromSurfaceId": get_attr_str(op, IN_OP_ID),
        "toSurfaceId": get_attr_str(op, OUT_OP_ID),
    }
    end_gap_data: SurfaceData = {
        "type": "surface",
        "id": get_attr_str(op, OUT_OP_ID),
        "op_name": op.name,
        "colour": surface_colour,
        "location": end_location,
        "size": size,
        "startHeight": get_end_height(op),
    }

    visualisation_data.append(start_gap_data)
    visualisation_data.append(surface_data)
    visualisation_data.append(end_gap_data)


def append_rotate_bridge_data(
    op: RotateOp,
    bridge_patch: SurfaceCodeBasePatch,
    bridge_sides: SideVisibility,
    visualisation_data: list[SpaceTimeVisualisationItem],
) -> None:
    """Append bridge surfaces and sides for a rotate operation."""
    from_patch = cast(SurfaceCodeBasePatch, op.patch.type)
    to_patch = cast(SurfaceCodeBasePatch, op.res.type)
    from_orientation = get_patch_orientation(from_patch)
    to_orientation = get_patch_orientation(to_patch)
    from_start_id = get_attr_str(op, IN_OP_ID)
    from_mid_id = f"{from_start_id}_rotate_midpoint"
    from_top_id = f"{from_start_id}_rotate_top"
    rotation_direction = get_rotation_direction(
        get_patch_location(from_patch), get_patch_location(to_patch)
    )
    rotate_top_surface, rotate_bottom_surface = get_rotate_surface_colours(
        from_orientation, rotation_direction
    )
    if rotate_top_surface is None or rotate_bottom_surface is None:
        msg = (
            "Unsupported rotation orientation or direction: "
            f"{from_orientation} and {rotation_direction}"
        )
        raise ValueError(msg)

    bridge_start = get_start_height(op)
    bridge_mid = bridge_start + (get_end_height(op) - get_start_height(op)) // 2
    bridge_end = get_end_height(op)
    bridge_start_id = f"{from_start_id}_to_{bridge_start}"
    bridge_mid_id = f"{from_mid_id}_to_{bridge_mid}"
    bridge_end_id = f"{from_top_id}_to_{bridge_end}"
    location = get_patch_location(bridge_patch)
    size = get_patch_size(bridge_patch)

    visualisation_data.extend(
        [
            {
                "type": "surface",
                "id": bridge_start_id,
                "op_name": op.name,
                "colour": rotate_bottom_surface,
                "location": location,
                "size": size,
                "startHeight": bridge_start,
            },
            {
                "type": "surface",
                "id": bridge_mid_id,
                "op_name": op.name,
                "colour": SurfaceColour.NONE,
                "location": location,
                "size": size,
                "startHeight": bridge_mid,
            },
            {
                "type": "surface",
                "id": bridge_end_id,
                "op_name": op.name,
                "colour": rotate_top_surface,
                "location": location,
                "size": size,
                "startHeight": bridge_end,
            },
            {
                "type": "side",
                "op_name": op.name,
                "colourScheme": SideColour.set_colour_scheme(from_orientation),
                "sides": bridge_sides,
                "fromSurfaceId": bridge_start_id,
                "toSurfaceId": bridge_mid_id,
            },
            {
                "type": "side",
                "op_name": op.name,
                "colourScheme": SideColour.set_colour_scheme(to_orientation),
                "sides": bridge_sides,
                "fromSurfaceId": bridge_mid_id,
                "toSurfaceId": bridge_end_id,
            },
        ]
    )


@handle_operation.register
def handle_rotate_operation(
    op: RotateOp, visualisation_data: list[SpaceTimeVisualisationItem]
) -> None:
    """Handle RotateOp for visualisation."""
    from_patch = cast(SurfaceCodeBasePatch, op.patch.type)
    to_patch = cast(SurfaceCodeBasePatch, op.res.type)

    from_location = get_patch_location(from_patch)
    to_location = get_patch_location(to_patch)
    rotation_direction = get_rotation_direction(from_location, to_location)
    from_size = get_patch_size(from_patch)
    to_size = get_patch_size(to_patch)
    from_orientation = get_patch_orientation(from_patch)
    to_orientation = get_patch_orientation(to_patch)

    from_start_id = get_attr_str(op, IN_OP_ID)
    from_mid_id = f"{from_start_id}_rotate_midpoint"
    from_top_id = f"{from_start_id}_rotate_top"
    to_start_id = get_attr_str(op, OUT_OP_ID)
    to_mid_id = f"{to_start_id}_rotate_midpoint"
    to_top_id = f"{to_start_id}_rotate_top"

    bridge_patch_types = [cast(SurfaceCodeBasePatch, bridge.type) for bridge in op.bridge_patches]
    (from_side,), bridge_from_sides = get_visible_sides([from_patch], bridge_patch_types)
    (to_side,), bridge_to_sides = get_visible_sides([to_patch], bridge_patch_types)
    from_sides = to_side_visibility(from_side)
    to_sides = to_side_visibility(to_side)

    rotate_top_surface, rotate_bottom_surface = get_rotate_surface_colours(
        from_orientation, rotation_direction
    )
    if rotate_top_surface is None or rotate_bottom_surface is None:
        msg = (
            "Unsupported rotation orientation or direction: "
            f"{from_orientation} and {rotation_direction}"
        )
        raise ValueError(msg)

    # Add transparent base for the rotate operation for initial patch
    rotate_surface_from_start: SurfaceData = {
        "type": "surface",
        "id": from_start_id,
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": from_location,
        "size": from_size,
        "startHeight": get_start_height(op),
    }
    # Add transparent mid surface for the rotate operation for initial patch
    rotate_surface_from_mid: SurfaceData = {
        "type": "surface",
        "id": from_mid_id,
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": from_location,
        "size": from_size,
        "startHeight": get_start_height(op) + (get_end_height(op) - get_start_height(op)) // 2,
    }
    # Add top surface for the rotate operation for initial patch with colour
    # based on the rotation direction and orientation of the patch
    rotate_surface_from_top: SurfaceData = {
        "type": "surface",
        "id": from_top_id,
        "op_name": op.name,
        "colour": rotate_top_surface,
        "location": from_location,
        "size": from_size,
        "startHeight": get_end_height(op),
    }
    # Add a sides element for the rotate operation for initial patch
    rotate_side_from: SidesData = {
        "type": "side",
        "op_name": op.name,
        "colourScheme": SideColour.set_colour_scheme(from_orientation),
        "sides": from_sides,
        "fromSurfaceId": from_start_id,
        "toSurfaceId": from_mid_id,
    }
    # Add rotate operation with colour scheme with different sequence
    # compared to sides element
    rotate_from: RotateData = {
        "type": "rotate",
        "op_name": op.name,
        "colourScheme": get_rotate_colour_scheme(
            orientation=from_orientation, rotation_direction=rotation_direction
        ),
        "sides": from_sides,
        "fromSurfaceId": from_mid_id,
        "toSurfaceId": from_top_id,
    }
    visualisation_data.append(rotate_surface_from_start)
    visualisation_data.append(rotate_surface_from_mid)
    visualisation_data.append(rotate_surface_from_top)
    visualisation_data.append(rotate_side_from)
    visualisation_data.append(rotate_from)

    for bridge_patch, bridge_from_side, bridge_to_side in zip(
        bridge_patch_types, bridge_from_sides, bridge_to_sides, strict=True
    ):
        bridge_sides = to_side_visibility(bridge_from_side, bridge_to_side)
        append_rotate_bridge_data(op, bridge_patch, bridge_sides, visualisation_data)

    # Add base surface for the rotate operation for the target patch
    rotate_surface_to_start: SurfaceData = {
        "type": "surface",
        "id": to_start_id,
        "op_name": op.name,
        "colour": rotate_bottom_surface,
        "location": to_location,
        "size": to_size,
        "startHeight": get_start_height(op),
    }
    # Add mid surface for the rotate operation for the target patch (transparent)
    rotate_surface_to_mid: SurfaceData = {
        "type": "surface",
        "id": to_mid_id,
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": to_location,
        "size": to_size,
        "startHeight": get_start_height(op) + (get_end_height(op) - get_start_height(op)) // 2,
    }
    # Add top surface for the rotate operation for the target patch (transparent)
    rotate_surface_to_top: SurfaceData = {
        "type": "surface",
        "id": to_top_id,
        "op_name": op.name,
        "colour": SurfaceColour.NONE,
        "location": to_location,
        "size": to_size,
        "startHeight": get_end_height(op),
    }
    # Add rotate operation for the target patch using its orientation and rotation direction.
    rotate_to: RotateData = {
        "type": "rotate",
        "op_name": op.name,
        "colourScheme": RotateColour.set_rotated_colour_scheme(
            orientation=to_orientation, rotation_direction=rotation_direction
        ),
        "sides": to_sides,
        "fromSurfaceId": to_start_id,
        "toSurfaceId": to_mid_id,
    }
    # Add sides for the rotate operation for the target patch connecting the mid and top surfaces
    rotate_side_to: SidesData = {
        "type": "side",
        "op_name": op.name,
        "colourScheme": SideColour.set_colour_scheme(to_orientation),
        "sides": to_sides,
        "fromSurfaceId": to_mid_id,
        "toSurfaceId": to_top_id,
    }

    visualisation_data.append(rotate_surface_to_start)
    visualisation_data.append(rotate_surface_to_mid)
    visualisation_data.append(rotate_surface_to_top)
    visualisation_data.append(rotate_side_to)
    visualisation_data.append(rotate_to)


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
