# (c) Copyright Riverlane 2020-2026.
"""Tests for LogAsmAPIVisualiser."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dkit_compile.frontend.logasm import LogAsmBuilder, RotatedPlanarPatch
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import SSAValue

from dkit_visualise.logical_assembly_api_visualiser import LogAsmAPIVisualiser


@pytest.fixture
def builder_with_two_patches() -> tuple[
    LogAsmBuilder, RotatedPlanarPatch, RotatedPlanarPatch
]:
    """Builder with a distance-12 patch (p0) and a distance-5 patch (p1)."""
    builder = LogAsmBuilder()
    p0 = builder.declare_patch(RotatedPlanarPatch(12, 12, location=(0, 0)))
    p0.prepare("Z")
    p0.measure_stabilisers(4)
    p1 = builder.declare_patch(RotatedPlanarPatch(5, 5, location=(10, 10)))
    p1.prepare("X")
    p1.measure_stabilisers(4)
    return builder, p0, p1


@pytest.fixture
def builder_with_single_patch() -> tuple[LogAsmBuilder, RotatedPlanarPatch]:
    """Builder with a single distance-5 patch."""
    builder = LogAsmBuilder()
    p = builder.declare_patch(RotatedPlanarPatch(5, 5, location=(0, 0)))
    p.prepare("Z")
    p.measure_stabilisers(4)
    return builder, p


class TestVisualiseLogicalPatch:
    """Tests for visualise_logical_patch / visualise."""

    def test_returns_path(self, monkeypatch, builder_with_single_patch) -> None:
        """visualise_logical_patch returns the path produced by show."""
        builder, patch = builder_with_single_patch

        monkeypatch.setattr(
            "dkit_visualise.logical_assembly_api_visualiser.show",
            lambda _data, **_kwargs: Path("/display/index.html"),
        )

        result = LogAsmAPIVisualiser(builder).visualise_logical_patch(patch)

        assert result == Path("/display/index.html")

    def test_different_patches_produce_different_visualisation_data(
        self, monkeypatch, builder_with_two_patches
    ) -> None:
        """p0 (distance 12) and p1 (distance 5) produce distinct visualisation data."""
        builder, p0, p1 = builder_with_two_patches
        datasets: list[dict] = []

        def fake_show(data, **_kwargs) -> Path:
            datasets.append(data)
            return Path("/display/index.html")

        monkeypatch.setattr(
            "dkit_visualise.logical_assembly_api_visualiser.show", fake_show
        )

        vis = LogAsmAPIVisualiser(builder)
        vis.visualise_logical_patch(p0)
        vis.visualise_logical_patch(p1)

        assert len(datasets) == 2
        assert str(datasets[0]) != str(datasets[1])

    def test_default_round_is_selected(
        self, monkeypatch, builder_with_single_patch
    ) -> None:
        """The default call returns the first round snapshot."""
        builder, patch = builder_with_single_patch
        captured: dict = {}

        def fake_show(data, **_kwargs) -> Path:
            captured["data"] = data
            return Path("/display/index.html")

        monkeypatch.setattr(
            "dkit_visualise.logical_assembly_api_visualiser.show", fake_show
        )

        LogAsmAPIVisualiser(builder).visualise_logical_patch(patch)

        assert [item["round"] for item in captured["data"]["ops"]] == [1]

    def test_selects_only_requested_round(
        self, monkeypatch, builder_with_single_patch
    ) -> None:
        """The payload contains only the requested round snapshot."""
        builder, patch = builder_with_single_patch
        captured: dict = {}

        monkeypatch.setattr(
            "dkit_visualise.logical_assembly_api_visualiser.show",
            lambda data, **_kwargs: (
                captured.__setitem__("data", data),
                Path("/display/index.html"),
            )[1],
        )

        LogAsmAPIVisualiser(builder).visualise_logical_patch(patch, round_no=2)

        assert [item["round"] for item in captured["data"]["ops"]] == [2]

    def test_unavailable_round_raises_error(self, builder_with_single_patch) -> None:
        """An unavailable requested round raises a validation error."""
        builder, patch = builder_with_single_patch

        with pytest.raises(
            ValueError,
            match="Error: Round number is more than maximum allowed value of 4",
        ):
            LogAsmAPIVisualiser(builder).visualise_logical_patch(patch, round_no=8)

    def test_non_positive_round_raises_error(self, builder_with_single_patch) -> None:
        """A non-positive round number raises a validation error."""
        builder, patch = builder_with_single_patch

        with pytest.raises(
            ValueError, match="Round number should be a positive number"
        ):
            LogAsmAPIVisualiser(builder).visualise_logical_patch(patch, round_no=0)


class TestGetModuleFromBuilder:
    """Tests for _get_module_from_builder."""

    def test_returns_module_op(self, builder_with_single_patch) -> None:
        """_get_module_from_builder returns a ModuleOp."""
        builder, _ = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        module = vis._get_module_from_builder()
        assert isinstance(module, ModuleOp)

    def test_raises_runtime_error_on_failure(self) -> None:
        """_get_module_from_builder wraps build errors in RuntimeError."""
        bad_builder = MagicMock(spec=LogAsmBuilder)
        bad_builder.build_program.side_effect = ValueError("broken")
        vis = LogAsmAPIVisualiser(bad_builder)
        with pytest.raises(RuntimeError, match="Failed to build module"):
            vis._get_module_from_builder()


class TestExtractPatchOperations:
    """Tests for _extract_patch_operations."""

    def test_extracts_ops_for_ssa_patch(self, builder_with_two_patches) -> None:
        """Extracting p0 yields a module with only p0's ops."""
        builder, p0, _ = builder_with_two_patches
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()
        full_op_count = sum(1 for _ in full_module.body.block.ops)

        filtered = vis._extract_patch_operations(full_module, p0)

        filtered_op_count = sum(1 for _ in filtered.body.block.ops)
        assert filtered_op_count < full_op_count

    def test_returns_full_module_for_unknown_type(
        self, builder_with_single_patch
    ) -> None:
        """When the patch has no .ssa, the full module is returned unchanged."""
        builder, _ = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()

        result = vis._extract_patch_operations(full_module, object())

        assert result is full_module

    def test_accepts_raw_ssa_value(self, builder_with_single_patch) -> None:
        """An SSAValue passed directly is handled without AttributeError."""
        builder, patch = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()

        result = vis._extract_patch_operations(full_module, patch.ssa)

        assert isinstance(result, ModuleOp)


class TestCreateFilteredModule:
    """Tests for _create_filtered_module."""

    def test_round_filter_preserves_rounds_beyond_measurement_count(
        self, builder_with_single_patch
    ) -> None:
        """A request beyond the measurement count must not wrap back to an earlier round."""
        builder, _ = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()

        round_two = vis._filter_module_by_round(full_module, 2)
        round_eight = vis._filter_module_by_round(full_module, 8)

        round_two_op = next(
            op for op in round_two.body.block.ops if op.name == "log_asm.meas_stab"
        )
        round_eight_op = next(
            op for op in round_eight.body.block.ops if op.name == "log_asm.meas_stab"
        )

        assert round_two_op.min_rounds.data == 2
        assert round_eight_op.min_rounds.data == 4

    def test_empty_operations_returns_original(self, builder_with_single_patch) -> None:
        """No operations → the original module is returned as fallback."""
        builder, _ = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        original = vis._get_module_from_builder()

        result = vis._create_filtered_module(original, [])

        assert result is original

    def test_cloned_module_contains_correct_op_count(
        self, builder_with_two_patches
    ) -> None:
        """Filtered module contains exactly the collected ops."""
        builder, p0, _ = builder_with_two_patches
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()

        filtered = vis._extract_patch_from_ssa_value(full_module, p0.ssa)
        op_count = sum(1 for _ in filtered.body.block.ops)

        # declare + prepare + measure_stabilisers = 3 ops for p0
        assert op_count == 3

    def test_ssa_operands_are_remapped_within_clone(
        self, builder_with_single_patch
    ) -> None:
        """Cloned ops reference each other, not the original builder ops."""
        builder, patch = builder_with_single_patch
        vis = LogAsmAPIVisualiser(builder)
        full_module = vis._get_module_from_builder()

        filtered = vis._extract_patch_from_ssa_value(full_module, patch.ssa)
        ops = list(filtered.body.block.ops)

        ops_in_module = set(ops)
        for op in ops:
            for operand in op.operands:
                if isinstance(operand, SSAValue) and operand.op is not None:
                    assert operand.op in ops_in_module
