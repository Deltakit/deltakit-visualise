# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Helpers for working with SSA values."""

from deltakit_compile.dialects.qstruct import ParallelOp, YieldOp
from xdsl.ir import OpResult, SSAValue


def unwrap_parallel_value(value: SSAValue) -> SSAValue:
    """Resolve a value produced by one or more ``qstruct.parallel`` ops.

    For a result of a ``ParallelOp``, follows the corresponding value yielded
    by its regions. The operation's results are matched to yielded operands
    in region order and nested parallel results are followed recursively.

    Args:
        value: The SSA value to resolve.

    Returns:
        The underlying yielded SSA value, or ``value`` if it is not produced
        by a ``ParallelOp``.
    """
    while isinstance(value, OpResult) and isinstance(value.op, ParallelOp):
        yielded_values: list[SSAValue] = []
        for region in value.op.par_regions:
            terminator = region.block.last_op
            if isinstance(terminator, YieldOp):
                yielded_values.extend(terminator.operands)
        value = yielded_values[value.index]
    return value
