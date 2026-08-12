# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Geometry helpers for rectangular surface-code patches."""

from dataclasses import dataclass, replace

from deltakit_compile.dialects.logical_assembly import SurfaceCodeBasePatch


@dataclass(frozen=True)
class Coordinate:
    """A pair of coordinates."""

    x: float
    y: float


PatchEdge = frozenset[Coordinate]


@dataclass(frozen=True)
class PatchSides:
    """The four sides of a rectangular patch."""

    top: PatchEdge
    right: PatchEdge
    bottom: PatchEdge
    left: PatchEdge


@dataclass(frozen=True)
class VisibleSides:
    """Visibility flags for the four sides of a patch."""

    bottom: bool = True
    right: bool = True
    top: bool = True
    left: bool = True


def get_patch_sides(patch: SurfaceCodeBasePatch) -> PatchSides:
    """Return the sides of a rectangular patch."""
    placement = patch.placement_data
    if placement is None:
        msg = "Patch must have placement data to compute visible sides."
        raise ValueError(msg)

    x, y = placement
    width, height = patch.size_data

    bottom_left = Coordinate(x=x, y=y)
    bottom_right = Coordinate(x=x + width, y=y)
    top_right = Coordinate(x=x + width, y=y + height)
    top_left = Coordinate(x=x, y=y + height)

    return PatchSides(
        top=frozenset((top_right, top_left)),
        right=frozenset((bottom_right, top_right)),
        bottom=frozenset((bottom_left, bottom_right)),
        left=frozenset((top_left, bottom_left)),
    )


def get_visible_sides(
    logical_patches: list[SurfaceCodeBasePatch],
    bridge_patches: list[SurfaceCodeBasePatch],
) -> tuple[list[VisibleSides], list[VisibleSides]]:
    """Compute visible sides in bottom, right, top, left order."""

    all_patches = logical_patches + bridge_patches
    all_patch_sides = [get_patch_sides(patch) for patch in all_patches]

    # Start with all sides visible
    all_visible = [VisibleSides() for _ in all_patches]

    def hide_side(visible: VisibleSides, side: str) -> VisibleSides:
        return replace(visible, **{side: False})

    # Define opposing side relationships
    side_pairs = [
        ("left", "right"),
        ("right", "left"),
        ("top", "bottom"),
        ("bottom", "top"),
    ]

    # Compare each pair once (O(n²))
    for i, first in enumerate(all_patch_sides):
        for j in range(i + 1, len(all_patch_sides)):
            second = all_patch_sides[j]

            for first_side, second_side in side_pairs:
                first_edge = getattr(first, first_side)
                second_edge = getattr(second, second_side)

                if first_edge == second_edge:
                    all_visible[i] = hide_side(all_visible[i], first_side)
                    all_visible[j] = hide_side(all_visible[j], second_side)

    logical_count = len(logical_patches)

    return (
        all_visible[:logical_count],
        all_visible[logical_count:],
    )
