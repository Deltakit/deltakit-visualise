# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""
This is a compiler pass that generates the data required for the surface code visualisation
from the MLIR program.
"""

import json
from dataclasses import dataclass, field
from functools import singledispatch
from typing import Any, Literal, TypeAlias, TypedDict

from deltakit_compile.dialects.logical_assembly import CastOp, PrepareOp
from deltakit_compile.dialects.plaquette import PlaquetteOp, RoundOp
from deltakit_compile.dialects.qcore import (
    AllocQubitOp,
    PackQubitRegOp,
    QubitRegType,
    QubitType,
    UnpackQubitRegOp,
)
from deltakit_compile.dialects.qstruct import CircuitOp, RepeatOp
from typing_extensions import override
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.ir import BlockArgument, Operation, OpResult, SSAValue, cast
from xdsl.passes import ModulePass

from deltakit_visualise.constants import PATCH_VISUALISATION_DATA, PlaquetteShape
from deltakit_visualise.types import PatchVisualisationItem

CoordKey: TypeAlias = tuple[float, float]
QubitKind: TypeAlias = Literal["data", "ancilla"]
PlaquetteColour: TypeAlias = Literal["red", "blue"]


class PatchQubit(TypedDict):
    """Internal qubit payload while building a surface-code item."""

    id: str
    type: QubitKind
    coordinates: list[float]


class PatchPlaquette(TypedDict):
    """Internal plaquette payload with temporary coordinate keys."""

    id: int
    colour: PlaquetteColour
    shape: PlaquetteShape
    weight: int
    _coord_keys: list[CoordKey]
    coordinates: list[str]


class PatchContainer(TypedDict):
    """Container for plaquettes in a patch."""

    plaquettes: list[PatchPlaquette]


class InternalPatchVisualisationItem(TypedDict):
    """Internal patch item shape before dropping temporary helper fields."""

    round: int
    qubits: list[PatchQubit]
    patches: list[PatchContainer]
    _qubit_types: dict[CoordKey, QubitKind]


@dataclass
class SurfaceCodeVisualisationState:
    """Mutable state shared by operation handlers in this pass.

    Attributes:
        visualisation_data: Patch visualisation payload items.
        round_indices: Mapping from each plaquette round op to all executed round numbers.
        round_counter: Execution-order round counter.
        coordinates_map: Map SSA values to 2D coordinates.
            The key has the form (SSAValue, register index) where the register index
            is None for non-register qubits.
        patch_items: Fast lookup of patch payload items with key as round index.
    """

    visualisation_data: list[InternalPatchVisualisationItem] = field(default_factory=list)
    round_indices: dict[RoundOp, list[int]] = field(default_factory=dict)
    round_counter: int = 0
    coordinates_map: dict[tuple[SSAValue, int | None], tuple[float, float]] = field(
        default_factory=dict
    )
    patch_items: dict[int, InternalPatchVisualisationItem] = field(default_factory=dict)


def _get_module_op(op: Operation) -> ModuleOp:
    """Return the module ancestor for an operation."""
    current: Operation | None = op
    while current is not None:
        if isinstance(current, ModuleOp):
            return current
        current = current.parent_op()
    msg = f"Could not find module ancestor for operation {op.name}."
    raise ValueError(msg)


def _get_round_ancestor(op: Operation) -> RoundOp:
    """Return the nearest plaquette round ancestor for an operation."""
    current: Operation | None = op
    while current is not None:
        if isinstance(current, RoundOp):
            return current
        current = current.parent_op()
    msg = f"Operation {op.name} is not inside a plaquette.round operation."
    raise ValueError(msg)


def _get_round_index_with_state(op: PlaquetteOp, state: SurfaceCodeVisualisationState) -> list[int]:
    """Get stable round indices from the cached round map."""
    round_op = _get_round_ancestor(op)
    if round_op in state.round_indices:
        return state.round_indices[round_op]

    # Fallback for robustness if apply order changes.
    module_op = _get_module_op(op)
    round_idx = 0
    for child in module_op.walk():
        if isinstance(child, RoundOp):
            round_idx += 1
            state.round_indices.setdefault(child, [round_idx + 1])
            if child is round_op:
                return state.round_indices[child]
    msg = f"Could not determine round index for operation {op.name}."
    raise ValueError(msg)


def _get_round_location(op: PlaquetteOp, state: SurfaceCodeVisualisationState) -> list[float]:
    """Get patch location from data qubits in the surrounding plaquette.round op."""
    round_op = _get_round_ancestor(op)

    round_data_coords: list[tuple[float, float]] = []
    for child in round_op.walk():
        if isinstance(child, PlaquetteOp):
            round_data_coords.extend(
                _resolve_qubit_coordinate(qubit, state) for qubit in child.data_qubits
            )

    if len(round_data_coords) == 0:
        msg = "plaquette.round has no data qubits to infer patch location."
        raise ValueError(msg)

    min_x = min(coord[0] for coord in round_data_coords)
    min_y = min(coord[1] for coord in round_data_coords)
    return [min_x - 0.5, min_y - 0.5]


def _index_round_executions_in_op(op: Operation, state: SurfaceCodeVisualisationState) -> None:
    """Populate round indices in execution order, expanding qstruct.repeat blocks."""
    if isinstance(op, RepeatOp):
        repetitions = op.repetitions.data
        for _ in range(repetitions):
            for block in op.body.blocks:
                for child in block.ops:
                    _index_round_executions_in_op(child, state)
        return

    if isinstance(op, RoundOp):
        state.round_counter += 1
        state.round_indices.setdefault(op, []).append(state.round_counter)
        return

    for region in op.regions:
        for block in region.blocks:
            for child in block.ops:
                _index_round_executions_in_op(child, state)


def _build_round_indices(module_op: ModuleOp, state: SurfaceCodeVisualisationState) -> None:
    """Precompute global round indices for each plaquette.round execution."""
    _index_round_executions_in_op(module_op, state)


def _cache_coordinate(
    state: SurfaceCodeVisualisationState,
    cache_key: tuple[SSAValue, int | None],
    coord: tuple[float, float],
) -> tuple[float, float]:
    """Cache and return a resolved coordinate."""
    state.coordinates_map[cache_key] = coord
    return coord


def _resolve_block_argument_coordinate(
    ssa: BlockArgument,
    state: SurfaceCodeVisualisationState,
    reg_index: int | None,
) -> tuple[float, float]:
    """Resolve coordinates for block arguments by following parent op bindings."""
    parent_op = ssa.owner.parent_op()
    if isinstance(parent_op, RoundOp):
        return _resolve_qubit_coordinate(parent_op.qubits[ssa.index], state, reg_index)
    if isinstance(parent_op, CircuitOp):
        return _resolve_qubit_coordinate(parent_op.args[ssa.index], state, reg_index)
    if isinstance(parent_op, RepeatOp):
        return _resolve_qubit_coordinate(parent_op.iter_args[ssa.index], state, reg_index)

    msg = f"Unsupported block argument parent while resolving coordinates: {parent_op}."
    raise ValueError(msg)


def _resolve_alloc_qubit_coordinate(
    ssa: OpResult,
    owner: AllocQubitOp,
    reg_index: int | None,
) -> tuple[float, float]:
    """Resolve coordinates for allocated qubits from allocation metadata."""
    qubit_ssa = cast(SSAValue[QubitType], ssa)
    coordinate = (
        owner.get_qubit_coordinate(cast(SSAValue[QubitRegType], ssa), reg_index)
        if reg_index is not None
        else owner.get_qubit_coordinate(qubit_ssa)
    )
    if coordinate is None:
        msg = "Allocated qubit does not have coordinates."
        raise ValueError(msg)
    if len(coordinate.data) < 2:
        msg = "Qubit coordinate has less than 2 dimensions."
        raise ValueError(msg)
    return (coordinate.data[0], coordinate.data[1])


def _resolve_op_result_coordinate(  # noqa: PLR0911
    ssa: OpResult,
    state: SurfaceCodeVisualisationState,
    reg_index: int | None,
) -> tuple[float, float]:
    """Resolve coordinates for operation results by handling supported producer ops."""
    owner = ssa.op
    if isinstance(owner, AllocQubitOp):
        return _resolve_alloc_qubit_coordinate(ssa, owner, reg_index)
    if isinstance(owner, UnpackQubitRegOp):
        return _resolve_qubit_coordinate(owner.reg, state, ssa.index)
    if isinstance(owner, PackQubitRegOp):
        if reg_index is None:
            msg = "PackQubitRegOp requires register index to resolve a qubit coordinate."
            raise ValueError(msg)
        return _resolve_qubit_coordinate(owner.qubits[reg_index], state)
    if isinstance(owner, CastOp):
        return _resolve_qubit_coordinate(owner.in_, state, reg_index)
    if isinstance(owner, PrepareOp):
        return _resolve_qubit_coordinate(owner.patch, state, reg_index)
    if isinstance(owner, RepeatOp):
        return _resolve_qubit_coordinate(owner.iter_args[ssa.index], state, reg_index)
    if isinstance(owner, CircuitOp):
        return _resolve_qubit_coordinate(owner.args[ssa.index], state, reg_index)

    msg = f"Unsupported SSA owner while resolving qubit coordinate: {owner.name}."
    raise ValueError(msg)


def _resolve_qubit_coordinate(
    ssa: SSAValue,
    state: SurfaceCodeVisualisationState,
    reg_index: int | None = None,
) -> tuple[float, float]:
    """Resolve a qubit SSA value to its 2D coordinate."""
    cache_key = (ssa, reg_index)
    if cache_key in state.coordinates_map:
        return state.coordinates_map[cache_key]

    if isinstance(ssa, BlockArgument):
        coord = _resolve_block_argument_coordinate(ssa, state, reg_index)
        return _cache_coordinate(state, cache_key, coord)

    if isinstance(ssa, OpResult):
        coord = _resolve_op_result_coordinate(ssa, state, reg_index)
        return _cache_coordinate(state, cache_key, coord)

    msg = f"Unsupported SSA value type while resolving qubit coordinate: {type(ssa)}."
    raise TypeError(msg)


def _coord_key(coord: tuple[float, float]) -> CoordKey:
    """Build a stable key for a coordinate pair."""
    return (round(coord[0], 12), round(coord[1], 12))


def _coord_from_key(key: CoordKey) -> list[float]:
    """Decode a coordinate key back to a serialisable coordinate pair."""
    return [key[0], key[1]]


def _rebuild_qubits_and_coordinates(item: InternalPatchVisualisationItem) -> None:
    """Rebuild qubit IDs and plaquette coordinate references from internal coordinate keys."""
    qubit_type_by_coord = item["_qubit_types"]
    sorted_coords = sorted(
        qubit_type_by_coord.keys(),
        key=lambda key: (
            0 if qubit_type_by_coord[key] == "data" else 1,
            _coord_from_key(key)[1],
            _coord_from_key(key)[0],
        ),
    )

    id_by_coord = {coord: f"q_{idx}" for idx, coord in enumerate(sorted_coords)}
    item["qubits"] = [
        {
            "id": id_by_coord[coord],
            "type": qubit_type_by_coord[coord],
            "coordinates": _coord_from_key(coord),
        }
        for coord in sorted_coords
    ]

    plaquettes = item["patches"][0]["plaquettes"]
    for plaquette in plaquettes:
        plaquette["coordinates"] = [id_by_coord[coord] for coord in plaquette["_coord_keys"]]


def _get_or_create_patch_item(
    state: SurfaceCodeVisualisationState,
    round_index: int,
) -> InternalPatchVisualisationItem:
    """Get an existing patch item by round index, or create a new one."""
    if round_index in state.patch_items:
        return state.patch_items[round_index]

    item: InternalPatchVisualisationItem = {
        "round": round_index,
        "qubits": [],
        "patches": [{"plaquettes": []}],
        "_qubit_types": {},
    }
    state.visualisation_data.append(item)
    state.patch_items[round_index] = item
    return item


def _get_plaquette_colour(op: PlaquetteOp) -> PlaquetteColour:
    """Derive plaquette colour from the first stabiliser type."""
    paulis = {
        qstate.pauli_state.data.name
        for stabiliser in op.stabilisers
        for qstate in stabiliser.qubit_states.data
    }
    if len(paulis) != 1:
        msg = (
            "Unsupported stabiliser Pauli for colour mapping. "
            f"Found the following paulis: {sorted(paulis)}."
        )
        raise ValueError(msg)

    pauli_name = next(iter(paulis))
    if pauli_name == "X":
        return "red"
    if pauli_name == "Z":
        return "blue"
    msg = f"Unsupported stabiliser Pauli for colour mapping: {pauli_name}."
    raise ValueError(msg)


def _get_plaquette_shape(
    qubit_type_by_coord: dict[CoordKey, QubitKind],
    involved_coords: list[CoordKey],
) -> PlaquetteShape:
    """Classify plaquettes as square/semicircle from participant qubit kinds."""
    has_ancilla_participant = any(
        qubit_type_by_coord[coord] == "ancilla" for coord in involved_coords
    )
    return PlaquetteShape.SEMICIRCLE if has_ancilla_participant else PlaquetteShape.SQUARE


def _get_plaquette_weight(
    qubit_type_by_coord: dict[CoordKey, QubitKind],
    involved_coords: list[CoordKey],
) -> int:
    """Count participant data qubits in the plaquette."""
    return sum(1 for coord in involved_coords if qubit_type_by_coord[coord] == "data")


def _finalise_visualisation_data(
    visualisation_data: list[InternalPatchVisualisationItem],
) -> list[PatchVisualisationItem]:
    """Strip internal fields and return the public payload shape."""
    final_data: list[PatchVisualisationItem] = []
    for item in visualisation_data:
        serialisable_item: dict[str, Any] = dict(item)
        plaquettes = serialisable_item["patches"][0]["plaquettes"]
        for plaquette in plaquettes:
            plaquette.pop("_coord_keys", None)
        serialisable_item.pop("_qubit_types", None)
        final_data.append(cast(PatchVisualisationItem, serialisable_item))
    return final_data


@singledispatch
def visualise_plaquette(_op: Operation, _state: SurfaceCodeVisualisationState) -> None:
    """

    Unhandled operations are ignored.
    """


@visualise_plaquette.register
def visualise_module_op(op: ModuleOp, state: SurfaceCodeVisualisationState) -> None:
    """Module op has no direct visualisation effect in this pass."""


@visualise_plaquette.register
def visualise_round_op(op: RoundOp, state: SurfaceCodeVisualisationState) -> None:
    """Round indices are precomputed before walk; no per-op action required."""


@visualise_plaquette.register
def visualise_alloc_qubits_op(op: AllocQubitOp, state: SurfaceCodeVisualisationState) -> None:
    """Warm coordinate cache for directly allocated qubits."""
    for result in op.results:
        if not isinstance(result.type, QubitType):
            continue
        coordinate = op.get_qubit_coordinate(cast(SSAValue[QubitType], result))
        if coordinate is None or len(coordinate.data) < 2:
            continue
        state.coordinates_map[(result, None)] = (coordinate.data[0], coordinate.data[1])


@visualise_plaquette.register
def visualise_plaquette_op(op: PlaquetteOp, state: SurfaceCodeVisualisationState) -> None:
    """Handle plaquette operations and aggregate surface-code visualisation data."""
    data_coords = [_resolve_qubit_coordinate(qubit, state) for qubit in op.data_qubits]
    ancilla_coords = [_resolve_qubit_coordinate(qubit, state) for qubit in op.ancilla_qubits]

    round_indices = _get_round_index_with_state(op, state)

    for round_index in round_indices:
        item = _get_or_create_patch_item(state, round_index)

        for coord in data_coords:
            item["_qubit_types"][_coord_key(coord)] = "data"
        for coord in ancilla_coords:
            item["_qubit_types"][_coord_key(coord)] = "ancilla"

        involved_coords = list(map(_coord_key, data_coords))
        if len(data_coords) < 4:
            involved_coords.extend(map(_coord_key, ancilla_coords))
        involved_coords = sorted(
            involved_coords,
            key=lambda key: (
                0 if item["_qubit_types"][key] == "data" else 1,
                _coord_from_key(key)[1],
                _coord_from_key(key)[0],
            ),
        )

        plaquettes = item["patches"][0]["plaquettes"]
        plaquettes.append(
            {
                "id": len(plaquettes),
                "colour": _get_plaquette_colour(op),
                "shape": _get_plaquette_shape(item["_qubit_types"], involved_coords),
                "weight": _get_plaquette_weight(item["_qubit_types"], involved_coords),
                "_coord_keys": involved_coords,
                "coordinates": [],
            }
        )

        _rebuild_qubits_and_coordinates(item)


@dataclass(frozen=True)
class VisualiseSurfaceCodes(ModulePass):
    """Compiler pass to generate surface code visualisation data."""

    name = "visualise-surface-codes"

    @override
    def apply(self, ctx, op: ModuleOp) -> None:
        """Apply the surface code visualisation pass to the module."""
        state = SurfaceCodeVisualisationState()
        _build_round_indices(op, state)

        for child in op.walk():
            visualise_plaquette(child, state)

        final_data = _finalise_visualisation_data(state.visualisation_data)
        op.attributes[PATCH_VISUALISATION_DATA] = StringAttr(json.dumps(final_data))
