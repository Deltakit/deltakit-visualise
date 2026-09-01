# (c) Copyright Riverlane 2025-2026. All rights reserved.
import json
import re
from typing import Any

from deltakit_visualise.constants import (
    DISPLAY_DIR,
    JS_HOME_DIR,
    RENDER_DATA_COMMAND,
    get_asset_file_content,
)


def _format_data(data: dict[str, Any] | str) -> str:
    """Format visualiser data"""
    if isinstance(data, str):
        return f"""
    <script>
        {data}
    </script>
    """
    return f"""
    <script>
        data = {json.dumps(data, indent=2)}
    </script>
    """


def prepare_html(data: dict[str, Any]) -> None:
    """Add data to main (index.html) HTML page"""
    formatted_data = _format_data(data)

    # Read index.html from assets using proper importlib.resources API
    content = get_asset_file_content("index.html")

    # The .js directory should be built into the package during wheel build
    # Check if the npm package was included in the package
    umd_js_path = "dist/deltakit-visualise.umd.js"
    umd_js_file = JS_HOME_DIR / umd_js_path

    if not umd_js_file.exists():
        msg = (
            f"JavaScript assets not found at '{umd_js_file}'. "
            "This should have been built into the package during installation. "
            "Please ensure the package was built with 'uv build --wheel' with npm "
            "and Node.js installed. "
            "Visit https://nodejs.org/ to install Node.js if needed."
        )
        raise FileNotFoundError(msg)

    # Write generated index.html to a writable cache directory
    display_index_html = DISPLAY_DIR / "index.html"

    # Pattern to match existing data script
    # Matches <script>...data = {...}...</script>
    # Uses re.DOTALL to match newlines
    data_script_pattern = r"<script>\s*data\s*=\s*\{[\s\S]*?<\/script>"

    if re.search(data_script_pattern, content):
        new_content = re.sub(data_script_pattern, formatted_data.strip(), content)  # type: ignore[attr-defined]
    else:
        library_tag_part = "{{deltakit_vis_script}}"
        err_msg = "Could not parse library script structure"
        if library_tag_part not in content:
            raise ValueError(err_msg)
        # Inline the JS so the HTML is self-contained
        js_content = umd_js_file.read_text(encoding="utf-8")
        inlined_lib = f"<script>\n{js_content}\n</script>"
        lib_tag_re = r"\{\{deltakit_vis_script\}\}"
        replacement = f"{inlined_lib}\n{formatted_data.strip()}"
        new_content = re.sub(lib_tag_re, lambda _: replacement, content)
        new_content = new_content.replace("{{deltakit_vis_script}}", inlined_lib)
    new_content = new_content.replace("{{fetch_data_script}}", "")
    new_content = new_content.replace("{{render_command}}", RENDER_DATA_COMMAND)

    with display_index_html.open("w") as file:
        file.write(new_content)
