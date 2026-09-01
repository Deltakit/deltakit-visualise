# (c) Copyright Riverlane 2020-2026.
"""Tests for show()'s static-vs-server dispatch and error handling."""

# pylint: disable=redefined-outer-name

from pathlib import Path
from unittest import mock

import pytest

from deltakit_visualise import visualiser
from deltakit_visualise.constants import SPACE_TIME
from deltakit_visualise.utils import notebook as notebook_utils


@pytest.fixture
def spacetime_data() -> dict:
    """A minimal payload that show() recognises as the 3D spacetime view."""
    return {"type": SPACE_TIME, "ops": [{"type": "surface"}, {"type": "side"}]}


def test_show_static_opens_file_without_starting_server(spacetime_data):
    """static=True (default) renders and opens the file, never touching the server."""
    with (
        mock.patch.object(visualiser, "prepare_html") as prepare,
        mock.patch.object(visualiser, "static_display") as static,
        mock.patch.object(visualiser, "start_server") as server,
    ):
        result = visualiser.show(spacetime_data)

    prepare.assert_called_once_with(spacetime_data)
    static.assert_called_once_with()
    server.assert_not_called()
    assert isinstance(result, Path)


def test_show_server_starts_http_server(spacetime_data):
    """static=False starts the blocking HTTP server instead of a file open."""
    with (
        mock.patch.object(visualiser, "prepare_html"),
        mock.patch.object(visualiser, "static_display") as static,
        mock.patch.object(visualiser, "start_server") as server,
    ):
        visualiser.show(spacetime_data, static=False)

    static.assert_not_called()
    server.assert_called_once_with()


def test_show_server_swallows_keyboard_interrupt(spacetime_data):
    """Ctrl-C out of the server is handled gracefully, not propagated."""
    with (
        mock.patch.object(visualiser, "prepare_html"),
        mock.patch.object(visualiser, "start_server", side_effect=KeyboardInterrupt),
    ):
        # Does not raise.
        visualiser.show(spacetime_data, static=False)


def test_show_server_reraises_unexpected_errors(spacetime_data):
    """A genuine server failure is logged and re-raised."""
    with (
        mock.patch.object(visualiser, "prepare_html"),
        mock.patch.object(visualiser, "start_server", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        visualiser.show(spacetime_data, static=False)


def test_show_rejects_unrecognised_view():
    """Data that isn't the spacetime view raises NotImplementedError."""
    with (
        mock.patch.object(visualiser, "prepare_html") as prepare,
        mock.patch.object(visualiser, "static_display") as static,
        pytest.raises(NotImplementedError),
    ):
        visualiser.show({"type": "unknown", "ops": [{"type": "patch"}]})

    prepare.assert_not_called()
    static.assert_not_called()


def test_add_cell_html_to_notebook_embeds_html_and_displays(tmp_path, monkeypatch):
    """Notebook helper embeds blob iframe and shows ipywidgets button for opening."""
    display_dir = tmp_path / "display"
    display_dir.mkdir()
    (display_dir / "index.html").write_text("<html><body>demo</body></html>", encoding="utf-8")
    monkeypatch.setattr(notebook_utils, "DISPLAY_DIR", display_dir)

    fake_display = mock.Mock()
    fake_html = mock.Mock(side_effect=lambda value: value)
    fake_ipython_display = type(
        "FakeIPythonDisplay",
        (),
        {"display": fake_display, "HTML": fake_html},
    )

    fake_button = mock.Mock()
    fake_hbox = mock.Mock()
    fake_layout = mock.Mock(return_value=mock.Mock())
    fake_widgets = type(
        "FakeWidgets",
        (),
        {
            "Button": mock.Mock(return_value=fake_button),
            "HBox": mock.Mock(return_value=fake_hbox),
            "Layout": fake_layout,
        },
    )

    def _import_side_effect(name: str) -> object:
        if name == "IPython.display":
            return fake_ipython_display
        if name == "ipywidgets":
            return fake_widgets
        raise ImportError(name)

    with (
        mock.patch.object(notebook_utils, "import_module", side_effect=_import_side_effect),
        mock.patch.object(notebook_utils, "prepare_html") as prepare,
    ):
        notebook_utils.add_cell_html_to_notebook({"type": SPACE_TIME, "ops": []})
        prepare.assert_called_once_with({"type": SPACE_TIME, "ops": []})

    displayed_html = fake_html.call_args.args[0]
    assert "<script>" in displayed_html
    assert "atob(" in displayed_html
    assert "sandbox" in displayed_html

    # Button was created and wired up
    fake_widgets.Button.assert_called_once()
    assert "Open link" in fake_widgets.Button.call_args.kwargs.get("description", "")
    fake_button.on_click.assert_called_once()

    # HBox wrapping the button was displayed
    fake_widgets.HBox.assert_called_once()
    assert fake_display.call_count == 2  # iframe HTML + button HBox


def test_add_cell_html_to_notebook_imports_ipython_lazily(tmp_path, monkeypatch):
    """No top-level imports are needed; helper loads IPython.display and ipywidgets lazily."""
    display_dir = tmp_path / "display"
    display_dir.mkdir()
    (display_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    monkeypatch.setattr(notebook_utils, "DISPLAY_DIR", display_dir)

    fake_button = mock.Mock()
    fake_widgets = type(
        "FakeWidgets",
        (),
        {
            "Button": mock.Mock(return_value=fake_button),
            "HBox": mock.Mock(return_value=mock.Mock()),
            "Layout": mock.Mock(return_value=mock.Mock()),
        },
    )
    fake_ipython_display = type(
        "FakeIPythonDisplay",
        (),
        {"display": mock.Mock(), "HTML": mock.Mock()},
    )

    def _import_side_effect(name: str) -> object:
        if name == "IPython.display":
            return fake_ipython_display
        if name == "ipywidgets":
            return fake_widgets
        raise ImportError(name)

    with (
        mock.patch.object(
            notebook_utils, "import_module", side_effect=_import_side_effect
        ) as import_mod,
        mock.patch.object(notebook_utils, "prepare_html"),
    ):
        notebook_utils.add_cell_html_to_notebook({"type": SPACE_TIME, "ops": []})

    imported_names = [call.args[0] for call in import_mod.call_args_list]
    assert "IPython.display" in imported_names
    assert "ipywidgets" in imported_names
