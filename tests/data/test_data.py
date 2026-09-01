# (c) Copyright Riverlane 2020-2026.
import tempfile
from pathlib import Path

import pytest

from deltakit_visualise.utils import data as data_utils


@pytest.mark.parametrize(
    ("input_data", "expected"),
    [
        ("var x = 1;", "<script>\n        var x = 1;\n    </script>\n    "),
        (
            {"foo": "bar"},
            '<script>\n        data = {\n  "foo": "bar"\n}\n    </script>\n    ',
        ),
    ],
)
def test_format_data(input_data, expected):
    """Test format_data for both string and dict input."""
    result = data_utils._format_data(input_data)
    assert result.strip().replace(" ", "") == expected.strip().replace(" ", "")


def test_prepare_html_replaces_data_script(prepare_html_dirs):
    """Test prepare_html replaces existing data script in index.html."""
    dirs = prepare_html_dirs
    static_index = dirs.assets_dir / "index.html"
    static_index.write_text("""
<html><body><script>data = {\n  "foo": "bar"\n}</script>
<script>const deltaKit = new Deltakit('app');</script></body></html>
""")

    data_utils.prepare_html({"baz": 42})

    display_index = dirs.display_dir / "index.html"
    out = display_index.read_text()
    assert "data = {" in out
    assert '"baz": 42' in out
    assert display_index.exists()


def test_prepare_html_inserts_after_library(prepare_html_dirs):
    """Test prepare_html inserts data after library script if no data script exists."""
    dirs = prepare_html_dirs
    static_index = dirs.assets_dir / "index.html"
    static_index.write_text("""
<html><body>{{deltakit_vis_script}}</body></html>
""")

    data_utils.prepare_html({"foo": "bar"})

    display_index = dirs.display_dir / "index.html"
    out = display_index.read_text()
    assert "data = {" in out
    assert '"foo": "bar"' in out
    assert static_index.exists()


def test_prepare_html_inlines_lib_file(prepare_html_dirs):
    """Test prepare_html inlines the library JS so the HTML is self-contained."""
    dirs = prepare_html_dirs
    static_index = dirs.assets_dir / "index.html"
    static_index.write_text("""
<html><body>{{deltakit_vis_script}}</body></html>
""")

    data_utils.prepare_html({"foo": "bar"})

    display_index = dirs.display_dir / "index.html"
    out = display_index.read_text()
    # The library JS is inlined (its content present), not referenced by src.
    assert dirs.umd_js_file.read_text() in out
    assert 'src="deltakit-visualise.umd.js"' not in out
    assert static_index.exists()


def test_prepare_html_file_not_found(mock_asset_reader):
    """Test prepare_html raises FileNotFoundError if index.html is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_dir = Path(tmpdir)
        mock_asset_reader(assets_dir)
        with pytest.raises(FileNotFoundError):
            data_utils.prepare_html({"foo": "bar"})


def test_prepare_html_library_tag_missing(prepare_html_dirs):
    """Test prepare_html raises ValueError if library tag is missing."""
    dirs = prepare_html_dirs
    index = dirs.assets_dir / "index.html"
    index.write_text(
        "<html><body><script>const deltaKit = new Deltakit('app');</script></body></html>"
    )

    err_msg = "Could not parse library script structure"
    with pytest.raises(ValueError, match=err_msg):
        data_utils.prepare_html({"foo": "bar"})


def test_prepare_html_js_assets_missing(monkeypatch, mock_asset_reader):
    """Test prepare_html raises FileNotFoundError if JS assets are not bundled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        js_dir = Path(tmpdir) / "js"
        assets_dir = Path(tmpdir) / "assets"
        js_dir.mkdir()
        assets_dir.mkdir()

        static_index = assets_dir / "index.html"
        static_index.write_text("""
<html><body>{{deltakit_vis_script}}</body></html>
""")

        mock_asset_reader(assets_dir)
        monkeypatch.setattr(data_utils, "JS_HOME_DIR", js_dir)
        # Don't create the npm file, so it's missing
        err_msg = "JavaScript assets not found"
        with pytest.raises(FileNotFoundError, match=err_msg):
            data_utils.prepare_html({"foo": "bar"})


def test_prepare_html_fallback_to_generic_script_tag(prepare_html_dirs):
    """Test prepare_html uses generic <script> tag fallback when Deltakit tag is missing."""
    dirs = prepare_html_dirs
    static_index = dirs.assets_dir / "index.html"
    # HTML with library script but without the Deltakit instantiation
    static_index.write_text("""
<html><body>{{deltakit_vis_script}}<script>console.log('other code');</script></body></html>
""")

    data_utils.prepare_html({"test": "data"})

    display_index = dirs.display_dir / "index.html"
    out = display_index.read_text()
    assert "data = {" in out
    assert '"test": "data"' in out
    assert dirs.umd_js_file.read_text() in out


def test_prepare_html_library_not_in_content_uses_generic_script(prepare_html_dirs):
    """Test error is raised when content doesn't have deltakit-vis library or script tags."""
    dirs = prepare_html_dirs
    static_index = dirs.assets_dir / "index.html"
    # HTML with no library includes and no generic script tags
    static_index.write_text("<html><body><div>Content without scripts</div></body></html>")

    err_msg = "Could not parse library script structure"
    with pytest.raises(ValueError, match=err_msg):
        data_utils.prepare_html({"foo": "bar"})
