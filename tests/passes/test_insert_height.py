# (c) Copyright Riverlane 2020-2026.
"""Tests for the InsertHeight pass."""

import pytest
from deltakit_compile.dialects.logical_assembly import MeasStabOp
from deltakit_compile.dialects.qstruct import ParallelOp, YieldOp
from xdsl.dialects.builtin import FloatAttr, ModuleOp
from xdsl.ir import Block, Operation, Region

from deltakit_visualise.constants import END_HEIGHT_ATTR, START_HEIGHT_ATTR
from deltakit_visualise.passes.insert_height import InsertHeight
from tests.conftest import (
    MakeBridgePatch,
    MakeMeasStab,
    MakeMeasure,
    MakeMultiPauliMeas,
    MakePreparedPatch,
)


def _get_heights(op: Operation) -> tuple[float, float]:
    """Extract start_height and end_height from an operation's attributes."""
    start = op.attributes.get(START_HEIGHT_ATTR)
    end = op.attributes.get(END_HEIGHT_ATTR)
    assert isinstance(start, FloatAttr), f"Missing {START_HEIGHT_ATTR} on {op.name}"
    assert isinstance(end, FloatAttr), f"Missing {END_HEIGHT_ATTR} on {op.name}"
    return (start.value.data, end.value.data)


class TestInsertHeightSimpleChain:
    """Tests for InsertHeight pass on simple single-patch chains."""

    @pytest.mark.parametrize(
        ("min_rounds", "include_measure", "expected_heights"),
        [
            # declare only
            (None, False, {"patch_dec": (0.0, 0.0)}),
            # declare + prepare only
            (None, False, {"patch_dec": (0.0, 0.0), "prepare": (0.0, 0.0)}),
            # declare + prepare + meas_stab(10)
            (
                10,
                False,
                {
                    "patch_dec": (0.0, 0.0),
                    "prepare": (0.0, 0.0),
                    "meas_stab": (0.0, 10.0),
                },
            ),
            # declare + prepare + meas_stab(10) + measure
            (
                10,
                True,
                {
                    "patch_dec": (0.0, 0.0),
                    "prepare": (0.0, 0.0),
                    "meas_stab": (0.0, 10.0),
                    "measure": (10.0, 10.0),
                },
            ),
        ],
        ids=[
            "declare",
            "declare+prepare",
            "declare+prepare+meas_stab",
            "declare+prepare+meas_stab+measure",
        ],
    )
    # PLR0913: suppresses "too many arguments" - needed for fixtures + parametrise
    def test_single_chain_heights(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
        min_rounds: int | None,
        include_measure: bool,
        expected_heights: dict[str, tuple[float, float]],
    ) -> None:
        """Test height assignment for single-chain operations."""
        patch = make_prepared_patch()

        ops: list[Operation] = [patch.patch_dec, patch.prepare]
        op_map: dict[str, Operation] = {
            "patch_dec": patch.patch_dec,
            "prepare": patch.prepare,
        }

        if min_rounds is not None:
            meas_stab = make_meas_stab(patch.prepare.res, min_rounds)
            ops.append(meas_stab)
            op_map["meas_stab"] = meas_stab

            if include_measure:
                measure = make_measure(meas_stab.res)
                ops.append(measure)
                op_map["measure"] = measure

        module = ModuleOp(ops)
        InsertHeight().apply(None, module)

        for op_name, expected in expected_heights.items():
            assert _get_heights(op_map[op_name]) == expected, f"Height mismatch for {op_name}"


class TestInsertHeightMultiPauli:
    """Tests for InsertHeight pass with MultiPauliMeasOp."""

    def test_two_chains_with_different_heights_synchronise(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test sequential height assignment with multiple inputs."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        # Patch A operations: declare -> prepare -> meas_stab(10)
        # Expected sequential: patch_dec (0,0), prepare (0,0), meas_stab (0,10)
        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)

        # Patch B operations: declare -> prepare -> meas_stab(5)
        # Sequential continues: patch_dec (10,10), prepare (10,10), meas_stab (10,15)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 5)

        # Bridge: sequential continues at (15,15)
        # MultiPauliMeasOp: (15, 18)
        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

        # Measure: (18, 18)
        measure = make_measure(multi_pauli.res[0])

        module = ModuleOp(
            [
                patch_a.patch_dec,
                patch_a.prepare,
                meas_stab_a,
                patch_b.patch_dec,
                patch_b.prepare,
                meas_stab_b,
                bridge_dec,
                multi_pauli,
                measure,
            ]
        )
        InsertHeight().apply(None, module)

        # Patch A - sequential order
        assert _get_heights(patch_a.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch_a.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab_a) == (0.0, 10.0)

        # Patch B - sequential continues
        assert _get_heights(patch_b.patch_dec) == (10.0, 10.0)
        assert _get_heights(patch_b.prepare) == (10.0, 10.0)
        assert _get_heights(meas_stab_b) == (10.0, 15.0)

        # Bridge - sequential continues
        assert _get_heights(bridge_dec) == (15.0, 15.0)

        # MultiPauliMeasOp: start=15, end=15+3=18
        assert _get_heights(multi_pauli) == (15.0, 18.0)
        assert _get_heights(measure) == (18.0, 18.0)

    def test_meas_stab_after_multi_pauli(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test sequential height tracking with operations following MultiPauliMeasOp."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        # Equal height chains
        # Sequential: declare_a (0,0), prepare_a (0,0), meas_stab_a (0,10)
        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        # Sequential: declare_b (10,10), prepare_b (10,10), meas_stab_b (10,20)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        # Sequential: bridge (20,20)
        # Sequential: multi_pauli (20,25) - no synchronisation in sequential mode
        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=5,
        )

        # Another meas_stab after multi_pauli: (25, 32)
        meas_stab_post = make_meas_stab(multi_pauli.res[0], 7)
        measure = make_measure(meas_stab_post.res)

        module = ModuleOp(
            [
                patch_a.patch_dec,
                patch_a.prepare,
                meas_stab_a,
                patch_b.patch_dec,
                patch_b.prepare,
                meas_stab_b,
                bridge_dec,
                multi_pauli,
                meas_stab_post,
                measure,
            ]
        )
        InsertHeight().apply(None, module)

        # MultiPauliMeasOp: start=20, end=20+5=25
        assert _get_heights(multi_pauli) == (20.0, 25.0)
        # meas_stab_post: start=25, end=25+7=32
        assert _get_heights(meas_stab_post) == (25.0, 32.0)
        assert _get_heights(measure) == (32.0, 32.0)


class TestInsertHeightConsecutiveMeasStab:
    """Tests for consecutive meas_stab operations with sequential height tracking."""

    @pytest.mark.parametrize(
        ("rounds_list", "expected_heights"),
        [
            # 2 consecutive meas_stabs
            ([5, 3], [(0.0, 5.0), (5.0, 8.0)]),
            # 3 consecutive meas_stabs
            ([2, 4, 6], [(0.0, 2.0), (2.0, 6.0), (6.0, 12.0)]),
            # Single meas_stab
            ([10], [(0.0, 10.0)]),
        ],
        ids=["2-meas_stabs", "3-meas_stabs", "1-meas_stab"],
    )
    def test_consecutive_meas_stab_accumulates_height(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        rounds_list: list[int],
        expected_heights: list[tuple[int, int]],
    ) -> None:
        """Test that consecutive meas_stab operations accumulate height correctly."""
        patch = make_prepared_patch()

        ops: list[Operation] = [patch.patch_dec, patch.prepare]

        meas_stabs: list[MeasStabOp] = []
        prev_res = patch.prepare.res
        for rounds in rounds_list:
            meas_stab = make_meas_stab(prev_res, rounds)
            meas_stabs.append(meas_stab)
            ops.append(meas_stab)
            prev_res = meas_stab.res

        module = ModuleOp(ops)
        InsertHeight().apply(None, module)

        assert _get_heights(patch.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch.prepare) == (0.0, 0.0)
        for meas_stab, expected in zip(meas_stabs, expected_heights, strict=True):
            assert _get_heights(meas_stab) == expected

    def test_two_independent_chains_with_different_meas_stab_counts(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test sequential height tracking across multiple patch operations."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()

        # Patch A operations: declare -> prepare -> meas_stab(5) -> meas_stab(3)
        # Sequential: declare_a (0,0), prepare_a (0,0), meas_stab_a1 (0,5), meas_stab_a2 (5,8)
        meas_stab_a1 = make_meas_stab(patch_a.prepare.res, 5)
        meas_stab_a2 = make_meas_stab(meas_stab_a1.res, 3)

        # Patch B operations: declare -> prepare -> meas_stab(2) -> meas_stab(4) -> meas_stab(6)
        # Sequential: declare_b (8,8), prepare_b (8,8), meas_stab_b1 (8,10),
        # meas_stab_b2 (10,14), meas_stab_b3 (14,20)
        meas_stab_b1 = make_meas_stab(patch_b.prepare.res, 2)
        meas_stab_b2 = make_meas_stab(meas_stab_b1.res, 4)
        meas_stab_b3 = make_meas_stab(meas_stab_b2.res, 6)

        module = ModuleOp(
            [
                patch_a.patch_dec,
                patch_a.prepare,
                meas_stab_a1,
                meas_stab_a2,
                patch_b.patch_dec,
                patch_b.prepare,
                meas_stab_b1,
                meas_stab_b2,
                meas_stab_b3,
            ]
        )
        InsertHeight().apply(None, module)

        # Patch A heights (sequential order)
        assert _get_heights(patch_a.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch_a.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab_a1) == (0.0, 5.0)
        assert _get_heights(meas_stab_a2) == (5.0, 8.0)

        # Patch B heights (sequential continues)
        assert _get_heights(patch_b.patch_dec) == (8.0, 8.0)
        assert _get_heights(patch_b.prepare) == (8.0, 8.0)
        assert _get_heights(meas_stab_b1) == (8.0, 10.0)
        assert _get_heights(meas_stab_b2) == (10.0, 14.0)
        assert _get_heights(meas_stab_b3) == (14.0, 20.0)


class TestInsertHeightParallelOp:
    """Tests for handle_parallel_height with ParallelOp."""

    def test_parallel_regions_start_at_same_height(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that operations in parallel regions all start at the same height."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        # Build two parallel regions with equal heights
        region_a = Region(Block([patch_a.patch_dec, patch_a.prepare, meas_stab_a, YieldOp()]))
        region_b = Region(Block([patch_b.patch_dec, patch_b.prepare, meas_stab_b, YieldOp()]))
        parallel_op = ParallelOp(result_types=[], par_regions=[region_a, region_b])

        module = ModuleOp([parallel_op])
        InsertHeight().apply(None, module)

        # Both regions start at 0 and run in parallel
        assert _get_heights(patch_a.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch_a.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab_a) == (0.0, 10.0)

        assert _get_heights(patch_b.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch_b.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab_b) == (0.0, 10.0)

    @pytest.mark.usefixtures("make_measure")
    def test_parallel_regions_with_different_heights_advance_to_max(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that tracker advances to the max end height across all regions."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()

        # Region A: meas_stab(10) -> end height = 10
        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        # Region B: meas_stab(5) -> end height = 5
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 5)

        region_a = Region(Block([patch_a.patch_dec, patch_a.prepare, meas_stab_a, YieldOp()]))
        region_b = Region(Block([patch_b.patch_dec, patch_b.prepare, meas_stab_b, YieldOp()]))
        parallel_op = ParallelOp(result_types=[], par_regions=[region_a, region_b])

        # Operation after the ParallelOp should start at max(10, 5) = 10
        post_patch = make_prepared_patch()
        meas_stab_post = make_meas_stab(post_patch.prepare.res, 3)

        module = ModuleOp([parallel_op, post_patch.patch_dec, post_patch.prepare, meas_stab_post])
        InsertHeight().apply(None, module)

        # Region A
        assert _get_heights(meas_stab_a) == (0.0, 10.0)
        # Region B
        assert _get_heights(meas_stab_b) == (0.0, 5.0)

        # After ParallelOp, tracker is at 10
        assert _get_heights(post_patch.patch_dec) == (10.0, 10.0)
        assert _get_heights(post_patch.prepare) == (10.0, 10.0)
        assert _get_heights(meas_stab_post) == (10.0, 13.0)

    def test_parallel_op_after_preceding_operations(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that ParallelOp regions start at the current tracker height."""
        # Operations before the ParallelOp
        pre_patch = make_prepared_patch()
        meas_stab_pre = make_meas_stab(pre_patch.prepare.res, 7)

        # Parallel regions
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        meas_stab_a = make_meas_stab(patch_a.prepare.res, 4)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 6)

        region_a = Region(Block([patch_a.patch_dec, patch_a.prepare, meas_stab_a, YieldOp()]))
        region_b = Region(Block([patch_b.patch_dec, patch_b.prepare, meas_stab_b, YieldOp()]))
        parallel_op = ParallelOp(result_types=[], par_regions=[region_a, region_b])

        module = ModuleOp([pre_patch.patch_dec, pre_patch.prepare, meas_stab_pre, parallel_op])
        InsertHeight().apply(None, module)

        # Pre-parallel operations
        assert _get_heights(pre_patch.patch_dec) == (0.0, 0.0)
        assert _get_heights(pre_patch.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab_pre) == (0.0, 7.0)

        # Parallel regions start at 7.0
        assert _get_heights(patch_a.patch_dec) == (7.0, 7.0)
        assert _get_heights(patch_a.prepare) == (7.0, 7.0)
        assert _get_heights(meas_stab_a) == (7.0, 11.0)

        assert _get_heights(patch_b.patch_dec) == (7.0, 7.0)
        assert _get_heights(patch_b.prepare) == (7.0, 7.0)
        assert _get_heights(meas_stab_b) == (7.0, 13.0)

    def test_parallel_op_single_region(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test ParallelOp with a single region behaves like sequential."""
        patch = make_prepared_patch()
        meas_stab = make_meas_stab(patch.prepare.res, 8)

        region = Region(Block([patch.patch_dec, patch.prepare, meas_stab, YieldOp()]))
        parallel_op = ParallelOp(result_types=[], par_regions=[region])

        post_patch = make_prepared_patch()

        module = ModuleOp([parallel_op, post_patch.patch_dec, post_patch.prepare])
        InsertHeight().apply(None, module)

        assert _get_heights(patch.patch_dec) == (0.0, 0.0)
        assert _get_heights(patch.prepare) == (0.0, 0.0)
        assert _get_heights(meas_stab) == (0.0, 8.0)

        # After the single-region ParallelOp, tracker is at 8
        assert _get_heights(post_patch.patch_dec) == (8.0, 8.0)
        assert _get_heights(post_patch.prepare) == (8.0, 8.0)

    def test_parallel_op_children_marked_processed(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that ops inside ParallelOp are not processed again during walk."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 5)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 3)

        region_a = Region(Block([patch_a.patch_dec, patch_a.prepare, meas_stab_a, YieldOp()]))
        region_b = Region(Block([patch_b.patch_dec, patch_b.prepare, meas_stab_b, YieldOp()]))
        parallel_op = ParallelOp(result_types=[], par_regions=[region_a, region_b])

        module = ModuleOp([parallel_op])
        InsertHeight().apply(None, module)

        # If children were processed twice, heights would be wrong.
        # Region A starts at 0, Region B also starts at 0 (not at 5).
        assert _get_heights(meas_stab_a) == (0.0, 5.0)
        assert _get_heights(meas_stab_b) == (0.0, 3.0)
