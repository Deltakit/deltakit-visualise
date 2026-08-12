# This file contains information which is proprietary to Riverlane Ltd
# ("Riverlane") and is Riverlane Confidential Information.
# (c) Copyright Riverlane 2025-2026. All rights reserved.
import errno
import http.server
import logging
import socketserver
import threading
import webbrowser
from typing import NoReturn

from deltakit_visualise.constants import DISPLAY_DIR

from .logging import _stream_handler

logger = logging.Logger(__name__)
logger.addHandler(_stream_handler)

_BASE_PORT = 8899
_PORT_RETRIES = 50


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    """Serves files from DISPLAY_DIR."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=DISPLAY_DIR, **kwargs)


def _bind_server(handler_cls: type) -> socketserver.TCPServer:
    """Bind to the first free port starting at _BASE_PORT."""
    for i in range(_PORT_RETRIES):
        try:
            return socketserver.TCPServer(("", _BASE_PORT + i), handler_cls)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    msg = f"No free port found in range [{_BASE_PORT}, {_BASE_PORT + _PORT_RETRIES})"
    raise OSError(msg)


def static_display() -> None:
    """Open the generated HTML in the browser via file:// URI (non-blocking)."""
    webbrowser.open((DISPLAY_DIR / "index.html").as_uri())


def start_server() -> NoReturn:  # type: ignore[misc]
    """Start a blocking HTTP server for the visualisation.

    Finds the first free port near _BASE_PORT, logs the URL, and opens the
    browser. Blocks until Ctrl-C, then frees the port before returning.

    Pass static=False to show() to use this instead of static_display().

    TODO: replace with a client/server architecture supporting frontend interactivity.
    """
    server = _bind_server(CustomHandler)
    port = server.server_address[1]
    url = f"http://localhost:{port}/"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Visualisation running on %s", url)
    logger.info("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        thread.join()
    finally:
        server.shutdown()
        server.server_close()
