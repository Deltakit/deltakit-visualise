"""Direction calculation utilities for patches and bridges."""

from deltakit_compile.dialects.logical_assembly import SurfaceCodeBasePatch
from deltakit_visualise.types import CorrelationDirection, SideVisibility
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
    """Return mapping of opposite patch edges (e.g., left-right, top-bottom)."""
    return {
        ("left", "right"): ("+X", "-X"),
        ("right", "left"): ("-X", "+X"),
        ("top", "bottom"): ("+Y", "-Y"),
        ("bottom", "top"): ("-Y", "+Y"),
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


def _get_bridge_correlation_directions(bridge_direction: str) -> list[CorrelationDirection]:
    """Get correlation directions for a bridge based on its movement axis.

    Bridge moving along ±Y: show ±Y vertical
    Bridge moving along ±X: show ±X horizontal
    """
    if bridge_direction in {"+Y", "-Y"}:
        return [
            {"orientation": "vertical", "direction": "+Y"},
            {"orientation": "vertical", "direction": "-Y"},
        ]
    # bridge_direction in {"+X", "-X"}
    return [
        {"orientation": "horizontal", "direction": "+X"},
        {"orientation": "horizontal", "direction": "-X"},
    ]


def _get_patch_correlation_directions(
    bridge_direction: str | None = None,
) -> list[CorrelationDirection]:
    """Get correlation directions for a patch.

    Patches always show ±Y (natural sides). If bridge_direction is perpendicular
    (±X), add that direction as well.
    """
    directions: list[CorrelationDirection] = [
        {"orientation": "vertical", "direction": "-Y"},
        {"orientation": "vertical", "direction": "+Y"},
    ]

    if bridge_direction and bridge_direction not in {"+Y", "-Y"}:
        directions.append(
            {
                "orientation": "horizontal",
                "direction": bridge_direction,
            }
        )

    return directions


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
