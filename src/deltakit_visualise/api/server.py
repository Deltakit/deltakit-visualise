# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""FastAPI server for deltakit-visualise."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from deltakit_visualise.constants import (
    ALLOWED_ORIGINS,
    FETCH_DATA_SCRIPT,
    RENDER_DYNAMIC_COMMAND,
)

APP_NAME = "deltakit-visualise"
BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "assets" / "index.html"

DELTAKIT_VIS_SCRIPT = '<script src="/deltakit-visualise.umd.js"></script>'


def create_app(
    space_time_data: dict[str, Any],
    logical_patches_data: dict[str, Any],
    render_command: str = RENDER_DYNAMIC_COMMAND,
) -> FastAPI:
    """Create a FastAPI app with the given module_op."""
    app = FastAPI(title=APP_NAME)

    app.state.space_time_data = space_time_data
    app.state.logical_patches_data = logical_patches_data

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def serve_index() -> HTMLResponse:
        """Serve the frontend index.html with render command injected."""
        content = INDEX_HTML.read_text(encoding="utf-8")
        modified_content = content.replace("{{fetch_data_script}}", FETCH_DATA_SCRIPT)
        modified_content = modified_content.replace(
            "{{render_command}}", render_command
        )
        modified_content = modified_content.replace(
            "{{deltakit_vis_script}}", DELTAKIT_VIS_SCRIPT
        )
        return HTMLResponse(content=modified_content)

    @app.get("/deltakit-visualise.umd.js")
    async def serve_deltakit_vis_js() -> FileResponse:
        """Serve the deltakit-visualise JavaScript library."""
        umd_js_path = ".js/dist/deltakit-visualise.umd.js"

        return FileResponse(BASE_DIR / umd_js_path)

    @app.get("/api/get-space-time-diagram")
    async def get_space_time_diagram() -> dict:
        """Return space-time diagram data."""

        return app.state.space_time_data

    @app.get("/api/get-patches-info-at-round/{round_no}")
    async def get_patches_info_at_round(round_no: int) -> dict:
        """Return logical patch data for the specified round."""

        ops_list = app.state.logical_patches_data.get("ops", [])
        patch_data_for_round = [op for op in ops_list if op.get("round") == round_no]

        return {
            "type": app.state.logical_patches_data.get("type", ""),
            "ops": patch_data_for_round,
        }

    @app.get("/api/get-patches-info-at-rounds/{start}...{end}")
    async def get_patches_info_at_rounds(start: int, end: int) -> dict:
        """Return logical patch data for a range of rounds (inclusive)."""

        ops_list = app.state.logical_patches_data.get("ops", [])
        patch_data_for_rounds = [
            op for op in ops_list if start <= op.get("round", 0) <= end
        ]

        return {
            "type": app.state.logical_patches_data.get("type", ""),
            "ops": patch_data_for_rounds,
        }

    return app
