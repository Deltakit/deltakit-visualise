# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Direction calculation utilities for patches and bridges."""

from deltakit_compile.dialects.logical_assembly import SurfaceCodeBasePatch

from deltakit_visualise.types import SideVisibility
from deltakit_visualise.utils.patch_geometry import VisibleSides, get_patch_sides


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


def _direction_to_surface(orientation: str, direction: str) -> str:
    """Convert orientation and direction to surface notation.

    In this coordinate system, Y is mapped to Z (vertical/height axis) and Z is
    mapped to Y.

    Examples:
        ("horizontal", "+X") → "Y+X" (Y spans completely, +X direction)
        ("horizontal", "-X") → "Y-X" (Y spans completely, -X direction)
        ("vertical", "+Y") → "X+Z" (X spans completely, +Z direction,
            where Z is vertical)
        ("vertical", "-Y") → "X-Z" (X spans completely, -Z direction,
            where Z is vertical)
    """
    if orientation == "horizontal":
        return f"Y{direction}"
    # vertical orientation: map Y to Z since Y is the vertical axis
    # Convert +Y to +Z and -Y to -Z
    mapped_direction = direction.replace("Y", "Z")
    return f"X{mapped_direction}"


def get_patch_connection_directions(
    patch: SurfaceCodeBasePatch, other_patch: SurfaceCodeBasePatch
) -> tuple[str, str] | None:
    """Return the facing directions when two patches share an edge."""
    patch_sides = get_patch_sides(patch)
    other_sides = get_patch_sides(other_patch)

    for (patch_side, other_side), (patch_dir, other_dir) in _get_opposing_sides_map().items():
        if getattr(patch_sides, patch_side) == getattr(other_sides, other_side):
            return patch_dir, other_dir
    return None


def _get_opposing_sides_map() -> dict[tuple[str, str], tuple[str, str]]:
    """Return mapping of opposite patch edges (e.g., left-right, top-bottom).

    Each tuple maps: when patch.side == other.side, the directions are:
    (direction patch faces towards other, direction other faces towards patch)
    """
    return {
        ("left", "right"): ("-X", "+X"),  # patch left touches other right
        ("right", "left"): ("+X", "-X"),  # patch right touches other left
        ("top", "bottom"): ("+Y", "-Y"),  # patch top touches other bottom
        ("bottom", "top"): ("-Y", "+Y"),  # patch bottom touches other top
    }


def _get_opposite_direction(direction: str) -> str:
    """Get opposite direction: +X ↔ -X, +Y ↔ -Y."""
    if direction == "+X":
        return "-X"
    if direction == "-X":
        return "+X"
    if direction == "+Y":
        return "-Y"
    if direction == "-Y":
        return "+Y"
    return direction


def _get_bridge_correlation_directions(
    bridge_direction: str,
) -> list[str]:
    """Get correlation surfaces for a bridge based on patch connection direction.

    The surfaces depend on the direction patches are connecting (not growth):
    - If connecting via ±Y (vertical, blue sides): Use X-based surfaces with
      directional extent
    - If connecting via ±X (horizontal, red sides): Use only vertical surfaces X±Z

    Args:
        bridge_direction: Direction bridge connects patches (±X or ±Y)

    Note: Y is vertical (mapped to Z); Z is horizontal (mapped to Y).
    """
    if bridge_direction in {"+Y", "-Y"}:
        # Vertical connection (±Y): show X-based surfaces with extent in ±Y
        return ["X+Y", "X-Y"]
    # Horizontal connection (±X): show only vertical surfaces
    return ["X+Z", "X-Z"]


def _get_patch_correlation_directions(
    bridge_direction: str | None = None,
) -> list[str]:
    """Get correlation surfaces for a patch in a multi-Pauli measurement.

    The surfaces depend on the direction patches are connecting (not growth):
    - If connecting via ±Y (vertical, blue sides): Use X-based surfaces with
      directional extent
    - If connecting via ±X (horizontal, red sides): Use only vertical surfaces X±Z

    Args:
        bridge_direction: Direction patch faces towards bridge (±X or ±Y)

    Note: Y is vertical (mapped to Z); Z is horizontal (mapped to Y).
    """
    if bridge_direction in {"+Y", "-Y"}:
        # Vertical connection: span X with extent in ±Y and ±Z
        if bridge_direction == "+Y":
            return ["X+Y", "X-Z"]
        # "-Y"
        return ["X-Y", "X+Z"]
    if bridge_direction in {"+X", "-X"}:
        # Horizontal connection: use only vertical surfaces
        return ["X+Z", "X-Z"]
    # No bridge: vertical surfaces spanning X
    return ["X+Z", "X-Z"]


def to_side_visibility(*visible: VisibleSides) -> SideVisibility:
    """Combine visible sides; a side is shown only if visible in all inputs."""
    if not visible:
        return {"+X": False, "-X": False, "+Y": False, "-Y": False}
    return {
        "+X": all(v.right for v in visible),
        "-X": all(v.left for v in visible),
        "+Y": all(v.top for v in visible),
        "-Y": all(v.bottom for v in visible),
    }
