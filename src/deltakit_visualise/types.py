# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Type definitions for deltakit-visualise."""

import json
from typing import Literal, TypedDict

from deltakit_compile.dialects.logical_assembly import OrientationAttr, OrientationEnum
from deltakit_compile.dialects.qcore import PauliAttr
from deltakit_compile.utilities.base_enums import BetterStrEnum
from xdsl.dialects.builtin import ArrayAttr


class SurfaceColour(BetterStrEnum):
    """Surface colour options."""

    RED = "RED"
    GREY = "GREY"
    BLUE = "BLUE"
    NONE = "NONE"

    @staticmethod
    def set_colour_scheme(basis: PauliAttr) -> "SurfaceColour":
        """Determine surface colour based on the basis."""
        if basis.data.name == "X":
            return SurfaceColour.RED
        if basis.data.name == "Z":
            return SurfaceColour.BLUE
        msg = f"Unsupported Pauli basis: {basis}"
        raise ValueError(msg)

    @staticmethod
    def set_colour_scheme_in_multi_pauli(
        basis: ArrayAttr[PauliAttr],
    ) -> "SurfaceColour":
        """Determine surface colour based on the basis."""
        # TODO: For more than 2 patches involved in a multi-Pauli measurement,
        # we may want to support a different colour scheme,
        names = {b.data.name for b in basis.data}
        if names == {"X"}:
            return SurfaceColour.BLUE
        if names == {"Z"}:
            return SurfaceColour.RED
        msg = f"Unsupported basis combination: {names}"
        raise ValueError(msg)


class SideColour(BetterStrEnum):
    """Sides colour options."""

    RED = "RED"
    BLUE = "BLUE"

    @staticmethod
    def set_colour_scheme(
        orientation: OrientationAttr,
    ) -> tuple["SideColour", "SideColour"]:
        """Determine sides colour based on the orientation."""
        if orientation.data == OrientationEnum.VERTICAL_Z:
            return (SideColour.RED, SideColour.BLUE)
        if orientation.data == OrientationEnum.HORIZONTAL_Z:
            return (SideColour.BLUE, SideColour.RED)
        msg = f"Unsupported orientation: {orientation}"
        raise ValueError(msg)


class SurfaceData(TypedDict):
    """Surface visualisation data item.

    Attributes:
        type: Literal discriminator indicating this is a surface item.
        id: Unique identifier for this surface.
        op_name: Name of the operation being visualised.
        colour: The colour to render the surface.
        location: The (x, y) coordinates of the surface's position.
        size: The (width, height) dimensions of the surface.
        startHeight: The height at which this surface starts.
    """

    type: Literal["surface"]
    id: str
    op_name: str
    colour: SurfaceColour
    location: tuple[float, float]
    size: tuple[int, int]
    startHeight: float


# SideVisibility defines the visibility of each side of a visualisation item.
# Defined as a TypedDict as +x and -x are not valid Python identifiers,
# so we cannot use a dataclass or a regular class for this purpose.
SideVisibility = TypedDict(
    "SideVisibility",
    {
        "+X": bool,
        "-X": bool,
        "+Y": bool,
        "-Y": bool,
    },
)


class SidesData(TypedDict):
    """Sides visualisation data item.

    Attributes:
        type: Literal discriminator indicating this is a side item.
        op_name: Name of the operation being visualised.
        colourScheme: A pair of colourScheme for the two sides.
        sides: Flags to show or hide sides, in the order (X, -X, Y, -Y).
        fromSurfaceId: Identifier of the surface this side starts from.
        toSurfaceId: Identifier of the surface this side connects to.
    """

    type: Literal["side"]
    op_name: str
    colourScheme: tuple[SideColour, SideColour]
    sides: SideVisibility
    fromSurfaceId: str
    toSurfaceId: str


# Union type for the 3D spacetime visualisation items
SpaceTimeVisualisationItem = SurfaceData | SidesData


class PlaquetteData(TypedDict):
    """Plaquette visualisation data item.

    Attributes:
        id: Unique identifier for this plaquette.
        weight: Number of data qubits involved in the plaquette.
        shape: Plaquette shaped based on qubits involved: square or semicircle.
        coordinates: List of qubit IDs (e.g. ["q_0", "q_1"]) that this plaquette involves.
        colour: The colour to render the plaquette.
    """

    id: int
    weight: int
    shape: Literal["square", "semicircle"]
    coordinates: list[str]
    colour: Literal["red", "blue"]


class PatchQubitData(TypedDict):
    """Qubit metadata for 2D patch visualisation."""

    id: str
    type: Literal["data", "ancilla"]
    coordinates: list[float]


class PatchData(TypedDict):
    """Container for plaquettes in one rendered patch."""

    plaquettes: list[PlaquetteData]


class PatchVisualisationItem(TypedDict):
    """2d Visualisation Data Item

    Attributes:
        round: The round number at which this surface code patch is selected.
        qubits: Qubits participating in this patch item.
        patches: The patches rendered for this round item.
    """

    round: int
    qubits: list[PatchQubitData]
    patches: list[PatchData]

    @staticmethod  # type: ignore[misc]
    def parse_list_from_json(payload: str) -> list["PatchVisualisationItem"]:
        """Parse a JSON list payload into patch visualisation items."""
        return json.loads(payload)
