# (c) Copyright Riverlane 2020-2026.
"""Tests for the AssignId pass."""

from unittest.mock import MagicMock

import pytest
from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
)
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, StringAttr
from xdsl.ir import Operation

from deltakit_visualise.constants import (
    IN_BRIDGE_PATCHES_ID,
    IN_LOGICAL_PATCHES_ID,
    IN_OP_ID,
    OUT_BRIDGE_PATCHES_ID,
    OUT_LOGICAL_PATCHES_ID,
    OUT_OP_ID,
)
from deltakit_visualise.passes.assign_id import AssignId
from deltakit_visualise.utils.id_tracker import IdTracker
from tests.conftest import (
    MakeBridgePatch,
    MakeMeasStab,
    MakeMeasure,
    MakeMultiPauliMeas,
    MakePreparedPatch,
)


def _get_in_id(op: Operation) -> str:
    """Extract the IN_OP_ID attribute from an operation."""
    attr = op.attributes.get(IN_OP_ID)
    assert isinstance(attr, StringAttr), f"Missing {IN_OP_ID} on {op.name}"
    return attr.data


def _get_out_id(op: Operation) -> str:
    """Extract the OUT_OP_ID attribute from an operation."""
    attr = op.attributes.get(OUT_OP_ID)
    assert isinstance(attr, StringAttr), f"Missing {OUT_OP_ID} on {op.name}"
    return attr.data


def _get_id_list(op: Operation, key: str) -> list[str]:
    """Extract a list of string IDs from an ArrayAttr attribute."""
    attr = op.attributes.get(key)
    assert isinstance(attr, ArrayAttr), f"Missing {key} on {op.name}"
    return [item.data for item in attr]


class TestAssignIdSimpleChain:
    """Tests for AssignId pass on simple single-patch chains."""

    @pytest.mark.parametrize(
        ("min_rounds", "include_measure"),
        [
            (None, False),
            (10, False),
            (10, True),
        ],
        ids=[
            "declare+prepare",
            "declare+prepare+meas_stab",
            "declare+prepare+meas_stab+measure",
        ],
    )
    # PLR0913: suppresses "too many arguments" - needed for fixtures + parametrise
    def test_single_chain_fresh_ids_are_unique(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
        min_rounds: int | None,
        include_measure: bool,
    ) -> None:
        """Test that freshly-assigned IDs along a single chain are all unique.

        Note: meas_stab IN_OP_ID intentionally chains (reuses) the ID of its
        input SSA value, so we only collect IDs from fresh ``assign()`` calls.
        """
        patch = make_prepared_patch()
        ops: list[Operation] = [patch.patch_dec, patch.prepare]

        if min_rounds is not None:
            meas_stab = make_meas_stab(patch.prepare.res, min_rounds)
            ops.append(meas_stab)

            if include_measure:
                measure = make_measure(meas_stab.res)
                ops.append(measure)

        module = ModuleOp(ops)
        AssignId().apply(None, module)

        # Collect all fresh IDs - meas_stab IN_OP_ID is also fresh (not chained)
        fresh_ids: list[str] = []
        fresh_ids.append(_get_in_id(patch.patch_dec))
        fresh_ids.append(_get_in_id(patch.prepare))

        if min_rounds is not None:
            fresh_ids.append(_get_in_id(meas_stab))
            fresh_ids.append(_get_out_id(meas_stab))

            if include_measure:
                fresh_ids.append(_get_out_id(measure))

        # All freshly-assigned IDs must be unique
        assert len(fresh_ids) == len(set(fresh_ids))

    def test_patch_declaration_has_in_id(
        self,
        make_prepared_patch: MakePreparedPatch,
    ) -> None:
        """Test that PatchDeclarationOp gets an IN_OP_ID attribute."""
        patch = make_prepared_patch()
        module = ModuleOp([patch.patch_dec, patch.prepare])
        AssignId().apply(None, module)

        in_id = _get_in_id(patch.patch_dec)
        assert isinstance(in_id, str)
        assert len(in_id) > 0

    def test_prepare_has_in_id(
        self,
        make_prepared_patch: MakePreparedPatch,
    ) -> None:
        """Test that PrepareOp gets an IN_OP_ID attribute."""
        patch = make_prepared_patch()
        module = ModuleOp([patch.patch_dec, patch.prepare])
        AssignId().apply(None, module)

        in_id = _get_in_id(patch.prepare)
        assert isinstance(in_id, str)
        assert len(in_id) > 0

    def test_meas_stab_has_in_and_out_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that MeasStabOp gets both IN_OP_ID and OUT_OP_ID attributes."""
        patch = make_prepared_patch()
        meas_stab = make_meas_stab(patch.prepare.res, 5)
        module = ModuleOp([patch.patch_dec, patch.prepare, meas_stab])
        AssignId().apply(None, module)

        in_id = _get_in_id(meas_stab)
        out_id = _get_out_id(meas_stab)
        assert in_id != out_id

    def test_meas_stab_in_id_is_fresh(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test that MeasStabOp IN_OP_ID is a fresh ID, not chained from PrepareOp."""
        patch = make_prepared_patch()
        meas_stab = make_meas_stab(patch.prepare.res, 5)
        module = ModuleOp([patch.patch_dec, patch.prepare, meas_stab])
        AssignId().apply(None, module)

        # IN_OP_ID is a fresh standalone ID — not the same as the previous op's output
        assert _get_in_id(meas_stab) != _get_in_id(patch.prepare)

    def test_measure_has_out_id(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
    ) -> None:
        """Test that MeasureOp gets an OUT_OP_ID attribute."""
        patch = make_prepared_patch()
        meas_stab = make_meas_stab(patch.prepare.res, 5)
        measure = make_measure(meas_stab.res)
        module = ModuleOp([patch.patch_dec, patch.prepare, meas_stab, measure])
        AssignId().apply(None, module)

        out_id = _get_out_id(measure)
        assert isinstance(out_id, str)
        assert len(out_id) > 0


class TestAssignIdMultiPauli:
    """Tests for AssignId pass with MultiPauliMeasOp."""

    def test_multi_pauli_has_logical_patch_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test that MultiPauliMeasOp gets logical patch ID array attributes."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

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
            ]
        )
        AssignId().apply(None, module)

        in_logical_ids = _get_id_list(multi_pauli, IN_LOGICAL_PATCHES_ID)
        out_logical_ids = _get_id_list(multi_pauli, OUT_LOGICAL_PATCHES_ID)

        assert len(in_logical_ids) == 2
        assert len(out_logical_ids) == 2
        # Input and output IDs must differ
        assert set(in_logical_ids).isdisjoint(set(out_logical_ids))

    def test_multi_pauli_has_bridge_patch_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test that MultiPauliMeasOp gets bridge patch ID array attributes."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

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
            ]
        )
        AssignId().apply(None, module)

        in_bridge_ids = _get_id_list(multi_pauli, IN_BRIDGE_PATCHES_ID)
        out_bridge_ids = _get_id_list(multi_pauli, OUT_BRIDGE_PATCHES_ID)

        assert len(in_bridge_ids) == 1
        assert len(out_bridge_ids) == 1
        assert in_bridge_ids[0] != out_bridge_ids[0]

    def test_multi_pauli_all_ids_unique(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test that all IDs across a MultiPauliMeasOp are globally unique."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

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
            ]
        )
        AssignId().apply(None, module)

        # All IDs are fresh — collect everything
        fresh_ids: list[str] = []
        fresh_ids.append(_get_in_id(patch_a.patch_dec))
        fresh_ids.append(_get_in_id(patch_a.prepare))
        fresh_ids.append(_get_in_id(meas_stab_a))
        fresh_ids.append(_get_out_id(meas_stab_a))
        fresh_ids.append(_get_in_id(patch_b.patch_dec))
        fresh_ids.append(_get_in_id(patch_b.prepare))
        fresh_ids.append(_get_in_id(meas_stab_b))
        fresh_ids.append(_get_out_id(meas_stab_b))
        fresh_ids.append(_get_in_id(bridge_dec))
        fresh_ids.extend(_get_id_list(multi_pauli, IN_LOGICAL_PATCHES_ID))
        fresh_ids.extend(_get_id_list(multi_pauli, OUT_LOGICAL_PATCHES_ID))
        fresh_ids.extend(_get_id_list(multi_pauli, OUT_BRIDGE_PATCHES_ID))

        # All freshly-assigned IDs must be unique
        assert len(fresh_ids) == len(set(fresh_ids))
        assert all(len(id_str) > 0 for id_str in fresh_ids)

    def test_meas_stab_after_multi_pauli_chains_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test that meas_stab after MultiPauliMeasOp correctly chains IDs."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

        # meas_stab on the first output of multi_pauli
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
        AssignId().apply(None, module)

        # meas_stab_post.IN_OP_ID is fresh — not chained from multi_pauli's OUT_LOGICAL[0]
        out_logical_ids = _get_id_list(multi_pauli, OUT_LOGICAL_PATCHES_ID)
        assert _get_in_id(meas_stab_post) != out_logical_ids[0]

        # meas_stab_post should have a distinct OUT_OP_ID
        assert _get_out_id(meas_stab_post) != _get_in_id(meas_stab_post)


class TestAssignIdConsecutiveMeasStab:
    """Tests for consecutive meas_stab ID chaining."""

    @pytest.mark.parametrize(
        "num_meas_stabs",
        [1, 2, 3],
        ids=["1-meas_stab", "2-meas_stabs", "3-meas_stabs"],
    )
    def test_consecutive_meas_stab_chains_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        num_meas_stabs: int,
    ) -> None:
        """Test that consecutive meas_stab operations chain IDs correctly."""
        patch = make_prepared_patch()
        ops: list[Operation] = [patch.patch_dec, patch.prepare]

        meas_stabs: list[MeasStabOp] = []
        prev_res = patch.prepare.res
        for _ in range(num_meas_stabs):
            meas_stab = make_meas_stab(prev_res, 5)
            meas_stabs.append(meas_stab)
            ops.append(meas_stab)
            prev_res = meas_stab.res

        module = ModuleOp(ops)
        AssignId().apply(None, module)

        # Each meas_stab gets fresh IN_OP_ID and OUT_OP_ID — no chaining
        all_ids = [_get_in_id(patch.patch_dec), _get_in_id(patch.prepare)]
        for meas_stab in meas_stabs:
            all_ids.append(_get_in_id(meas_stab))
            all_ids.append(_get_out_id(meas_stab))
        assert len(all_ids) == len(set(all_ids)), "All IDs must be unique"

    def test_two_independent_chains_have_distinct_ids(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
    ) -> None:
        """Test two independent chains produce distinct sets of IDs."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 5)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 3)

        module = ModuleOp(
            [
                patch_a.patch_dec,
                patch_a.prepare,
                meas_stab_a,
                patch_b.patch_dec,
                patch_b.prepare,
                meas_stab_b,
            ]
        )
        AssignId().apply(None, module)

        chain_a_ids = {
            _get_in_id(patch_a.patch_dec),
            _get_in_id(patch_a.prepare),
            _get_in_id(meas_stab_a),
            _get_out_id(meas_stab_a),
        }
        chain_b_ids = {
            _get_in_id(patch_b.patch_dec),
            _get_in_id(patch_b.prepare),
            _get_in_id(meas_stab_b),
            _get_out_id(meas_stab_b),
        }

        # The two chains should have no ID overlap
        assert chain_a_ids.isdisjoint(chain_b_ids)

    def test_bridge_patch_id_not_duplicated_across_ops(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_bridge_patch: MakeBridgePatch,
        make_meas_stab: MakeMeasStab,
        make_multi_pauli_meas: MakeMultiPauliMeas,
    ) -> None:
        """Test that bridge patch IDs are not duplicated
        between PatchDeclarationOp and MultiPauliMeasOp."""
        patch_a = make_prepared_patch()
        patch_b = make_prepared_patch()
        bridge_dec = make_bridge_patch()

        meas_stab_a = make_meas_stab(patch_a.prepare.res, 10)
        meas_stab_b = make_meas_stab(patch_b.prepare.res, 10)

        multi_pauli = make_multi_pauli_meas(
            logical_patches=[meas_stab_a.res, meas_stab_b.res],
            bridge_patches=[bridge_dec.res],
            rounds=3,
        )

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
            ]
        )
        AssignId().apply(None, module)

        # All IDs are fresh — collect everything including IN_OP_IDs and IN_LOGICAL_PATCHES_ID
        fresh_ids: list[str] = []
        fresh_ids.append(_get_in_id(patch_a.patch_dec))
        fresh_ids.append(_get_in_id(patch_a.prepare))
        fresh_ids.append(_get_in_id(patch_b.patch_dec))
        fresh_ids.append(_get_in_id(patch_b.prepare))
        fresh_ids.append(_get_in_id(bridge_dec))
        fresh_ids.append(_get_in_id(meas_stab_a))
        fresh_ids.append(_get_out_id(meas_stab_a))
        fresh_ids.append(_get_in_id(meas_stab_b))
        fresh_ids.append(_get_out_id(meas_stab_b))
        fresh_ids.extend(_get_id_list(multi_pauli, IN_LOGICAL_PATCHES_ID))
        fresh_ids.extend(_get_id_list(multi_pauli, OUT_LOGICAL_PATCHES_ID))
        fresh_ids.extend(_get_id_list(multi_pauli, IN_BRIDGE_PATCHES_ID))
        fresh_ids.extend(_get_id_list(multi_pauli, OUT_BRIDGE_PATCHES_ID))

        duplicates = [id_ for id_ in fresh_ids if fresh_ids.count(id_) > 1]
        assert duplicates == [], f"Duplicate IDs found: {set(duplicates)}"

    def test_duplicate_id_detected(
        self,
        make_prepared_patch: MakePreparedPatch,
        make_meas_stab: MakeMeasStab,
        make_measure: MakeMeasure,
    ) -> None:
        """Test that all assigned IDs are unique even when many operations share structure."""
        patches = [make_prepared_patch() for _ in range(5)]
        ops: list[Operation] = []
        meas_stabs: list[MeasStabOp] = []

        for patch in patches:
            ops.append(patch.patch_dec)
            ops.append(patch.prepare)
            ms = make_meas_stab(patch.prepare.res, 5)
            meas_stabs.append(ms)
            ops.append(ms)

        measures = [make_measure(ms.res) for ms in meas_stabs]
        ops.extend(measures)

        module = ModuleOp(ops)
        AssignId().apply(None, module)

        all_ids: list[str] = []
        for patch in patches:
            all_ids.append(_get_in_id(patch.patch_dec))
            all_ids.append(_get_in_id(patch.prepare))
        for ms in meas_stabs:
            all_ids.append(_get_in_id(ms))
            all_ids.append(_get_out_id(ms))
        for m in measures:
            all_ids.append(_get_out_id(m))

        duplicates = [id_ for id_ in all_ids if all_ids.count(id_) > 1]
        assert duplicates == [], f"Duplicate IDs found: {set(duplicates)}"


class TestIdTracker:
    """Unit tests for IdTracker edge cases."""

    def test_make_unique_appends_suffix_on_collision(self) -> None:
        """Duplicate base names get a _1 suffix."""
        tracker = IdTracker()
        first = tracker._make_unique("foo")
        second = tracker._make_unique("foo")
        assert first == "foo"
        assert second == "foo_1"

    def test_assign_without_name_hint(self) -> None:
        """Assign falls back to counter-based ID when name_hint is None."""
        ssa = MagicMock()
        ssa.name_hint = None
        tracker = IdTracker()
        id_str = tracker.assign(ssa)
        assert id_str == "gen_id_0"

    def test_get_or_assign_new_value(self) -> None:
        """get_or_assign assigns a new ID for an untracked SSA value."""
        ssa = MagicMock()
        ssa.name_hint = "x"
        tracker = IdTracker()
        result = tracker.get_or_assign(ssa)
        assert result == "x"
        # Second call returns the same cached ID
        assert tracker.get_or_assign(ssa) == "x"
