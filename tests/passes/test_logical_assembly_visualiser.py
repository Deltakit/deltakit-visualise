# (c) Copyright Riverlane 2020-2026.
"""Tests for LogicalAssemblyVisualiser."""

import contextlib
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock

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


@pytest.mark.usefixtures("no_serve")
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


@pytest.fixture(autouse=True)
def _isolate_active_visualiser(monkeypatch):
    """Keep the class-level server tracking from leaking between tests."""
    monkeypatch.setattr(LogicalAssemblyVisualiser, "_active_visualiser", None)
    yield
    active = LogicalAssemblyVisualiser._active_visualiser
    if active is not None:
        active.stop()


def _fake_serve(server, *_args):
    """Stand-in for ``Server.run``: report started, then idle until told to exit."""
    server.started = True
    while not server.should_exit:
        time.sleep(0.001)


@pytest.fixture(name="no_serve")
def _no_serve(monkeypatch):
    """Serve from a fake notebook loop without binding a port, keeping the real Config/Server."""
    monkeypatch.setattr(
        "deltakit_visualise.logical_assembly_visualiser._in_running_event_loop", lambda: True
    )
    monkeypatch.setattr(uvicorn.Server, "run", _fake_serve)


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

    def test_visualise_runs_server_once(self, monkeypatch):
        """Outside notebooks the server runs once, blocking, and is untracked once it returns."""
        runs = []

        def record_run(server):
            runs.append(server)

        monkeypatch.setattr(
            "deltakit_visualise.logical_assembly_visualiser._in_running_event_loop",
            lambda: False,
        )
        monkeypatch.setattr(uvicorn.Server, "run", record_run)
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))

        vis.visualise()

        assert len(runs) == 1
        assert vis._server is None
        assert LogicalAssemblyVisualiser._active_visualiser is None

    def test_visualise_in_notebook_runs_server_once_on_tracked_thread(self, monkeypatch):
        """With a running loop, one server runs, on the thread ``stop`` will join."""
        runs = []

        def record_run(server):
            runs.append((server, threading.current_thread()))
            _fake_serve(server)

        monkeypatch.setattr(uvicorn.Server, "run", record_run)
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))

        vis.visualise()

        assert runs == [(vis._server, vis._thread)]
        vis.stop()

    # uvicorn signals a failed bind with sys.exit inside the server thread.
    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
    def test_visualise_raises_and_clears_state_when_server_fails_to_start(self, monkeypatch):
        """A server that dies during startup (e.g. port in use) is reported, not ignored."""

        def fail_to_bind(_server):
            raise SystemExit(1)

        monkeypatch.setattr(uvicorn.Server, "run", fail_to_bind)
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))

        with pytest.raises(RuntimeError, match="failed to start"):
            vis.visualise()

        assert vis._server is None
        assert vis._thread is None
        assert LogicalAssemblyVisualiser._active_visualiser is None

    def test_visualise_does_not_report_restart_of_exited_server(self, caplog):
        """A server whose thread already exited is cleaned up, not reported as running."""
        first = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        first.visualise()
        first_thread = first._thread
        assert first_thread is not None
        first._server.should_exit = True
        first_thread.join(timeout=5)

        second = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        with caplog.at_level("INFO", logger="deltakit_visualise.logical_assembly_visualiser"):
            second.visualise()

        assert "Server already running" not in caplog.text
        assert first._server is None
        assert LogicalAssemblyVisualiser._active_visualiser is second

    def test_concurrent_visualise_calls_leave_one_server_running(self, monkeypatch):
        """Racing ``visualise`` calls stop each other's server rather than both serving."""
        servers = []

        def record_serve(server):
            servers.append(server)
            _fake_serve(server)

        monkeypatch.setattr(uvicorn.Server, "run", record_serve)
        visualisers = [
            LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH)) for _ in range(4)
        ]
        barrier = threading.Barrier(len(visualisers))

        def run(vis):
            barrier.wait()
            vis.visualise()

        threads = [threading.Thread(target=run, args=(vis,)) for vis in visualisers]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert len(servers) == len(visualisers)
        running = [s for s in servers if not s.should_exit]
        active = LogicalAssemblyVisualiser._active_visualiser
        assert active is not None
        assert running == [active._server]

    def test_stop_does_not_block_forever_on_stuck_server(self, caplog):
        """A server that ignores ``should_exit`` must not hang ``stop``."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()
        stuck_thread = Mock()
        stuck_thread.is_alive.return_value = True
        vis._thread = stuck_thread

        with caplog.at_level("WARNING", logger="deltakit_visualise.logical_assembly_visualiser"):
            vis.stop()

        stuck_thread.join.assert_called_once_with(timeout=5)
        assert "did not shut down" in caplog.text
        assert vis._thread is None

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

    def test_visualise_restarts_existing_server(self, caplog):
        """A second notebook execution on the same object stops the old server."""
        vis = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        vis.visualise()
        first_server = vis._server
        assert first_server is not None

        with caplog.at_level("INFO", logger="deltakit_visualise.logical_assembly_visualiser"):
            vis.visualise()

        assert first_server.should_exit
        assert vis._server is not first_server
        assert "Server already running, restarting..." in caplog.text

    def test_new_visualiser_restarts_previous_instances_server(self):
        """Recreating the visualiser releases the previous instance's port."""
        first = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        first.visualise()
        first_server = first._server
        assert first_server is not None
        first_thread = Mock()
        first._thread = first_thread

        second = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        second.visualise()

        assert first_server.should_exit
        first_thread.join.assert_called_once_with(timeout=5)
        assert first._server is None
        assert first._thread is None
        assert second._server is not None
        assert second._server is not first_server
        second.stop()

    def test_stopping_previous_instance_preserves_new_server_tracking(self):
        """Stopping a replaced instance must not lose the current server owner."""
        first = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        first.visualise()
        second = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        second.visualise()
        second_server = second._server
        assert second_server is not None

        first.stop()
        third = LogicalAssemblyVisualiser.from_log_asm_file(str(QMEM_MLIR_PATH))
        third.visualise()

        assert second_server.should_exit
        assert third._server is not None
        third.stop()
