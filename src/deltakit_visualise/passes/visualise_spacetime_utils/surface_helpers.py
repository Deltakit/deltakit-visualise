# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Surface and colour scheme utilities."""

from deltakit_compile.dialects.logical_assembly import OrientationAttr, OrientationEnum

from deltakit_visualise.types import RotateColour, SurfaceColour


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
