"""Correlation surface helpers for multi-Pauli measurements."""

from itertools import pairwise
from typing import cast, Literal

from deltakit_compile.dialects.logical_assembly import SurfaceCodeBasePatch
from deltakit_compile.dialects.sobs import LocateUnplacedObservableOp
from deltakit_compile.dialects.qcore import PauliAttr
from xdsl.ir import SSAValue

from deltakit_visualise.types import CorrelationData, CorrelationDirection, SurfaceColour, SpaceTimeVisualisationItem
from deltakit_visualise.utils.attributes import (
    get_in_bridge_patch_ids,
    get_in_logical_patch_ids,
    get_out_bridge_patch_ids,
    get_out_logical_patch_ids,
)

from .direction_helpers import (
    _get_bridge_correlation_directions,
    _get_opposite_direction,
    _get_patch_correlation_directions,
    get_patch_connection_directions,
)


def make_side_id(from_surface_id: str, to_surface_id: str) -> str:
    """Create a deterministic ID for a side connecting two surfaces."""
    return f"side_{len(from_surface_id)}:{from_surface_id}:{to_surface_id}"


def _match_bridge_to_patch_pair(
    patch: SurfaceCodeBasePatch,
    next_patch: SurfaceCodeBasePatch,
    bridge_patches: list[SurfaceCodeBasePatch],
) -> tuple[int, str, str, str, str] | None:
    """Find the single bridge connecting two adjacent patches."""
    for bridge_index, bridge_patch in enumerate(bridge_patches):
        patch_to_bridge = get_patch_connection_directions(patch, bridge_patch)
        bridge_to_next = get_patch_connection_directions(bridge_patch, next_patch)

        if patch_to_bridge is not None and bridge_to_next is not None:
            return (
                bridge_index,
                patch_to_bridge[0],
                patch_to_bridge[1],
                bridge_to_next[0],
                bridge_to_next[1],
            )
    return None


def get_multi_pauli_connections(
    logical_patch_types: list[SurfaceCodeBasePatch],
    bridge_patch_types: list[SurfaceCodeBasePatch],
) -> list[tuple[int, str, str, str, str]]:
    """Match each adjacent logical-patch pair to its bridge and facing directions.

    Returns a list of connections where each connection is:
    (bridge_index, patch_to_bridge_dir, bridge_to_patch_dir,
     bridge_to_next_dir, next_to_bridge_dir)
    """
    connections: list[tuple[int, str, str, str, str]] = []
    used_bridge_indices: set[int] = set()

    for patch, next_patch in pairwise(logical_patch_types):
        connection = _match_bridge_to_patch_pair(patch, next_patch, bridge_patch_types)

        if connection is None:
            msg = "Each adjacent pair of located patches must share exactly one bridge."
            raise ValueError(msg)

        bridge_index = connection[0]
        if bridge_index in used_bridge_indices:
            msg = "A bridge cannot connect more than one adjacent patch pair."
            raise ValueError(msg)

        used_bridge_indices.add(bridge_index)
        connections.append(connection)

    return connections


def make_correlation_data(
    block_id: str,
    directions: list[CorrelationDirection],
    bases: list[PauliAttr],
) -> CorrelationData:
    """Build one correlation item associated with a side."""
    colour = SurfaceColour.set_colour_scheme(bases[0])
    return {
        "type": "correlation",
        "blockId": block_id,
        "directions": directions,
        "colour": cast(Literal[SurfaceColour.BLUE, SurfaceColour.RED], colour),
    }


def _append_first_patch_correlation(
    visualisation_data: list[SpaceTimeVisualisationItem],
    input_ids: list[str],
    output_ids: list[str],
    logical_indices: list[int],
    bases: list[PauliAttr],
    bridge_direction: str | None = None,
) -> None:
    """Append correlation for the first patch in a multi-Pauli chain."""
    directions = _get_patch_correlation_directions(bridge_direction)

    visualisation_data.append(
        make_correlation_data(
            make_side_id(input_ids[logical_indices[0]], output_ids[logical_indices[0]]),
            directions,
            [bases[0]],
        )
    )


def _append_middle_patch_correlation(
    visualisation_data: list[SpaceTimeVisualisationItem],
    input_ids: list[str],
    output_ids: list[str],
    logical_indices: list[int],
    bases: list[PauliAttr],
    patch_index: int,
) -> None:
    """Append correlation for a middle patch (not first or last)."""
    visualisation_data.append(
        make_correlation_data(
            make_side_id(
                input_ids[logical_indices[patch_index]],
                output_ids[logical_indices[patch_index]],
            ),
            [
                {"orientation": "vertical", "direction": "-Y"},
                {"orientation": "vertical", "direction": "+Y"},
            ],
            [bases[patch_index]],
        )
    )


def _append_last_patch_correlation(
    visualisation_data: list[SpaceTimeVisualisationItem],
    input_ids: list[str],
    output_ids: list[str],
    logical_indices: list[int],
    bases: list[PauliAttr],
    bridge_direction: str | None = None,
    last_patch: SSAValue | None = None,
) -> None:
    """Append correlation for the last patch in a multi-Pauli chain.
    
    The bridge_direction parameter is the direction the last patch already faces
    towards the bridge (from the connection tuple's [4] element).
    
    If the bridge_direction is horizontal (±X) and the last patch has no subsequent
    operations, exclude the +Y direction from the correlation.
    """
    directions = _get_patch_correlation_directions(bridge_direction)
    
    # If correlation is purely horizontal (±X) and last patch has no further operations,
    # remove +Y to avoid unnecessary vertical correlation
    if (
        last_patch is not None
        and bridge_direction in {"+X", "-X"}
        and not last_patch.uses
    ):
        # Remove +Y from directions, keeping only -Y and the horizontal direction
        directions = [d for d in directions if d["direction"] != "+Y"]

    visualisation_data.append(
        make_correlation_data(
            make_side_id(input_ids[logical_indices[-1]], output_ids[logical_indices[-1]]),
            directions,
            [bases[-1]],
        )
    )


def _append_bridge_correlation(
    visualisation_data: list[SpaceTimeVisualisationItem],
    connection: tuple[int, str, str, str, str],
    bridge_input_ids: list[str],
    bridge_output_ids: list[str],
    bases: list[PauliAttr],
    connection_index: int,
) -> None:
    """Append correlation for a bridge connecting two patches."""
    bridge_index, _, bridge_direction_in, _, _ = connection

    # Get bases for bridge (if available, otherwise use first base)
    if connection_index + 1 < len(bases):
        bridge_bases = [bases[connection_index], bases[connection_index + 1]]
    else:
        bridge_bases = [bases[connection_index]] if connection_index < len(bases) else []

    directions = _get_bridge_correlation_directions(bridge_direction_in)

    visualisation_data.append(
        make_correlation_data(
            make_side_id(bridge_input_ids[bridge_index], bridge_output_ids[bridge_index]),
            directions,
            bridge_bases,
        )
    )


def append_multi_pauli_correlations(
    op: LocateUnplacedObservableOp,
    multi_pauli_op,
    logical_patches: list[SSAValue],
    visualisation_data: list[SpaceTimeVisualisationItem],
) -> None:
    """Append correlation items spanning a multi-Pauli patch chain.

    For a chain of N patches with N-1 bridges:
    - First patch: ±Y + opposite bridge direction (if perpendicular)
    - Bridges: directions matching bridge movement axis
    - Middle patches: ±Y only
    - Last patch: ±Y + direction it faces towards bridge
    """
    # Extract and validate data
    logical_patch_types = [cast(SurfaceCodeBasePatch, patch.type) for patch in logical_patches]
    bridge_patch_types = [
        cast(SurfaceCodeBasePatch, bridge.type) for bridge in multi_pauli_op.bridge_patches
    ]
    connections = get_multi_pauli_connections(logical_patch_types, bridge_patch_types)
    logical_indices = [multi_pauli_op.res.index(patch) for patch in logical_patches]
    input_ids = get_in_logical_patch_ids(multi_pauli_op)
    output_ids = get_out_logical_patch_ids(multi_pauli_op)
    bridge_input_ids = get_in_bridge_patch_ids(multi_pauli_op)
    bridge_output_ids = get_out_bridge_patch_ids(multi_pauli_op)
    bases = list(op.bases.data)

    # Single patch case: no bridges
    if len(logical_patch_types) == 1:
        logical_index = logical_indices[0]
        visualisation_data.append(
            make_correlation_data(
                make_side_id(input_ids[logical_index], output_ids[logical_index]),
                _get_patch_correlation_directions(),
                [bases[0]],
            )
        )
        return

    # Multi-patch chain: append correlations for first, bridges, middle, and last
    first_bridge_direction = connections[0][2]
    _append_first_patch_correlation(
        visualisation_data,
        input_ids,
        output_ids,
        logical_indices,
        bases,
        bridge_direction=_get_opposite_direction(first_bridge_direction),
    )

    for connection_index, connection in enumerate(connections):
        _append_bridge_correlation(
            visualisation_data,
            connection,
            bridge_input_ids,
            bridge_output_ids,
            bases,
            connection_index,
        )

        # Append middle patches (between bridges)
        patch_index = connection_index + 1
        if patch_index < len(logical_patch_types) - 1:
            _append_middle_patch_correlation(
                visualisation_data,
                input_ids,
                output_ids,
                logical_indices,
                bases,
                patch_index,
            )

    last_patch_direction = connections[-1][4]
    _append_last_patch_correlation(
        visualisation_data,
        input_ids,
        output_ids,
        logical_indices,
        bases,
        bridge_direction=last_patch_direction,
        last_patch=logical_patches[-1],
    )
