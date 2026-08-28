# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Path constants and IR attribute key definitions for deltakit-visualise."""

import logging
from enum import Enum
from importlib.resources import files
from pathlib import Path
from typing import Final

from platformdirs import PlatformDirs

_logger = logging.getLogger(__name__)


class PlaquetteShape(str, Enum):
    """Supported plaquette shapes in patch visualisation payloads."""

    SQUARE = "square"
    SEMICIRCLE = "semicircle"


_DIRS: Final[PlatformDirs] = PlatformDirs("deltakit-visualise")

WORK_DIR: Final[Path] = Path(_DIRS.user_data_path)
CACHE_DIR: Final[Path] = Path(_DIRS.user_cache_path)

# Read-only JS assets bundled in the package during wheel build
JS_HOME_DIR: Final[Path] = Path(__file__).parent / ".js"

# Writable directory for generated output (e.g. index.html with injected data)
DISPLAY_DIR: Final[Path] = CACHE_DIR / "display"

_PATHS_TO_CREATE = [WORK_DIR, CACHE_DIR, DISPLAY_DIR]
for _path in _PATHS_TO_CREATE:
    try:
        _path.mkdir(parents=True, exist_ok=True)
    except OSError:
        _logger.warning("Failed to create directory %s", _path)


def get_asset_file_content(relative_path: str) -> str:
    """Read asset file content from the package using importlib.resources."""
    try:
        return (
            files("deltakit_visualise")
            .joinpath("assets", relative_path)
            .read_text(encoding="utf-8")
        )
    except FileNotFoundError as e:
        msg = f"Asset file '{relative_path}' not found in deltakit_visualise package: {e}"
        raise FileNotFoundError(msg) from e


# Attribute key where a pipeline's terminal pass stores its visualisation output
VISUALISE_SPACETIME_DATA: Final[str] = "visualise.spacetime.data"
PATCH_VISUALISATION_DATA: Final[str] = "visualise.patch_visualisation.data"
START_HEIGHT_ATTR: Final[str] = "visualise.start_height"
END_HEIGHT_ATTR: Final[str] = "visualise.end_height"
IN_OP_ID: Final[str] = "visualise.op.in.id"
OUT_OP_ID: Final[str] = "visualise.op.out.id"
IN_LOGICAL_PATCHES_ID: Final[str] = "visualise.multi_pauli_meas.logical_patches.in.id"
OUT_LOGICAL_PATCHES_ID: Final[str] = "visualise.multi_pauli_meas.logical_patches.out.id"
IN_BRIDGE_PATCHES_ID: Final[str] = "visualise.multi_pauli_meas.bridge_patches.in.id"
OUT_BRIDGE_PATCHES_ID: Final[str] = "visualise.multi_pauli_meas.bridge_patches.out.id"

# Allowed origins for CORS in the FastAPI server, update to include any additional origins as needed
ALLOWED_ORIGINS: Final[list[str]] = [f"http://localhost:{port_no}" for port_no in range(5173, 5179)]

# Commands to be injected into the frontend index.html for rendering visualisation data
RENDER_DATA_COMMAND = "deltakit.render(data);"
RENDER_DYNAMIC_COMMAND = "deltakit.renderDynamic();"
RENDER_VISUALISE_COMMAND = "deltakit.renderDynamic({ showSurfaceCodePanel: true });"

LOGICAL_PATCH = "logical_patch"
SPACE_TIME = "spacetime"

NOTEBOOK_HTML_SCRIPT: Final[str] = """
<script>
(function() {{
    const html = atob('{html_encoded}');
    const blob = new Blob([html], {{ type: 'text/html' }});
    const url = URL.createObjectURL(blob);

    const container = document.createElement('div');
    container.style.width = '100%';
    container.style.height = '500px';

    const iframe = document.createElement('iframe');
    iframe.src = url;
    iframe.style.width = '100%';
    iframe.style.height = '500px';
    iframe.style.border = 'none';
    iframe.sandbox.add('allow-scripts', 'allow-same-origin');

    container.appendChild(iframe);

    document.currentScript.parentElement.insertBefore(
        container,
        document.currentScript
    );
}})();
</script>
"""

FETCH_DATA_SCRIPT: Final[str] = """
fetch("/api/get-space-time-diagram")
    .then((response) => response.json())
    .then((data) => {
        const deltakit = new Deltakit('app');
        deltakit.render(data);
    })
    .catch((error) => {
        console.error("Error fetching data:", error);
    });
"""
