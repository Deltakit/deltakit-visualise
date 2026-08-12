# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Module for assigning unique identifiers to logical assembly operations.

This module provides a pass that walks the AST and assigns unique ID attributes
to operations, enabling tracking and visualisation of operations throughout
the compilation pipeline. IDs are generated via an internal counter (IdTracker)
and written as attributes on the IR
"""

from dataclasses import dataclass
from functools import singledispatch

from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    PatchDeclarationOp,
    PrepareOp,
)
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.ir import Operation
from xdsl.passes import ModulePass

from deltakit_visualise.constants import (
    IN_BRIDGE_PATCHES_ID,
    IN_LOGICAL_PATCHES_ID,
    IN_OP_ID,
    OUT_BRIDGE_PATCHES_ID,
    OUT_LOGICAL_PATCHES_ID,
    OUT_OP_ID,
)
from deltakit_visualise.utils.id_tracker import IdTracker


@singledispatch
def assign_id(_op: Operation, _tracker: IdTracker) -> None:
    """Assign unique identifier attributes to an operation's SSA values."""


@assign_id.register
def handle_patch_declaration_id(op: PatchDeclarationOp, tracker: IdTracker) -> None:
    """Assign an input ID attribute to a patch declaration operation."""
    in_id = tracker.assign(op.res)
    op.attributes[IN_OP_ID] = StringAttr(in_id)


@assign_id.register
def handle_prepare_id(op: PrepareOp, tracker: IdTracker) -> None:
    """Assign an input ID attribute to a prepare operation."""
    in_id = tracker.assign(op.res)
    op.attributes[IN_OP_ID] = StringAttr(in_id)


@assign_id.register
def handle_meas_stab_id(op: MeasStabOp, tracker: IdTracker) -> None:
    """Assign input and output ID attributes to a stabiliser measurement operation."""
    in_id = tracker.next_id()
    op.attributes[IN_OP_ID] = StringAttr(in_id)

    out_id = tracker.assign(op.res)
    op.attributes[OUT_OP_ID] = StringAttr(out_id)


@assign_id.register
def handle_measure_id(op: MeasureOp, tracker: IdTracker) -> None:
    """Assign an output ID attribute to a measure operation."""
    out_id = tracker.assign(op.measurement)
    op.attributes[OUT_OP_ID] = StringAttr(out_id)


@assign_id.register
def handle_multi_pauli_meas_id(op: MultiPauliMeasOp, tracker: IdTracker) -> None:
    """Assign input and output ID attributes to a multi-Pauli measurement operation."""
    in_logical_ids = [tracker.next_id() for _ in op.logical_patches]
    out_logical_ids = [tracker.assign(res) for res in op.res]

    op.attributes[IN_LOGICAL_PATCHES_ID] = ArrayAttr([StringAttr(pid) for pid in in_logical_ids])
    op.attributes[OUT_LOGICAL_PATCHES_ID] = ArrayAttr([StringAttr(pid) for pid in out_logical_ids])

    # for each bridge patch, we need to assign a unique ID given that
    # tracker.get_or_assign(bridge_patch) is returning the same ID for the bridge patch declaration
    in_bridge_ids = [tracker.next_id() for _ in op.bridge_patches]
    out_bridge_ids = [tracker.next_id() for _ in op.bridge_patches]

    op.attributes[IN_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr(pid) for pid in in_bridge_ids])
    op.attributes[OUT_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr(pid) for pid in out_bridge_ids])

    tracker.assign(op.measurement)


@assign_id.register
def handle_module_op_id(_op: ModuleOp, _tracker: IdTracker) -> None:
    """ModuleOp - ignored as it's the top-level container."""


@dataclass(frozen=True)
class AssignId(ModulePass):
    """Pass that walks the AST and assigns unique ID attributes to operations."""

    name = "assign-id"

    def apply(self, _context, op: ModuleOp) -> None:
        """Assign ID attributes to operations using an internal counter."""
        tracker = IdTracker()
        for child in op.walk():
            assign_id(child, tracker)
