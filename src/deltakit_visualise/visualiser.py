# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""Reading visualisation data off a module and rendering it in the browser."""

import json
import logging
from pathlib import Path

from xdsl.dialects.builtin import ModuleOp, StringAttr

from deltakit_visualise.constants import (
    DISPLAY_DIR,
    LOGICAL_PATCH,
    PATCH_VISUALISATION_DATA,
    SPACE_TIME,
    VISUALISE_SPACETIME_DATA,
)
from deltakit_visualise.types import PatchVisualisationItem, SpaceTimeVisualisationItem
from deltakit_visualise.utils.data import prepare_html
from deltakit_visualise.utils.notebook import (
    add_cell_html_to_notebook,
    is_running_in_notebook,
)
from deltakit_visualise.utils.server import start_server, static_display

logger = logging.getLogger(__name__)

# The ``type`` discriminators carried by SpaceTimeVisualisationItem
# (SurfaceData / SidesData). show() uses these to recognise spacetime data.
_SPACETIME_ITEM_TYPES = frozenset({"surface", "side"})
_PATCH_ITEM_KEYS = frozenset({"round", "qubits", "patches"})
VisualisationItem = SpaceTimeVisualisationItem | PatchVisualisationItem


def get_visualisation_data(
    module: ModuleOp,
) -> dict[str, list[VisualisationItem]]:
    """Read the visualisation data a terminal pass stored on ``module``.

    A visualisation pipeline's final passes writes outputs to the module
    under either :data:`deltakit_visualise.constants.VISUALISE_SPACETIME_DATA` (spacetime)
    or :data:`deltakit_visualise.constants.PATCH_VISUALISATION_DATA` (logical patch). This
    returns that payload as ``{"ops": [...]}``, ready to hand to :func:`show`.

    Args:
        module: A module that a visualisation pipeline has already run over.

    Returns:
        The ``{"ops": [...]}`` payload.

    Raises:
        ValueError: If the module carries no visualisation data — typically
            because no terminal visualisation pass has been run over it.
    """
    attr = module.attributes.get(VISUALISE_SPACETIME_DATA) or module.attributes.get(
        PATCH_VISUALISATION_DATA
    )
    visualisation_type = (
        f"{SPACE_TIME}" if module.attributes.get(VISUALISE_SPACETIME_DATA) else f"{LOGICAL_PATCH}"
    )
    if attr is None:
        msg = (
            "No visualisation data found. Run a visualisation pipeline "
            f"(terminal pass writes {visualisation_type}) "
            "over the module first."
        )
        raise ValueError(msg)
    assert isinstance(attr, StringAttr)
    return {"type": visualisation_type, "ops": json.loads(attr.data)}


def show(data: dict[str, list[VisualisationItem]], static: bool = True) -> Path:
    """Render visualisation data in the browser.

    Pass the ``{"ops": [...]}`` payload from :func:`get_visualisation_data`.
    The view is determined from the item schema:
    ``SpaceTimeVisualisationItem`` (``type`` of ``"surface"``/``"side"``)
    renders the 3D spacetime view, while ``PatchVisualisationItem``
    (``round``/``qubits``/``patches`` fields) renders the 2D patch view.

    Args:
        data: The ``{"ops": [...]}`` payload to render.
        static: If True (default), open the generated HTML in the system browser
            without starting an HTTP server (non-blocking). If False, start a
            blocking HTTP server on port 8899.

            TODO: The server mode (static=False) will be replaced by a proper
            client/server architecture that supports dynamic queries from the
            frontend. See the client/server milestone.

    Returns:
        Path to the generated index.html.

    Raises:
        NotImplementedError: If the items belong to a view whose rendering is
            not yet implemented.
    """
    items = data["ops"]
    visualisation_type = data["type"]

    if (
        visualisation_type == SPACE_TIME
        and all(item.get("type") in _SPACETIME_ITEM_TYPES for item in items)
    ) or (
        visualisation_type == LOGICAL_PATCH
        and all(_PATCH_ITEM_KEYS.issubset(item) for item in items)
    ):
        prepare_html(data)
    else:
        msg = f"Visualisation data for '{visualisation_type}' is not recognised by show()."
        raise NotImplementedError(msg)

    if static:
        if is_running_in_notebook():
            add_cell_html_to_notebook(data)
        else:
            static_display()
    else:
        try:
            start_server()
        except KeyboardInterrupt:
            logger.info("HTTP server terminated")
        except Exception:
            logger.error("HTTP server panicked")
            raise
    return DISPLAY_DIR / "index.html"
