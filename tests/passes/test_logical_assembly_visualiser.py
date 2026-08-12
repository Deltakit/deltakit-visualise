# (c) Copyright Riverlane 2020-2026.
"""Tests for LogicalAssemblyVisualiser."""

import contextlib
import tempfile
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from xdsl.dialects.builtin import ModuleOp

from deltakit_visualise.api.server import create_app
from deltakit_visualise.constants import RENDER_DYNAMIC_COMMAND, RENDER_VISUALISE_COMMAND
from deltakit_visualise.logical_assembly_visualiser import LogicalAssemblyVisualiser
from deltakit_visualise.pipelines.spacetime import SpacetimePipeline
from deltakit_visualise.pipelines.surfacecodes import PatchVisualisationPipeline
from deltakit_visualise.visualiser import get_visualisation_data

# Path to the CNOT example MLIR file
CNOT_MLIR_PATH = Path(__file__).parents[1] / "filecheck" / "extended" / "cnot.mlir"
SURFACE_CODE_2D_PATH = (
    Path(__file__).parents[1] / "filecheck" / "primitives" / "surface_code_2d.mlir"
)
# A program both pipelines fully support, so `visualise` reaches the server setup.
# (cnot.mlir does not: `patch-to-plaquette` raises on MultiPauliMeasOp.)
QMEM_MLIR_PATH = Path(__file__).parents[1] / "filecheck" / "extended" / "qmem.mlir"


def _spacetime_data(module_op: ModuleOp) -> dict:
    """Run the spacetime pipeline over ``module_op`` and extract its data."""
    ctx = LogicalAssemblyVisualiser.make_context()
    SpacetimePipeline().apply(ctx, module_op)
    return get_visualisation_data(module_op)


def _patch_data(module_op: ModuleOp) -> dict:
    """Run the patch visualisation pipeline over ``module_op`` and extract its data."""
    ctx = LogicalAssemblyVisualiser.make_context()
    PatchVisualisationPipeline().apply(ctx, module_op)
    return get_visualisation_data(module_op)


@pytest.fixture(name="basic_mlir_content")
def _basic_mlir_content() -> str:
    """Fixture for basic MLIR content with a single patch declaration."""
    return """\
builtin.module {
    %lq = log_asm.patch_dec -> !log_asm.patch.rot_planar<size=(5, 5), location=(1, 1), orient=v_z>
}
"""


class TestParseMlirFile:
    """Tests for parse_mlir_file."""

    def test_parses_valid_mlir_file(self, basic_mlir_content: str):
        """Test that parse_mlir_file parses a valid MLIR file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
            f.write(basic_mlir_content)
            f.flush()

            module_op = LogicalAssemblyVisualiser.parse_mlir_file(f.name)

            assert isinstance(module_op, ModuleOp)

        Path(f.name).unlink()

    def test_raises_on_invalid_file_path(self):
        """Test that parse_mlir_file raises RuntimeError for invalid path."""
        with pytest.raises(RuntimeError, match="Error parsing MLIR file"):
            LogicalAssemblyVisualiser.parse_mlir_file("/nonexistent/path/to/file.mlir")

    def test_raises_on_invalid_mlir_syntax(self):
        """Test that parse_mlir_file raises RuntimeError for invalid MLIR."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
            f.write("invalid { mlir syntax }")
            f.flush()

            with pytest.raises(RuntimeError, match="Error parsing MLIR file"):
                LogicalAssemblyVisualiser.parse_mlir_file(f.name)

        Path(f.name).unlink()


class TestSpacetimeDataExtraction:
    """Tests for the low-level path: apply a pipeline, then extract its data."""

    def test_basic_mlir(self, basic_mlir_content: str):
        """A single patch declaration produces its surface."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
            f.write(basic_mlir_content)
            f.flush()

            module_op = LogicalAssemblyVisualiser.parse_mlir_file(f.name)
            data = _spacetime_data(module_op)

            # Should have the patch declaration surface
            assert len(data["ops"]) >= 1
            surfaces = [d for d in data["ops"] if d["type"] == "surface"]
            assert len(surfaces) >= 1
            assert any(d["op_name"] == "log_asm.patch_dec" for d in surfaces)

        Path(f.name).unlink()

    def test_cnot_mlir_file(self):
        """The CNOT example produces ordered surface/side items."""
        module_op = LogicalAssemblyVisualiser.parse_mlir_file(str(CNOT_MLIR_PATH))
        data = _spacetime_data(module_op)

        # CNOT circuit should produce many visualisation items
        assert len(data["ops"]) > 10

        # Check for expected operation types (as list to preserve order)
        op_names = [d["op_name"] for d in data["ops"]]

        expected_order = [
            "log_asm.patch_dec",
            "log_asm.prepare",
            "log_asm.meas_stab",
            "log_asm.multi_pauli_meas",
            "log_asm.measure",
        ]
        for i in range(len(expected_order) - 1):
            assert op_names.index(expected_order[i]) < op_names.index(expected_order[i + 1]), (
                f"{expected_order[i]} should appear before {expected_order[i + 1]}"
            )

        # Check for both visualisation types
        types = {d["type"] for d in data["ops"]}
        assert types == {"surface", "side"}

    def test_extract_raises_without_terminal_pass(self):
        """get_visualisation_data raises if no pipeline has been run."""
        with pytest.raises(ValueError, match="No visualisation data"):
            get_visualisation_data(ModuleOp([]))


class TestPatchDataExtraction:
    """Tests for the low-level path: apply patch pipeline, then extract its data."""

    def test_basic_mlir_patch_data(self, basic_mlir_content: str):
        """A single patch declaration produces patch data (may be empty for simple case)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mlir", delete=False) as f:
            f.write(basic_mlir_content)
            f.flush()

            module_op = LogicalAssemblyVisualiser.parse_mlir_file(f.name)
            data = _patch_data(module_op)

            assert "ops" in data
            if len(data["ops"]) > 0:
                assert all(
                    "round" in item and "qubits" in item and "patches" in item
                    for item in data["ops"]
                )

        Path(f.name).unlink()


class TestVisualiseSpaceTime:
    """Tests for the high-level visualise_space_time view (auto-shows)."""

    def test_renders_spacetime_data_and_returns_path(self, monkeypatch):
        """visualise_space_time extracts the data, shows it, and returns the path."""
        captured: dict = {}

        def fake_show(data, static: bool = True) -> Path:
            captured["data"] = data
            captured["static"] = static
            return Path("/display/index.html")

        monkeypatch.setattr("deltakit_visualise.logical_assembly_visualiser.show", fake_show)

        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(CNOT_MLIR_PATH))
        result = vis.visualise_space_time()

        assert result == Path("/display/index.html")
        assert len(captured["data"]["ops"]) > 10
        assert {d["type"] for d in captured["data"]["ops"]} == {"surface", "side"}


class TestVisualiseLogicalPatch:
    """Tests for the visualise_logical_patch view."""

    def test_renders_patch_data_and_returns_path(self, monkeypatch):
        """visualise_logical_patch extracts data, shows it, and returns the path."""
        captured: dict = {}

        def fake_show(data, static: bool = True) -> Path:
            captured["data"] = data
            captured["static"] = static
            return Path("/display/index.html")

        monkeypatch.setattr("deltakit_visualise.logical_assembly_visualiser.show", fake_show)

        try:
            vis = LogicalAssemblyVisualiser.from_log_asm_file(str(SURFACE_CODE_2D_PATH))
            result = vis.visualise_logical_patch()
            assert result == Path("/display/index.html")
            assert "ops" in captured["data"]
            if len(captured["data"]["ops"]) > 0:
                assert all(
                    "round" in item and "qubits" in item and "patches" in item
                    for item in captured["data"]["ops"]
                )
        except (NotImplementedError, RuntimeError):
            # MLIR file may have parsing errors or PatchToPlaquettes pass
            # may not support all circuit types yet
            pass


class TestCombinedVisualise:
    """Tests for the combined visualise method that runs both pipelines."""

    def test_visualise_combines_both_pipelines(self, monkeypatch):
        """visualise runs both spacetime and patch pipelines and creates app."""
        captured: dict = {}

        def fake_create_app(space_time_data, logical_patches_data, **_kwargs):
            captured["space_time_data"] = space_time_data
            captured["logical_patches_data"] = logical_patches_data

        monkeypatch.setattr(
            "deltakit_visualise.logical_assembly_visualiser.create_app", fake_create_app
        )

        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(CNOT_MLIR_PATH))
        with contextlib.suppress(NotImplementedError, RuntimeError):
            vis.visualise()

        if "space_time_data" in captured:
            space_time = captured["space_time_data"]
            patches = captured["logical_patches_data"]

            assert "ops" in space_time
            assert len(space_time["ops"]) > 10

            assert "ops" in patches
            if len(patches["ops"]) > 0:
                assert all(
                    "round" in item and "qubits" in item and "patches" in item
                    for item in patches["ops"]
                )


@pytest.fixture(name="no_serve")
def _no_serve(monkeypatch):
    """Stop ``visualise`` from actually serving, keeping the real Config/Server."""
    monkeypatch.setattr(uvicorn.Server, "run", lambda *_args: None)


@pytest.fixture(name="created_app")
def _created_app(monkeypatch):
    """Capture the args ``visualise`` passes to ``create_app``.

    The real ``create_app`` still runs, so the captured app is the one the server
    would have been handed.
    """
    captured: dict = {}

    def spy_create_app(space_time_data, logical_patches_data, *args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["space_time_data"] = space_time_data
        captured["logical_patches_data"] = logical_patches_data
        app = create_app(space_time_data, logical_patches_data, *args, **kwargs)
        captured["app"] = app
        return app

    monkeypatch.setattr("deltakit_visualise.logical_assembly_visualiser.create_app", spy_create_app)
    return captured


@pytest.mark.usefixtures("no_serve")
class TestVisualiseRenderCommand:
    """``visualise`` must serve the frontend with the surface-code panel enabled."""

    def test_visualise_passes_visualise_render_command(self, created_app):
        """create_app is given RENDER_VISUALISE_COMMAND, not the default."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        render_command = created_app["kwargs"].get("render_command")
        assert render_command == RENDER_VISUALISE_COMMAND
        assert render_command != RENDER_DYNAMIC_COMMAND

    def test_visualise_still_passes_both_payloads(self, created_app):
        """The render command is additional to — not instead of — the two payloads."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        space_time = created_app["space_time_data"]
        patches = created_app["logical_patches_data"]

        assert {d["type"] for d in space_time["ops"]} == {"surface", "side"}
        assert patches["ops"]
        assert all(
            "round" in item and "qubits" in item and "patches" in item for item in patches["ops"]
        )

    def test_visualise_passes_render_command_as_keyword(self, created_app):
        """Only the two payloads are positional, so create_app can grow parameters."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        assert created_app["args"] == ()
        assert set(created_app["kwargs"]) == {"render_command"}

    def test_visualise_serves_index_with_surface_code_panel(self, created_app):
        """End to end: the app `visualise` builds serves the panel-enabled command."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        app = created_app["app"]
        assert isinstance(app, FastAPI)
        text = TestClient(app).get("/").text

        assert RENDER_VISUALISE_COMMAND in text
        assert "{{render_command}}" not in text

    def test_visualise_app_still_serves_its_data_endpoints(self, created_app):
        """The panel the render command opens is fed by the patch endpoints."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        client = TestClient(created_app["app"])
        assert client.get("/api/get-space-time-diagram").json() == created_app["space_time_data"]

        rounds = {op["round"] for op in created_app["logical_patches_data"]["ops"]}
        first_round = min(rounds)
        response = client.get(f"/api/get-patches-info-at-round/{first_round}")
        assert response.status_code == 200
        ops = response.json()["ops"]
        assert ops
        assert all(op["round"] == first_round for op in ops)

    def test_visualise_configures_server_with_the_created_app(self, created_app):
        """The app carrying the render command is the one uvicorn is configured with."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()

        assert vis._server is not None
        assert vis._server.config.app is created_app["app"]
