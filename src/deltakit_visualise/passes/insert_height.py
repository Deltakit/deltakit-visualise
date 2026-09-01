# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""
Compiler pass that walks the AST to insert START_HEIGHT_ATTR and END_HEIGHT_ATTR
attributes into Ops.

Height tracking uses an increasing counter. Each operation is placed immediately
after the previous one. ParallelOp children are synchronised so that all regions
start at the same height (current_height at the point of the ParallelOp).
"""

from dataclasses import dataclass, field
from functools import singledispatch

from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    PatchDeclarationOp,
    PrepareOp,
)
from deltakit_compile.dialects.qstruct import ParallelOp
from xdsl.dialects.builtin import Float64Type, FloatAttr, ModuleOp
from xdsl.ir import Operation
from xdsl.passes import ModulePass

from deltakit_visualise.constants import END_HEIGHT_ATTR, START_HEIGHT_ATTR

DEFAULT_HEIGHT_COST: float = 0.0


@dataclass
class HeightTracker:
    """Tracks a monotonically increasing height counter."""

    current_height: float = 0
    processed: set[Operation] = field(default_factory=set)

    def consume(self, cost: float) -> tuple[float, float]:
        """Reserve *cost* height units and return (start_height, end_height)."""
        start = self.current_height
        end = start + cost
        self.current_height = end
        return start, end

    def mark_processed(self, op: Operation) -> None:
        """Mark an operation as already processed."""
        self.processed.add(op)

    def is_processed(self, op: Operation) -> bool:
        """Check if an operation has already been processed."""
        return op in self.processed


@singledispatch
def insert_height(_op: Operation, _tracker: HeightTracker) -> None:
    """
    Set start_height / end_height attributes for operations.
    Dispatches to specific handlers based on operation type.
    Unhandled operations are ignored.
    """


@insert_height.register
def handle_parallel_height(op: ParallelOp, tracker: HeightTracker) -> None:
    """Sets child operations in parallel — all regions start at the same height.

    When ops share a ParallelOp parent, they all start at the same current_height.
    After processing all regions, current_height advances to the max end height
    across all regions.
    """
    start_height = tracker.current_height
    max_end_height = start_height

    for region in op.par_regions:
        tracker.current_height = start_height
        for child_op in region.block.ops:
            insert_height(child_op, tracker)
            tracker.mark_processed(child_op)
        max_end_height = max(max_end_height, tracker.current_height)

    tracker.current_height = max_end_height


@insert_height.register
def handle_patch_declaration_height(op: PatchDeclarationOp, tracker: HeightTracker) -> None:
    """PatchDeclarationOp occupies DEFAULT_HEIGHT_COST height units."""
    start, end = tracker.consume(DEFAULT_HEIGHT_COST)
    op.attributes[START_HEIGHT_ATTR] = FloatAttr(start, Float64Type())
    op.attributes[END_HEIGHT_ATTR] = FloatAttr(end, Float64Type())


@insert_height.register
def handle_prepare_height(op: PrepareOp, tracker: HeightTracker) -> None:
    """PrepareOp occupies DEFAULT_HEIGHT_COST height units."""
    start, end = tracker.consume(DEFAULT_HEIGHT_COST)
    op.attributes[START_HEIGHT_ATTR] = FloatAttr(start, Float64Type())
    op.attributes[END_HEIGHT_ATTR] = FloatAttr(end, Float64Type())


@insert_height.register
def handle_meas_stab_height(op: MeasStabOp, tracker: HeightTracker) -> None:
    """MeasStabOp occupies *min_rounds* height units."""
    start, end = tracker.consume(op.min_rounds.data)
    op.attributes[START_HEIGHT_ATTR] = FloatAttr(start, Float64Type())
    op.attributes[END_HEIGHT_ATTR] = FloatAttr(end, Float64Type())


@insert_height.register
def handle_measure_height(op: MeasureOp, tracker: HeightTracker) -> None:
    """MeasureOp occupies DEFAULT_HEIGHT_COST height units."""
    start, end = tracker.consume(DEFAULT_HEIGHT_COST)
    op.attributes[START_HEIGHT_ATTR] = FloatAttr(start, Float64Type())
    op.attributes[END_HEIGHT_ATTR] = FloatAttr(end, Float64Type())


@insert_height.register
def handle_multi_pauli_meas_height(op: MultiPauliMeasOp, tracker: HeightTracker) -> None:
    """MultiPauliMeasOp occupies *rounds* height units."""
    start, end = tracker.consume(op.rounds.data)
    op.attributes[START_HEIGHT_ATTR] = FloatAttr(start, Float64Type())
    op.attributes[END_HEIGHT_ATTR] = FloatAttr(end, Float64Type())


@insert_height.register
def handle_module_height(_op: ModuleOp, _tracker: HeightTracker) -> None:
    """ModuleOp - ignored as it's the top-level container."""


@dataclass(frozen=True)
class InsertHeight(ModulePass):
    """Pass that walks the AST and inserts start_height and end_height attributes."""

    name = "insert-height"

    def apply(self, _context, op: ModuleOp) -> None:
        """Add start_height and end_height attributes to operations
        based on their position in the patch chains."""
        tracker = HeightTracker()

        for child in op.walk():
            if tracker.is_processed(child):
                continue
            insert_height(child, tracker)
