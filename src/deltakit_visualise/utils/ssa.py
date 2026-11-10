# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Helpers for working with SSA values."""

from deltakit_compile.dialects.qstruct import ParallelOp, YieldOp
from xdsl.ir import OpResult, SSAValue


def unwrap_parallel_value(value: SSAValue) -> SSAValue:
    """Follow ParallelOp results through their yielded values."""
    while isinstance(value, OpResult) and isinstance(value.op, ParallelOp):
        yielded_values: list[SSAValue] = []
        for region in value.op.par_regions:
            terminator = region.block.last_op
            if isinstance(terminator, YieldOp):
                yielded_values.extend(terminator.operands)
        value = yielded_values[value.index]
    return value
