# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Notebook-specific helpers for visualiser behaviour."""

import sys
from base64 import b64encode
from importlib import import_module

from deltakit_visualise.constants import DISPLAY_DIR, NOTEBOOK_HTML_SCRIPT
from deltakit_visualise.types import PatchVisualisationItem, SpaceTimeVisualisationItem
from deltakit_visualise.utils.data import prepare_html
from deltakit_visualise.utils.server import static_display

VisualisationItem = SpaceTimeVisualisationItem | PatchVisualisationItem


def is_running_in_notebook() -> bool:
    """Return True when executing inside a Jupyter notebook kernel."""
    return "ipykernel" in sys.modules


def add_cell_html_to_notebook(data: dict[str, list[VisualisationItem]]) -> None:
    """Display visualisation in notebook with a Python-side button to open in browser.

    The inline iframe uses a blob URL (works in both VS Code and JupyterLab).
    The \"Open link\" button uses ipywidgets (Python comm) so that clicking it calls
    Python's webbrowser.open() — this works in both VS Code and JupyterLab.
    """

    prepare_html(data)

    html_path = DISPLAY_DIR / "index.html"

    with html_path.open("r", encoding="utf-8") as f:
        html_encoded = b64encode(f.read().encode()).decode()

    try:
        ipython_display = import_module("IPython.display")
    except ImportError as e:
        msg = (
            "Could not import 'IPython.display'. IPython is only available in "
            "notebook environments "
            "and add_cell_html_to_notebook should not be called outside of a notebook."
        )
        raise RuntimeError(msg) from e
    ipython_display.display(
        ipython_display.HTML(NOTEBOOK_HTML_SCRIPT.format(html_encoded=html_encoded))
    )

    widgets = import_module("ipywidgets")

    def _open_in_browser(_button: object) -> None:
        prepare_html(data)
        static_display()

    button = widgets.Button(
        description="Open link \u2197",
        layout=widgets.Layout(margin="4px 0 0 0"),
    )
    button.on_click(_open_in_browser)
    ipython_display.display(
        widgets.HBox(
            [button],
            layout=widgets.Layout(width="100%", justify_content="flex-end"),
        )
    )
