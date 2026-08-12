# (c) Copyright Riverlane 2025-2026.
"""Tests for the FastAPI server in deltakit_visualise/api/server.py."""

import pytest
from fastapi.testclient import TestClient

from deltakit_visualise.api import server
from deltakit_visualise.api.server import (
    DELTAKIT_VIS_SCRIPT,
    create_app,
)
from deltakit_visualise.constants import (
    ALLOWED_ORIGINS,
    FETCH_DATA_SCRIPT,
    RENDER_DATA_COMMAND,
    RENDER_DYNAMIC_COMMAND,
    RENDER_VISUALISE_COMMAND,
)


@pytest.fixture
def sample_space_time_data() -> dict:
    """Sample space-time diagram data."""
    return {
        "type": "space_time_diagram",
        "rounds": [
            {"round": 0, "ops": ["op1", "op2"]},
            {"round": 1, "ops": ["op3"]},
        ],
    }


@pytest.fixture
def sample_logical_patches_data() -> dict:
    """Sample logical patches data with ops keyed by round for filtering tests."""
    return {
        "type": "logical_patches",
        "ops": [
            {"round": 0, "patch_id": "p0", "op": "prepare"},
            {"round": 0, "patch_id": "p1", "op": "measure"},
            {"round": 1, "patch_id": "p0", "op": "meas_stab"},
            {"round": 2, "patch_id": "p1", "op": "prepare"},
        ],
    }


@pytest.fixture
def app(sample_space_time_data, sample_logical_patches_data):
    """FastAPI app instance."""
    return create_app(sample_space_time_data, sample_logical_patches_data)


@pytest.fixture
def client(app):
    """TestClient for the FastAPI app."""
    return TestClient(app)


def test_create_app_initialises_with_space_time_data(
    sample_space_time_data, sample_logical_patches_data
):
    """App is created with space_time_data stored in state."""
    app = create_app(sample_space_time_data, sample_logical_patches_data)
    assert app.state.space_time_data == sample_space_time_data


def test_create_app_has_correct_title(sample_space_time_data, sample_logical_patches_data):
    """App is created with the correct title."""
    app = create_app(sample_space_time_data, sample_logical_patches_data)
    assert app.title == "deltakit-visualise"


def test_create_app_has_cors_middleware(sample_space_time_data, sample_logical_patches_data):
    """App has CORS middleware configured."""
    app = create_app(sample_space_time_data, sample_logical_patches_data)
    middleware_types = [str(m.cls) for m in app.user_middleware]
    assert any("CORSMiddleware" in str(m) for m in middleware_types)


def test_serve_index_returns_html_response(client):
    """The / endpoint returns HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_serve_index_replaces_render_command(client, tmp_path, monkeypatch):
    """The / endpoint replaces {{render_command}} placeholder."""
    index_content = "<html><body>{{render_command}}</body></html>"
    mock_index = tmp_path / "index.html"
    mock_index.write_text(index_content)

    monkeypatch.setattr(server, "INDEX_HTML", mock_index)

    response = client.get("/")
    assert RENDER_DYNAMIC_COMMAND in response.text
    assert "{{render_command}}" not in response.text


def test_serve_index_replaces_deltakit_vis_script(client, tmp_path, monkeypatch):
    """The / endpoint replaces {{deltakit_vis_script}} placeholder."""
    index_content = "<html><body>{{deltakit_vis_script}}</body></html>"
    mock_index = tmp_path / "index.html"
    mock_index.write_text(index_content)

    monkeypatch.setattr(server, "INDEX_HTML", mock_index)

    response = client.get("/")
    assert DELTAKIT_VIS_SCRIPT in response.text
    assert "{{deltakit_vis_script}}" not in response.text


def test_serve_index_replaces_both_placeholders(client, tmp_path, monkeypatch):
    """The / endpoint replaces both placeholders correctly."""
    index_content = "<html><body>{{deltakit_vis_script}}{{render_command}}</body></html>"
    mock_index = tmp_path / "index.html"
    mock_index.write_text(index_content)

    monkeypatch.setattr(server, "INDEX_HTML", mock_index)

    response = client.get("/")
    assert DELTAKIT_VIS_SCRIPT in response.text
    assert RENDER_DYNAMIC_COMMAND in response.text
    assert "{{render_command}}" not in response.text
    assert "{{deltakit_vis_script}}" not in response.text


def test_serve_deltakit_vis_js_returns_file_response(client, tmp_path, monkeypatch):
    """The /deltakit-visualise.umd.js endpoint returns a file response."""
    umd_content = "console.log('deltakit-vis library');"
    umd_dir = tmp_path / ".js" / "dist"
    umd_dir.mkdir(parents=True)
    umd_file = umd_dir / "deltakit-visualise.umd.js"
    umd_file.write_text(umd_content)

    monkeypatch.setattr(server, "BASE_DIR", tmp_path)

    response = client.get("/deltakit-visualise.umd.js")
    assert response.status_code == 200


def test_serve_deltakit_vis_js_returns_correct_content_type(client, tmp_path, monkeypatch):
    """The /deltakit-visualise.umd.js endpoint returns correct content type."""
    umd_content = "console.log('deltakit-vis library');"
    umd_dir = tmp_path / ".js" / "dist"
    umd_dir.mkdir(parents=True)
    umd_file = umd_dir / "deltakit-visualise.umd.js"
    umd_file.write_text(umd_content)

    monkeypatch.setattr(server, "BASE_DIR", tmp_path)

    response = client.get("/deltakit-visualise.umd.js")
    assert "javascript" in response.headers["content-type"]


def test_get_space_time_diagram_returns_data(client, sample_space_time_data):
    """The endpoint returns the space-time data."""
    response = client.get("/api/get-space-time-diagram")
    assert response.status_code == 200
    assert response.json() == sample_space_time_data


def test_get_space_time_diagram_returns_json(client):
    """The endpoint returns JSON format."""
    response = client.get("/api/get-space-time-diagram")
    assert response.headers["content-type"] == "application/json"


def test_get_space_time_diagram_with_empty_data():
    """The endpoint works with empty space-time data."""
    empty_data = {}
    empty_patches_data = {}
    app = create_app(empty_data, empty_patches_data)
    client = TestClient(app)

    response = client.get("/api/get-space-time-diagram")
    assert response.status_code == 200
    assert response.json() == empty_data


def test_get_space_time_diagram_with_complex_data():
    """The endpoint returns complex nested data correctly."""
    complex_data = {
        "type": "space_time_diagram",
        "metadata": {"version": "1.0"},
        "rounds": [
            {
                "round": 0,
                "ops": ["op1", "op2"],
                "details": {"duration": 10},
            },
            {
                "round": 1,
                "ops": ["op3"],
                "details": {"duration": 5},
            },
        ],
    }
    empty_patches_data = {}
    app = create_app(complex_data, empty_patches_data)
    client = TestClient(app)

    response = client.get("/api/get-space-time-diagram")
    assert response.status_code == 200
    assert response.json() == complex_data


def test_get_patches_info_at_round_returns_data(client):
    """The endpoint returns patches info for a specific round."""
    response = client.get("/api/get-patches-info-at-round/0")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_get_patches_info_at_round_returns_json(client):
    """The endpoint returns JSON format."""
    response = client.get("/api/get-patches-info-at-round/0")
    assert response.headers["content-type"] == "application/json"


def test_get_patches_info_at_round_with_different_rounds(client):
    """The endpoint returns data for different rounds."""
    for round_no in [0, 1, 5, 10]:
        response = client.get(f"/api/get-patches-info-at-round/{round_no}")
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert "ops" in data


def test_get_patches_info_at_round_invalid_round(client):
    """The endpoint handles invalid round numbers gracefully."""
    response = client.get("/api/get-patches-info-at-round/invalid")
    assert response.status_code == 422


def test_cors_allows_specified_origins(client):
    """CORS headers are set for allowed origins."""

    if ALLOWED_ORIGINS:
        origin = ALLOWED_ORIGINS[0]
        response = client.get("/", headers={"Origin": origin})
        assert response.status_code == 200


def test_cors_middleware_configured(app):
    """The app has CORS middleware configured."""
    middleware_types = [str(m.cls) for m in app.user_middleware]
    assert any("CORSMiddleware" in str(m) for m in middleware_types)


def test_create_app_initialises_with_logical_patches_data(
    sample_space_time_data, sample_logical_patches_data
):
    """App is created with logical_patches_data stored in state."""
    app = create_app(sample_space_time_data, sample_logical_patches_data)
    assert app.state.logical_patches_data == sample_logical_patches_data


def test_get_patches_info_at_round_filters_by_round(client):
    """Only ops belonging to the requested round are returned."""
    response = client.get("/api/get-patches-info-at-round/0")
    assert response.status_code == 200
    data = response.json()
    assert all(op["round"] == 0 for op in data["ops"])
    assert len(data["ops"]) == 2


def test_get_patches_info_at_round_returns_correct_ops_for_round_1(client):
    """Round 1 returns only the single op assigned to that round."""
    response = client.get("/api/get-patches-info-at-round/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["ops"]) == 1
    assert data["ops"][0]["round"] == 1


def test_get_patches_info_at_round_preserves_type_field(client):
    """The `type` field from logical_patches_data is preserved in the response."""
    response = client.get("/api/get-patches-info-at-round/0")
    assert response.status_code == 200
    assert response.json()["type"] == "logical_patches"


def test_get_patches_info_at_round_nonexistent_round_returns_empty_ops(client):
    """A round with no ops returns an empty ops list."""
    response = client.get("/api/get-patches-info-at-round/99")
    assert response.status_code == 200
    data = response.json()
    assert data["ops"] == []


def test_get_patches_info_at_round_with_empty_patches_data():
    """The endpoint works when logical_patches_data has no ops key."""
    app = create_app({}, {})
    client = TestClient(app)
    response = client.get("/api/get-patches-info-at-round/0")
    assert response.status_code == 200
    data = response.json()
    assert data["ops"] == []
    assert data["type"] == ""


@pytest.fixture
def range_client(sample_space_time_data, sample_logical_patches_data):
    """TestClient wired with multi-round patch data."""
    app = create_app(sample_space_time_data, sample_logical_patches_data)
    return TestClient(app)


def test_get_patches_info_at_rounds_returns_200(range_client):
    """The range endpoint returns HTTP 200."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...2")
    assert response.status_code == 200


def test_get_patches_info_at_rounds_returns_json(range_client):
    """The range endpoint returns JSON."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...2")
    assert response.headers["content-type"] == "application/json"


def test_get_patches_info_at_rounds_response_has_type_and_ops(range_client):
    """The response contains `type` and `ops` keys."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...2")
    data = response.json()
    assert "type" in data
    assert "ops" in data


def test_get_patches_info_at_rounds_preserves_type_field(range_client):
    """The `type` field from logical_patches_data is preserved."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...2")
    assert response.json()["type"] == "logical_patches"


def test_get_patches_info_at_rounds_inclusive_bounds(range_client):
    """Start and end rounds are both included in the result."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...2")
    data = response.json()
    rounds_returned = {op["round"] for op in data["ops"]}
    assert 0 in rounds_returned
    assert 2 in rounds_returned


def test_get_patches_info_at_rounds_only_ops_in_range_returned(range_client):
    """Only ops whose round falls within [start, end] are returned."""
    response = range_client.get("/api/get-patches-info-at-rounds/1...2")
    data = response.json()
    assert all(1 <= op["round"] <= 2 for op in data["ops"])
    assert len(data["ops"]) == 2  # rounds 1 and 2 each have one op


def test_get_patches_info_at_rounds_single_round_range(range_client):
    """start == end selects exactly one round."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...0")
    data = response.json()
    assert all(op["round"] == 0 for op in data["ops"])
    assert len(data["ops"]) == 2


def test_get_patches_info_at_rounds_no_ops_in_range(range_client):
    """A range with no matching ops returns an empty ops list."""
    response = range_client.get("/api/get-patches-info-at-rounds/10...20")
    assert response.status_code == 200
    assert response.json()["ops"] == []


def test_get_patches_info_at_rounds_invalid_start(range_client):
    """Non-integer start parameter returns 422."""
    response = range_client.get("/api/get-patches-info-at-rounds/abc...2")
    assert response.status_code == 422


def test_get_patches_info_at_rounds_invalid_end(range_client):
    """Non-integer end parameter returns 422."""
    response = range_client.get("/api/get-patches-info-at-rounds/0...abc")
    assert response.status_code == 422


def test_get_patches_info_at_rounds_with_empty_patches_data():
    """The range endpoint works when logical_patches_data is empty."""
    app = create_app({}, {})
    client = TestClient(app)
    response = client.get("/api/get-patches-info-at-rounds/0...5")
    assert response.status_code == 200
    data = response.json()
    assert data["ops"] == []
    assert data["type"] == ""


@pytest.fixture
def index_template(tmp_path, monkeypatch):
    """Point INDEX_HTML at a tmp template; returns a writer for its content."""

    def _write(content: str) -> None:
        mock_index = tmp_path / "index.html"
        mock_index.write_text(content)
        monkeypatch.setattr(server, "INDEX_HTML", mock_index)

    return _write


def _index_text(render_command: str | None, index_template) -> str:
    """Serve `/` from a `{{render_command}}`-only template and return the HTML."""
    index_template("<html><body>{{render_command}}</body></html>")
    if render_command is None:
        app = create_app({}, {})
    else:
        app = create_app({}, {}, render_command=render_command)
    return TestClient(app).get("/").text


def test_render_command_defaults_to_dynamic_when_omitted(index_template):
    """Callers that omit render_command still get the dynamic render call."""
    assert _index_text(None, index_template).strip() == (
        f"<html><body>{RENDER_DYNAMIC_COMMAND}</body></html>"
    )


def test_render_command_override_is_injected(index_template):
    """An explicit render_command replaces the placeholder verbatim."""
    html = _index_text(RENDER_VISUALISE_COMMAND, index_template)
    assert RENDER_VISUALISE_COMMAND in html
    assert "{{render_command}}" not in html


def test_render_command_override_suppresses_the_default(index_template):
    """Overriding render_command means the default is not injected as well."""
    html = _index_text(RENDER_VISUALISE_COMMAND, index_template)
    assert RENDER_DYNAMIC_COMMAND not in html


def test_render_command_accepts_any_command_string(index_template):
    """create_app does not restrict render_command to the dynamic commands."""
    html = _index_text(RENDER_DATA_COMMAND, index_template)
    assert RENDER_DATA_COMMAND in html
    assert "{{render_command}}" not in html


def test_render_command_may_be_passed_positionally(index_template):
    """render_command is the third positional parameter of create_app."""
    index_template("<html><body>{{render_command}}</body></html>")
    app = create_app({}, {}, RENDER_VISUALISE_COMMAND)
    assert RENDER_VISUALISE_COMMAND in TestClient(app).get("/").text


def test_render_command_replaces_every_placeholder_occurrence(index_template):
    """A template repeating the placeholder gets the command in each position."""
    index_template("{{render_command}}|{{render_command}}")
    app = create_app({}, {}, render_command=RENDER_VISUALISE_COMMAND)
    text = TestClient(app).get("/").text
    assert text == f"{RENDER_VISUALISE_COMMAND}|{RENDER_VISUALISE_COMMAND}"


def test_render_command_override_leaves_other_placeholders_replaced(index_template):
    """Overriding render_command does not disturb the other substitutions."""
    index_template(
        "<html><body>{{deltakit_vis_script}}"
        "<script>{{fetch_data_script}}{{render_command}}</script></body></html>"
    )
    app = create_app({}, {}, render_command=RENDER_VISUALISE_COMMAND)
    text = TestClient(app).get("/").text

    assert DELTAKIT_VIS_SCRIPT in text
    assert FETCH_DATA_SCRIPT in text
    assert RENDER_VISUALISE_COMMAND in text
    assert "{{" not in text


def test_render_command_is_per_app(index_template):
    """Two apps with different render commands do not affect one another."""
    index_template("{{render_command}}")
    default_client = TestClient(create_app({}, {}))
    override_client = TestClient(create_app({}, {}, render_command=RENDER_VISUALISE_COMMAND))

    assert default_client.get("/").text == RENDER_DYNAMIC_COMMAND
    assert override_client.get("/").text == RENDER_VISUALISE_COMMAND
    # Re-request the default app to confirm the override did not leak into it.
    assert default_client.get("/").text == RENDER_DYNAMIC_COMMAND


def test_render_command_is_stable_across_requests(index_template):
    """The override is applied on every request, not just the first."""
    index_template("{{render_command}}")
    client = TestClient(create_app({}, {}, render_command=RENDER_VISUALISE_COMMAND))

    assert [client.get("/").text for _ in range(3)] == [RENDER_VISUALISE_COMMAND] * 3


def test_bundled_index_renders_override(sample_space_time_data):
    """The real bundled index.html carries the override through, unplaceheld."""
    app = create_app(sample_space_time_data, {}, render_command=RENDER_VISUALISE_COMMAND)
    text = TestClient(app).get("/").text

    assert RENDER_VISUALISE_COMMAND in text
    assert "{{render_command}}" not in text


def test_render_visualise_command_enables_surface_code_panel():
    """The visualise command is a renderDynamic call opting into the patch panel."""
    assert RENDER_VISUALISE_COMMAND.startswith("deltakit.renderDynamic(")
    assert "showSurfaceCodePanel: true" in RENDER_VISUALISE_COMMAND
    assert RENDER_VISUALISE_COMMAND != RENDER_DYNAMIC_COMMAND
