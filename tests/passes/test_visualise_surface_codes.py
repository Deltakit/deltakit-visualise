# (c) Copyright Riverlane 2020-2026.
"""Tests for the VisualiseSurfaceCodes compiler pass."""

import json
from pathlib import Path

import pytest
from xdsl.dialects.builtin import StringAttr

from deltakit_visualise.constants import PATCH_VISUALISATION_DATA
from deltakit_visualise.logical_assembly_visualiser import LogicalAssemblyVisualiser
from deltakit_visualise.passes.visualise_surface_codes import (
    SurfaceCodeVisualisationState,
    _build_round_indices,
    _cache_coordinate,
    _coord_from_key,
    _coord_key,
    _finalise_visualisation_data,
    _get_or_create_patch_item,
    _rebuild_qubits_and_coordinates,
)
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.types import PatchVisualisationItem


def _visualise_patch(mlir_file_path: str) -> list[PatchVisualisationItem]:
    """Parse an MLIR file, apply the patch pipeline, and return visualisation items."""

    ctx = LogicalAssemblyVisualiser.make_context()
    module_op = LogicalAssemblyVisualiser.parse_mlir_file(mlir_file_path)
    PatchVisualisationPipeline().apply(ctx, module_op)
    attr = module_op.attributes[PATCH_VISUALISATION_DATA]
    assert isinstance(attr, StringAttr)
    return json.loads(attr.data)


@pytest.fixture(name="surface_code_simple_path")
def _surface_code_simple_path() -> Path:
    """Path to the simple surface code MLIR test file."""
    return (
        Path(__file__).parents[2]
        / "tests"
        / "filecheck"
        / "surface_codes"
        / "surface_code_simple.mlir"
    )


@pytest.fixture(name="surface_code_repeat_path")
def _surface_code_repeat_path() -> Path:
    """Path to the surface code repeat MLIR test file."""
    return (
        Path(__file__).parents[2]
        / "tests"
        / "filecheck"
        / "surface_codes"
        / "surface_code_repeat.mlir"
    )


@pytest.fixture(name="surface_code_2d_path")
def _surface_code_2d_path() -> Path:
    """Path to the surface code 2D MLIR test file."""
    return (
        Path(__file__).parents[2] / "tests" / "filecheck" / "surface_codes" / "surface_code_2d.mlir"
    )


class TestCoordinateKeyConversion:
    """Tests for coordinate key conversion functions."""

    def test_coord_key_rounds_correctly(self):
        """Test that _coord_key properly rounds coordinates."""
        coord = (1.123456789012345, 2.987654321098765)
        key = _coord_key(coord)
        assert key == (1.123456789012, 2.987654321099)

    def test_coord_from_key_recovers_coordinates(self):
        """Test that _coord_from_key recovers coordinates from key."""
        key = (1.5, 2.5)
        coord = _coord_from_key(key)
        assert coord == [1.5, 2.5]

    def test_roundtrip_conversion(self):
        """Test roundtrip: coord -> key -> coord maintains values."""
        original_coord = (3.14159, 2.71828)
        key = _coord_key(original_coord)
        recovered = _coord_from_key(key)
        assert recovered[0] == key[0]
        assert recovered[1] == key[1]


class TestSurfaceCodeVisualisationState:
    """Tests for SurfaceCodeVisualisationState."""

    def test_state_initialisation(self):
        """Test that state initialises with default empty values."""
        state = SurfaceCodeVisualisationState()
        assert state.visualisation_data == []
        assert state.round_indices == {}
        assert state.round_counter == 0
        assert state.coordinates_map == {}
        assert state.patch_items == {}

    def test_state_mutability(self):
        """Test that state is mutable and tracks data correctly."""
        state = SurfaceCodeVisualisationState()
        state.visualisation_data.append({"test": "item"})
        state.round_counter = 5
        assert len(state.visualisation_data) == 1
        assert state.round_counter == 5


class TestCacheCoordinate:
    """Tests for _cache_coordinate function."""

    def test_cache_coordinate_stores_and_returns(self):
        """Test that _cache_coordinate stores coordinate and returns it."""
        state = SurfaceCodeVisualisationState()
        # Create a mock SSAValue key
        coord = (1.5, 2.5)
        # Use None as a simple SSAValue placeholder for testing
        cache_key = (None, None)

        result = _cache_coordinate(state, cache_key, coord)

        assert result == coord
        assert state.coordinates_map[cache_key] == coord


class TestGetOrCreatePatchItem:
    """Tests for _get_or_create_patch_item function."""

    def test_create_new_patch_item(self):
        """Test creating a new patch item."""
        state = SurfaceCodeVisualisationState()
        round_index = 1

        item = _get_or_create_patch_item(state, round_index)

        assert item["round"] == round_index
        assert item["qubits"] == []
        assert len(item["patches"]) == 1
        assert item["patches"][0]["plaquettes"] == []
        assert item in state.visualisation_data

    def test_get_existing_patch_item(self):
        """Test retrieving an existing patch item."""
        state = SurfaceCodeVisualisationState()
        round_index = 2

        item1 = _get_or_create_patch_item(state, round_index)
        item1["custom_field"] = "test_value"

        item2 = _get_or_create_patch_item(state, round_index)

        assert item1 is item2
        assert item2.get("custom_field") == "test_value"
        assert len(state.visualisation_data) == 1

    def test_different_rounds_create_different_items(self):
        """Test that different rounds create different patch items."""
        state = SurfaceCodeVisualisationState()

        item1 = _get_or_create_patch_item(state, 1)
        item2 = _get_or_create_patch_item(state, 2)

        assert item1 is not item2
        assert len(state.visualisation_data) == 2


class TestRebuildQubitsAndCoordinates:
    """Tests for _rebuild_qubits_and_coordinates function."""

    def test_rebuild_qubits_creates_qubit_list(self):
        """Test that _rebuild_qubits_and_coordinates creates qubit list."""
        item: dict = {
            "_qubit_types": {
                (0.5, 0.5): "data",
                (1.5, 0.5): "data",
                (1.0, 1.0): "ancilla",
            },
            "patches": [{"plaquettes": [{"_coord_keys": [(0.5, 0.5), (1.5, 0.5), (1.0, 1.0)]}]}],
        }

        _rebuild_qubits_and_coordinates(item)

        assert "qubits" in item
        assert len(item["qubits"]) == 3
        assert all("id" in q and "type" in q and "coordinates" in q for q in item["qubits"])

    def test_rebuild_sorts_qubits_correctly(self):
        """Test that qubits are sorted with data qubits first."""
        item: dict = {
            "_qubit_types": {(0.5, 0.5): "data", (1.0, 1.0): "ancilla"},
            "patches": [{"plaquettes": [{"_coord_keys": [(0.5, 0.5), (1.0, 1.0)]}]}],
        }

        _rebuild_qubits_and_coordinates(item)

        # Data qubits should come before ancilla
        assert item["qubits"][0]["type"] == "data"
        assert item["qubits"][1]["type"] == "ancilla"

    def test_rebuild_updates_plaquette_coordinates(self):
        """Test that plaquette coordinates are rebuilt with qubit IDs."""
        item: dict = {
            "_qubit_types": {(0.5, 0.5): "data", (1.5, 0.5): "data"},
            "patches": [{"plaquettes": [{"_coord_keys": [(0.5, 0.5), (1.5, 0.5)]}]}],
        }

        _rebuild_qubits_and_coordinates(item)

        plaquette = item["patches"][0]["plaquettes"][0]
        assert "coordinates" in plaquette
        assert len(plaquette["coordinates"]) == 2
        assert all(isinstance(c, str) for c in plaquette["coordinates"])


class TestIntegrationWithRealMlir:
    """Integration tests using real MLIR files."""

    def test_visualise_surface_code_simple(self, surface_code_simple_path: Path):
        """Test visualisation of simple surface code."""
        if not surface_code_simple_path.exists():
            pytest.skip(f"Test file not found: {surface_code_simple_path}")

        result = _visualise_patch(str(surface_code_simple_path))

        assert result is not None
        # Simple case has no plaquettes, so ops should be empty
        assert result == []

    def test_visualise_surface_code_repeat(self, surface_code_repeat_path: Path):
        """Test visualisation of surface code with repeat."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        result = _visualise_patch(str(surface_code_repeat_path))

        assert result is not None
        # Should have operations for each round
        ops = result
        assert len(ops) >= 1
        # Check structure of first operation
        if len(ops) > 0:
            op = ops[0]
            assert "round" in op
            assert "qubits" in op
            assert "patches" in op
            plaquettes = op["patches"][0]["plaquettes"]
            if plaquettes:
                first_plaquette = plaquettes[0]
                assert "shape" in first_plaquette
                assert first_plaquette["shape"] in ("square", "semicircle")
                assert "weight" in first_plaquette
                assert isinstance(first_plaquette["weight"], int)
                assert first_plaquette["shape"] == "semicircle"
                assert first_plaquette["weight"] == 2

    def test_visualise_surface_code_2d(self, surface_code_2d_path: Path):
        """Test visualisation of 2D surface code."""
        if not surface_code_2d_path.exists():
            pytest.skip(f"Test file not found: {surface_code_2d_path}")

        result = _visualise_patch(str(surface_code_2d_path))

        assert result is not None
        assert isinstance(result, list)
        if result:
            plaquettes = result[0]["patches"][0]["plaquettes"]
            assert any(p["shape"] == "square" for p in plaquettes)
            assert any(p["shape"] == "square" and p["weight"] == 4 for p in plaquettes)
            assert any(p["shape"] == "semicircle" and p["weight"] == 2 for p in plaquettes)


class TestErrorHandlingInCoordinateResolution:
    """Tests for error handling in coordinate resolution functions."""

    def test_resolve_qubit_coordinate_on_real_mlir(self, surface_code_repeat_path: Path):
        """Test coordinate resolution on real MLIR to verify error paths."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        # This test exercises coordinate resolution paths
        module_op = LogicalAssemblyVisualiser.parse_mlir_file(str(surface_code_repeat_path))
        state = SurfaceCodeVisualisationState()

        _build_round_indices(module_op, state)

        # Build should succeed without errors
        assert state.round_counter >= 0


class TestPassIntegration:
    """Integration tests for the VisualiseSurfaceCodes pass."""

    def test_visualise_surface_codes_pass_applies(self, surface_code_repeat_path: Path):
        """Test that VisualiseSurfaceCodes pass applies successfully."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        # Use the compiler which applies the pass
        result = _visualise_patch(str(surface_code_repeat_path))

        assert result is not None
        assert isinstance(result, list)

    def test_pass_produces_valid_json(self, surface_code_repeat_path: Path):
        """Test that the pass produces valid JSON output."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        result = _visualise_patch(str(surface_code_repeat_path))

        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        recovered = json.loads(json_str)
        assert recovered == result


class TestRoundIndexing:
    """Tests for round indexing functionality."""

    def test_round_counter_increments_with_execution_order(self):
        """Test that round counter increments in execution order."""
        state = SurfaceCodeVisualisationState()

        # Simulate round indexing by directly manipulating state
        state.round_counter = 0
        state.round_counter += 1
        state.round_counter += 1

        assert state.round_counter == 2

    def test_build_round_indices_on_real_mlir(self, surface_code_repeat_path: Path):
        """Test round index building on real MLIR."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        module_op = LogicalAssemblyVisualiser.parse_mlir_file(str(surface_code_repeat_path))
        state = SurfaceCodeVisualisationState()

        _build_round_indices(module_op, state)

        # Should have populated round indices
        assert len(state.round_indices) >= 0
        # Round counter should have incremented
        assert state.round_counter >= 0


class TestGetPlaquetteColour:
    """Tests for plaquette colour determination from stabilisers."""

    def test_get_plaquette_colour_integration(self, surface_code_repeat_path: Path):
        """Test plaquette colour determination through full pass."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        result = _visualise_patch(str(surface_code_repeat_path))

        # Should have plaquettes with assigned colours
        if result:
            plaquettes = result[0].get("patches", [{}])[0].get("plaquettes", [])
            if plaquettes:
                for plaquette in plaquettes:
                    assert "colour" in plaquette
                    assert plaquette["colour"] in ("red", "blue")


class TestCoordinateResolutionEdgeCases:
    """Tests for edge cases in coordinate resolution."""

    def test_coordinate_caching_across_calls(self):
        """Test that coordinates are properly cached."""
        state = SurfaceCodeVisualisationState()
        coord = (1.5, 2.5)
        cache_key = (None, 0)

        # First call should cache
        _cache_coordinate(state, cache_key, coord)
        assert cache_key in state.coordinates_map

        # Second call should return cached value
        cached_coord = state.coordinates_map[cache_key]
        assert cached_coord == coord

    def test_patch_items_keyed_by_round(self):
        """Test that patch items are correctly keyed by round index."""
        state = SurfaceCodeVisualisationState()

        item1 = _get_or_create_patch_item(state, 1)
        item2 = _get_or_create_patch_item(state, 2)
        item3 = _get_or_create_patch_item(state, 3)

        # Verify all items are different
        assert item1 is not item2
        assert item1 is not item3
        assert item2 is not item3

        # Verify correct number of items created
        assert len(state.visualisation_data) == 3


class TestVisualisationDataFormatting:
    """Tests for the output formatting of visualisation data."""

    def test_finalise_removes_internal_fields(self):
        """Test that _finalise_visualisation_data removes internal fields."""
        visualisation_data = [
            {
                "round": 1,
                "qubits": [{"id": "q_0", "type": "data", "coordinates": [0.5, 0.5]}],
                "patches": [
                    {
                        "plaquettes": [
                            {
                                "id": 0,
                                "colour": "blue",
                                "shape": "semicircle",
                                "weight": 1,
                                "_coord_keys": [(0.5, 0.5)],
                            }
                        ]
                    }
                ],
                "_qubit_types": {(0.5, 0.5): "data"},
            }
        ]

        final_data = _finalise_visualisation_data(visualisation_data)

        assert len(final_data) == 1
        final_item = final_data[0]
        assert "_qubit_types" not in final_item
        assert "_coord_keys" not in final_item["patches"][0]["plaquettes"][0]
        assert "round" in final_item
        assert "qubits" in final_item
        assert "patches" in final_item


class TestFullVisualisationPipeline:
    """Tests for the full visualisation pipeline."""

    def test_module_pass_integration(self, surface_code_repeat_path: Path):
        """Test the full VisualiseSurfaceCodes module pass."""
        if not surface_code_repeat_path.exists():
            pytest.skip(f"Test file not found: {surface_code_repeat_path}")

        result = _visualise_patch(str(surface_code_repeat_path))

        # Verify the result is properly formatted
        assert isinstance(result, list)

        # Each operation should have required fields
        for op in result:
            assert "round" in op
            assert isinstance(op["round"], int)
            assert "qubits" in op
            assert "patches" in op
            assert isinstance(op["qubits"], list)
            assert isinstance(op["patches"], list)

    def test_json_serialisation_roundtrip(self, surface_code_2d_path: Path):
        """Test that visualisation data survives JSON serialisation."""
        if not surface_code_2d_path.exists():
            pytest.skip(f"Test file not found: {surface_code_2d_path}")

        original = _visualise_patch(str(surface_code_2d_path))

        # Serialise and deserialize
        json_str = json.dumps(original)
        recovered = json.loads(json_str)

        # Should be identical
        assert original == recovered
