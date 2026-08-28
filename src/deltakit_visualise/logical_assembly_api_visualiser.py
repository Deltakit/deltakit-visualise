# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Visualisation interface for Logical-Assembly API programs."""

from pathlib import Path
from typing import Any

from deltakit_compile.dialects.logical_assembly import IntAttr, MeasStabOp
from deltakit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch
from xdsl.dialects.builtin import IntegerAttr, ModuleOp
from xdsl.ir import Operation, OpResult, SSAValue

from deltakit_visualise.logical_assembly_visualiser import LogicalAssemblyVisualiser
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.visualiser import get_visualisation_data, show


class LogAsmAPIVisualiser:
    """Visualiser for the Logical-Assembly API (high-level builder interface).

    For now, this class enables visualisation of individual patches as they are
    being constructed using the LogAsmBuilder, rather than after building the
    entire program.

    Example::

        >>> builder = LogAsmBuilder()
        >>> p = builder.declare_patch(...)
        >>> p = p.prepare(...)
        >>> p = p.measure_stabilisers(...)
        >>> visualiser = LogAsmAPIVisualiser(builder)
        >>> visualiser.visualise_logical_patch(p)

    Args:
        logical_assembly_builder: A LogAsmBuilder instance that is being used
            to construct a logical assembly program.

    Attributes:
        logical_assembly_builder: The LogAsmBuilder instance used to construct the program.
    """

    logical_assembly_builder: LogAsmBuilder

    def __init__(self, logical_assembly_builder: LogAsmBuilder) -> None:
        self.logical_assembly_builder = logical_assembly_builder

    def visualise_logical_patch(
        self, patch: SSAValue | RotatedPlanarPatch, round_no: int = 1
    ) -> Path:
        """Visualise a single logical patch at its current state.

        This method extracts the operations related to the given patch from the
        builder's current state and renders the 2D logical patch view.

        Args:
            patch: An SSA value or patch object representing the patch to visualise.
                This is typically the result of builder methods like declare_patch(),
                prepare(), measure_stabilisers(), etc.
            round_no: Round number to visualise. Defaults to 1. Operations up to
                and including the specified round are used to build the snapshot.

        Returns:
            The path to the generated ``index.html`` that is opened.

        Raises:
            ValueError: If the patch object cannot be processed or if no visualisation
                data can be generated.
        """
        module = self._get_module_from_builder()

        filtered_module = self._extract_patch_operations(module, patch)

        max_round_number = self._get_max_round_number(filtered_module)
        if round_no <= 0:
            msg = "Round number should be a positive number"
            raise ValueError(msg)
        if round_no > max_round_number:
            msg = f"Error: Round number is more than maximum allowed value of {max_round_number}"
            raise ValueError(msg)

        filtered_module = self._filter_module_by_round(filtered_module, round_no)

        ctx = LogicalAssemblyVisualiser.make_context()
        pipeline = PatchVisualisationPipeline(verify_between_passes=False)
        pipeline.apply(ctx, filtered_module)

        visualisation_data = get_visualisation_data(filtered_module)
        round_data = [
            item for item in visualisation_data["ops"] if item.get("round") == round_no
        ]
        visualisation_data["ops"] = round_data

        return show(visualisation_data, static=True)

    def _get_max_round_number(self, module: ModuleOp) -> int:
        """Return the cumulative number of measurement rounds in a module."""
        return sum(
            op.min_rounds.data for op in module.walk() if isinstance(op, MeasStabOp)
        )

    def _get_module_from_builder(self) -> ModuleOp:
        """Convert the current builder state to a ModuleOp."""
        try:
            return self.logical_assembly_builder.build_program().module
        except Exception as e:
            msg = f"Failed to build module from LogAsmBuilder: {e}"
            raise RuntimeError(msg) from e

    def _extract_patch_operations(self, module: ModuleOp, patch: Any) -> ModuleOp:
        """Extract operations related to a specific patch from the module."""
        ssa_value: SSAValue | None = None
        if isinstance(patch, SSAValue):
            ssa_value = patch
        elif hasattr(patch, "ssa"):
            ssa_value = patch.ssa

        if ssa_value is not None:
            return self._extract_patch_from_ssa_value(module, ssa_value)

        return module

    def _extract_patch_from_ssa_value(
        self, module: ModuleOp, ssa_value: SSAValue
    ) -> ModuleOp:
        """
        Extract patch operations for a specific SSA value.

        Traverses backwards from the SSA value to find all operations in its
        dependency chain, then creates a new module with just those operations.
        """
        collected_ops: list[Operation] = []
        visited: set[Operation] = set()

        def collect_dependencies(value: SSAValue) -> None:
            """Recursively collect operations that produce this value."""
            if not isinstance(value, OpResult):
                return
            op = value.op
            if op in visited:
                return

            visited.add(op)

            for operand in op.operands:
                if isinstance(operand, SSAValue):
                    collect_dependencies(operand)

            collected_ops.append(op)

        collect_dependencies(ssa_value)

        if not collected_ops:
            return module

        return self._create_filtered_module(module, collected_ops)

    def _create_filtered_module(
        self,
        original_module: ModuleOp,
        operations: list[Operation],
    ) -> ModuleOp:
        """Create a new module containing only the specified operations."""
        if not operations:
            return original_module

        value_mapper: dict[SSAValue, SSAValue] = {}
        clones = [op.clone(value_mapper=value_mapper) for op in operations]
        return ModuleOp(clones)

    def _filter_module_by_round(self, module: ModuleOp, round_no: int) -> ModuleOp:
        """Filter module operations to include only those up to the specified round.

        Args:
            module: The module to filter.
            round_no: The maximum round number to include.

        Returns:
            A new module containing only operations up to the specified round.
        """
        if not module.body.blocks:
            return module

        filtered_ops: list[Operation] = []

        for op in module.body.blocks[0].ops:
            op_round = self._get_operation_round(op)

            if op_round is None or op_round <= round_no:
                filtered_ops.append(op)

        value_mapper: dict[SSAValue, SSAValue] = {}
        clones: list[Operation] = []
        for op in filtered_ops:
            clone = op.clone(value_mapper=value_mapper)
            if isinstance(clone, MeasStabOp):
                clone.min_rounds = IntAttr.get(
                    min(clone.min_rounds.data, max(round_no, 0))
                )
            clones.append(clone)

        return ModuleOp(clones) if clones else module

    def _get_operation_round(self, op: Operation) -> int | None:
        """Extract round number from an operation's attributes.

        Args:
            op: The operation to extract round information from.

        Returns:
            The round number if found, None otherwise.
        """
        for attr_name in ("round", "round_index", "round_number"):
            if attr_name in op.attributes:
                attr = op.attributes[attr_name]
                if isinstance(attr, IntegerAttr):
                    try:
                        return int(attr.value.data)
                    except (AttributeError, TypeError, ValueError):
                        pass
        return None
