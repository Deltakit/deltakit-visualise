# (c) Copyright Riverlane 2020-2026.
"""Tests for the VisualiseSpacetime pass operation handlers."""

import pytest
from deltakit_compile.dialects.logical_assembly import (
    MeasStabOp,
    MeasureOp,
    MultiPauliMeasOp,
    OrientationEnum,
    PatchDeclarationOp,
    PlacementAttr,
    PrepareOp,
    RotatedPlanarPatchType,
)
from deltakit_compile.dialects.qcore import PauliAttr
from xdsl.dialects import test
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr

from deltakit_visualise.constants import (
    END_HEIGHT_ATTR,
    IN_BRIDGE_PATCHES_ID,
    IN_LOGICAL_PATCHES_ID,
    IN_OP_ID,
    OUT_BRIDGE_PATCHES_ID,
    OUT_LOGICAL_PATCHES_ID,
    OUT_OP_ID,
    START_HEIGHT_ATTR,
)
from deltakit_visualise.passes.visualise_spacetime import (
    get_end_height,
    get_start_height,
    handle_measure_operation,
    handle_measure_stabiliser,
    handle_multi_pauli_measurement,
    handle_patch_declaration,
    handle_prepare_operation,
)
from deltakit_visualise.types import (
    SideColour,
    SpaceTimeVisualisationItem,
    SurfaceColour,
)
from tests.conftest import make_size


class TestHeightAttributes:
    """Tests for height attribute validation."""

    def test_get_start_height_missing_attribute_raises_error(self):
        """Test that get_start_height raises ValueError when START_HEIGHT_ATTR is missing."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        op = PatchDeclarationOp(patch_type)
        # Do not set START_HEIGHT_ATTR

        with pytest.raises(
            ValueError, match=r"is missing a valid visualise\.start_height attribute"
        ):
            get_start_height(op)

    def test_get_end_height_missing_attribute_raises_error(self):
        """Test that get_end_height raises ValueError when END_HEIGHT_ATTR is missing."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        op = PatchDeclarationOp(patch_type)
        # Do not set END_HEIGHT_ATTR

        with pytest.raises(ValueError, match=r"is missing a valid visualise\.end_height attribute"):
            get_end_height(op)

    def test_handle_patch_declaration_missing_start_height_raises_error(self):
        """handle_patch_declaration raises ValueError when START_HEIGHT_ATTR is missing."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        op = PatchDeclarationOp(patch_type)
        op.attributes[IN_OP_ID] = StringAttr("patch_A_0_")
        # Do not set START_HEIGHT_ATTR
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        with pytest.raises(
            ValueError, match=r"is missing a valid visualise\.start_height attribute"
        ):
            handle_patch_declaration(op, visualisation_data)


class TestHandlePatchDeclaration:
    """Tests for handle_patch_declaration handler."""

    def test_with_placement_outputs_surface(self):
        """Test that PatchDeclarationOp with placement outputs surface data."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        op = PatchDeclarationOp(patch_type)
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[IN_OP_ID] = StringAttr("patch_A_0_")
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_patch_declaration(op, visualisation_data)

        assert len(visualisation_data) == 1
        data = visualisation_data[0]
        assert data["type"] == "surface"
        assert data["op_name"] == "log_asm.patch_dec"
        assert data["location"] == (1, 1)
        assert data["colour"] == SurfaceColour.GREY
        assert data["size"] == (5, 5)
        assert "id" in data
        assert "startHeight" in data


class TestHandlePrepareOperation:
    """Tests for handle_prepare_operation handler."""

    @pytest.mark.parametrize(
        ("basis", "expected_colour"),
        [
            (PauliAttr.X(), SurfaceColour.RED),
            (PauliAttr.Z(), SurfaceColour.BLUE),
        ],
    )
    def test_with_placement_outputs_coloured_surface(
        self,
        basis: PauliAttr,
        expected_colour: SurfaceColour,
    ):
        """Test that PrepareOp with placement outputs correctly coloured surface."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        patch = test.TestOp(result_types=[patch_type]).res[0]
        op = PrepareOp(patch, basis)
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[IN_OP_ID] = StringAttr("patch_A_1_")
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_prepare_operation(op, visualisation_data)

        assert len(visualisation_data) == 1
        data = visualisation_data[0]
        assert data["type"] == "surface"
        assert data["op_name"] == "log_asm.prepare"
        assert data["colour"] == expected_colour
        assert data["location"] == (1, 1)
        assert data["size"] == (5, 5)
        assert "id" in data
        assert "startHeight" in data


class TestHandleMeasStabOp:
    """Tests for handle_measure_stabiliser handler."""

    @pytest.mark.parametrize(
        ("orientation", "expected_colours"),
        [
            (OrientationEnum.VERTICAL_Z, (SideColour.RED, SideColour.BLUE)),
            (OrientationEnum.HORIZONTAL_Z, (SideColour.BLUE, SideColour.RED)),
        ],
    )
    def test_with_placement_outputs_coloured_sides(
        self,
        orientation: OrientationEnum,
        expected_colours: tuple[SideColour, SideColour],
    ):
        """Test that MeasStabOp with placement outputs correctly coloured sides."""
        patch_type = RotatedPlanarPatchType(make_size(5, 5), PlacementAttr([1, 1], orientation))
        patch = test.TestOp(result_types=[patch_type]).res[0]
        op = MeasStabOp(patch, 10)
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[END_HEIGHT_ATTR] = IntAttr(10)
        op.attributes[IN_OP_ID] = StringAttr("patch_A_1_")
        op.attributes[OUT_OP_ID] = StringAttr("patch_A_2_")
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_measure_stabiliser(op, visualisation_data)

        assert len(visualisation_data) == 3
        # Check start-gap surface (first item)
        start_gap = visualisation_data[0]
        assert start_gap["type"] == "surface"
        assert start_gap["colour"] == SurfaceColour.NONE
        assert start_gap["id"] == "patch_A_1_"
        # Check sides data (second item)
        sides_data = visualisation_data[1]
        assert sides_data["type"] == "side"
        assert sides_data["op_name"] == "log_asm.meas_stab"
        assert sides_data["colourScheme"] == expected_colours
        assert sides_data["sides"] == {"+X": True, "-X": True, "+Y": True, "-Y": True}
        # Check end-gap surface (third item)
        surface_data = visualisation_data[2]
        assert surface_data["type"] == "surface"
        assert surface_data["op_name"] == "log_asm.meas_stab"
        assert surface_data["colour"] == SurfaceColour.NONE
        assert surface_data["location"] == (1, 1)
        assert surface_data["size"] == (5, 5)
        assert "id" in surface_data
        assert "startHeight" in surface_data


class TestHandleMultiPauliMeasurement:
    """Tests for handle_multi_pauli_measurement handler."""

    def test_zz_basis_outputs_red_bridge_surfaces(self):
        """Test that MultiPauliMeasOp with ZZ basis outputs red bridge surfaces."""
        patch_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([0, 0], OrientationEnum.VERTICAL_Z)
            ),
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([6, 0], OrientationEnum.VERTICAL_Z)
            ),
        ]
        bridge_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([3, 0], OrientationEnum.VERTICAL_Z)
            ),
        ]
        patches = test.TestOp(result_types=patch_types).res
        bridges = test.TestOp(result_types=bridge_types).res

        op = MultiPauliMeasOp(5, [PauliAttr.Z(), PauliAttr.Z()], patches, bridges)
        # Set up required attributes for patch IDs
        op.attributes[IN_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_in_0"), StringAttr("logical_in_1")]
        )
        op.attributes[OUT_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_out_0"), StringAttr("logical_out_1")]
        )
        op.attributes[IN_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_in_0")])
        op.attributes[OUT_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_out_0")])
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[END_HEIGHT_ATTR] = IntAttr(5)
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_multi_pauli_measurement(op, visualisation_data)

        # Output: 2 logical (start surface + sides + end surface each)
        # + 1 bridge (surface + sides + surface) = 9
        assert len(visualisation_data) == 9

        # Check sides data
        sides_data = [d for d in visualisation_data if d["type"] == "side"]
        assert len(sides_data) == 3
        for s in sides_data:
            assert s["op_name"] == "log_asm.multi_pauli_meas"
        assert sides_data[0]["sides"] == {
            "+X": False,
            "-X": True,
            "+Y": True,
            "-Y": True,
        }
        assert sides_data[1]["sides"] == {
            "+X": True,
            "-X": False,
            "+Y": True,
            "-Y": True,
        }
        assert sides_data[2]["sides"] == {
            "+X": False,
            "-X": False,
            "+Y": True,
            "-Y": True,
        }

        # 2 logical patches x 3 items + 1 bridge x 3 items = 9 total surfaces/sides
        surfaces = [d for d in visualisation_data if d["type"] == "surface"]
        assert len(surfaces) == 6
        # Check for RED surface (ZZ basis) for the bridge
        red_surfaces = [s for s in surfaces if s["colour"] == SurfaceColour.RED]
        assert len(red_surfaces) == 2  # Bridge start and end surfaces
        assert red_surfaces[0]["location"] == (3, 0)

    def test_xx_basis_outputs_blue_bridge_surfaces(self):
        """Test that MultiPauliMeasOp with XX basis outputs blue bridge surfaces."""
        patch_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([0, 0], OrientationEnum.HORIZONTAL_Z)
            ),
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([6, 0], OrientationEnum.HORIZONTAL_Z)
            ),
        ]
        bridge_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([3, 0], OrientationEnum.HORIZONTAL_Z)
            ),
        ]
        patches = test.TestOp(result_types=patch_types).res
        bridges = test.TestOp(result_types=bridge_types).res

        op = MultiPauliMeasOp(10, [PauliAttr.X(), PauliAttr.X()], patches, bridges)
        # Set up required attributes for patch IDs
        op.attributes[IN_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_in_0"), StringAttr("logical_in_1")]
        )
        op.attributes[OUT_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_out_0"), StringAttr("logical_out_1")]
        )
        op.attributes[IN_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_in_0")])
        op.attributes[OUT_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_out_0")])
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[END_HEIGHT_ATTR] = IntAttr(10)
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_multi_pauli_measurement(op, visualisation_data)

        # Check for BLUE surface (XX basis) for the bridge
        surfaces = [d for d in visualisation_data if d["type"] == "surface"]
        blue_surfaces = [s for s in surfaces if s["colour"] == SurfaceColour.BLUE]
        assert len(blue_surfaces) == 2  # Bridge start and end surfaces

    def test_computes_sides_from_patch_geometry(self):
        """Test that sides are computed directly from patch geometry."""
        patch_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([0, 0], OrientationEnum.VERTICAL_Z)
            ),
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([4, 0], OrientationEnum.VERTICAL_Z)
            ),
        ]
        bridge_types = [
            RotatedPlanarPatchType(
                make_size(3, 3), PlacementAttr([3, 0], OrientationEnum.VERTICAL_Z)
            ),
        ]
        patches = test.TestOp(result_types=patch_types).res
        bridges = test.TestOp(result_types=bridge_types).res

        op = MultiPauliMeasOp(5, [PauliAttr.Z(), PauliAttr.Z()], patches, bridges)
        # Set up required attributes for patch IDs
        op.attributes[IN_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_in_0"), StringAttr("logical_in_1")]
        )
        op.attributes[OUT_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_out_0"), StringAttr("logical_out_1")]
        )
        op.attributes[IN_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_in_0")])
        op.attributes[OUT_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_out_0")])
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[END_HEIGHT_ATTR] = IntAttr(5)

        visualisation_data: list[SpaceTimeVisualisationItem] = []
        handle_multi_pauli_measurement(op, visualisation_data)

        sides_data = [d for d in visualisation_data if d["type"] == "side"]
        assert len(sides_data) == 3

        assert sides_data[0]["sides"] == {
            "+X": False,
            "-X": True,
            "+Y": True,
            "-Y": True,
        }
        assert sides_data[1]["sides"] == {
            "+X": True,
            "-X": True,
            "+Y": True,
            "-Y": True,
        }
        assert sides_data[2]["sides"] == {
            "+X": True,
            "-X": False,
            "+Y": True,
            "-Y": True,
        }
        op = MultiPauliMeasOp(5, [PauliAttr.X(), PauliAttr.Y()], patches, bridges)
        op.attributes[IN_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_in_0"), StringAttr("logical_in_1")]
        )
        op.attributes[OUT_LOGICAL_PATCHES_ID] = ArrayAttr(
            [StringAttr("logical_out_0"), StringAttr("logical_out_1")]
        )
        op.attributes[IN_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_in_0")])
        op.attributes[OUT_BRIDGE_PATCHES_ID] = ArrayAttr([StringAttr("bridge_out_0")])
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[END_HEIGHT_ATTR] = IntAttr(5)
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        with pytest.raises(ValueError, match="Unsupported basis combination"):
            handle_multi_pauli_measurement(op, visualisation_data)


class TestHandleMeasureOperation:
    """Tests for handle_measure_operation handler."""

    @pytest.mark.parametrize(
        ("basis", "expected_colour"),
        [
            (PauliAttr.X(), SurfaceColour.RED),
            (PauliAttr.Z(), SurfaceColour.BLUE),
        ],
    )
    def test_with_placement_outputs_coloured_surface(
        self,
        basis: PauliAttr,
        expected_colour: SurfaceColour,
    ):
        """Test that MeasureOp with placement outputs correctly coloured surface."""
        patch_type = RotatedPlanarPatchType(
            make_size(5, 5), PlacementAttr([1, 1], OrientationEnum.VERTICAL_Z)
        )
        patch = test.TestOp(result_types=[patch_type]).res[0]
        op = MeasureOp(patch, basis)
        op.attributes[START_HEIGHT_ATTR] = IntAttr(0)
        op.attributes[OUT_OP_ID] = StringAttr("measurement")
        visualisation_data: list[SpaceTimeVisualisationItem] = []

        handle_measure_operation(op, visualisation_data)

        assert len(visualisation_data) == 1
        data = visualisation_data[0]
        assert data["type"] == "surface"
        assert data["op_name"] == "log_asm.measure"
        assert data["colour"] == expected_colour
        assert data["location"] == (1, 1)
        assert data["size"] == (5, 5)
        assert "id" in data
        assert "startHeight" in data
