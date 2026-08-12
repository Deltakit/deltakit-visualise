# (c) Copyright Riverlane 2020-2026.
"""Tests for the visualisation HTTP server and static-display helpers."""

import errno
import socket
import socketserver
import threading
import urllib.request
from pathlib import Path
from unittest import mock

import pytest

from deltakit_visualise.utils import server as server_utils


@pytest.fixture
def display_dir(tmp_path, monkeypatch) -> Path:
    """Point DISPLAY_DIR at a tmp dir holding an index.html."""
    (tmp_path / "index.html").write_text("<html>hello</html>")
    monkeypatch.setattr(server_utils, "DISPLAY_DIR", tmp_path)
    return tmp_path


def test_bind_server_uses_base_port_when_free(monkeypatch):
    """When the base port is free, it is the one that gets bound."""
    monkeypatch.setattr(server_utils, "_BASE_PORT", 0)  # let OS pick a free port
    server = server_utils._bind_server(server_utils.CustomHandler)
    try:
        assert server.server_address[1] != 0  # a concrete port was assigned
    finally:
        server.server_close()


def test_bind_server_skips_busy_ports(monkeypatch):
    """Ports already in use are skipped until a free one is found."""
    monkeypatch.setattr(server_utils, "_BASE_PORT", 8899)
    busy = {8899, 8900}
    real_tcp_server = socketserver.TCPServer

    def fake_tcp_server(addr, handler_cls):
        if addr[1] in busy:
            raise OSError(errno.EADDRINUSE, "address in use")
        return real_tcp_server(("", 0), handler_cls)  # bind a real free socket

    with mock.patch.object(server_utils.socketserver, "TCPServer", fake_tcp_server):
        server = server_utils._bind_server(server_utils.CustomHandler)
    server.server_close()  # bound successfully after skipping the busy ports


def test_bind_server_reraises_non_address_in_use_errors(monkeypatch):
    """An OSError that isn't EADDRINUSE is not swallowed by the retry loop."""
    monkeypatch.setattr(server_utils, "_BASE_PORT", 8899)

    def boom(addr, handler_cls):  # noqa: ARG001
        raise OSError(errno.EACCES, "permission denied")

    with (
        mock.patch.object(server_utils.socketserver, "TCPServer", boom),
        pytest.raises(OSError, match="permission denied") as exc_info,
    ):
        server_utils._bind_server(server_utils.CustomHandler)
    assert exc_info.value.errno == errno.EACCES


def test_bind_server_raises_when_no_free_port(monkeypatch):
    """When every candidate port is busy, a clear OSError is raised."""
    monkeypatch.setattr(server_utils, "_BASE_PORT", 8899)
    monkeypatch.setattr(server_utils, "_PORT_RETRIES", 3)

    def always_busy(addr, handler_cls):  # noqa: ARG001
        raise OSError(errno.EADDRINUSE, "address in use")

    with (
        mock.patch.object(server_utils.socketserver, "TCPServer", always_busy),
        pytest.raises(OSError, match="No free port found"),
    ):
        server_utils._bind_server(server_utils.CustomHandler)


def test_static_display_opens_index_as_file_uri(display_dir):
    """static_display opens the generated index.html via a file:// URI."""
    with mock.patch.object(server_utils.webbrowser, "open") as mock_open:
        server_utils.static_display()

    mock_open.assert_called_once()
    (opened_uri,) = mock_open.call_args.args
    assert opened_uri == (display_dir / "index.html").as_uri()
    assert opened_uri.startswith("file://")


def test_start_server_opens_browser_and_cleans_up():
    """start_server serves on the bound port, opens the browser, then tears down."""
    fake_server = mock.Mock()
    fake_server.server_address = ("", 8899)

    class ImmediateThread:
        """Stand-in for threading.Thread whose serve loop is a no-op."""

        def __init__(self, *args, **kwargs) -> None:
            pass

        def start(self) -> None:
            pass

        def join(self) -> None:
            pass

    with (
        mock.patch.object(server_utils, "_bind_server", return_value=fake_server),
        mock.patch.object(server_utils.threading, "Thread", ImmediateThread),
        mock.patch.object(server_utils.webbrowser, "open") as mock_open,
    ):
        server_utils.start_server()

    mock_open.assert_called_once_with("http://localhost:8899/")
    # The port is always freed, even though serve_forever never really ran.
    fake_server.shutdown.assert_called_once()
    fake_server.server_close.assert_called_once()


def test_start_server_frees_port_on_keyboard_interrupt():
    """A Ctrl-C while blocked on join() still shuts the server down cleanly."""
    fake_server = mock.Mock()
    fake_server.server_address = ("", 8899)

    class InterruptingThread:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def start(self) -> None:
            pass

        def join(self) -> None:
            raise KeyboardInterrupt

    with (
        mock.patch.object(server_utils, "_bind_server", return_value=fake_server),
        mock.patch.object(server_utils.threading, "Thread", InterruptingThread),
        mock.patch.object(server_utils.webbrowser, "open"),
        pytest.raises(KeyboardInterrupt),
    ):
        server_utils.start_server()

    fake_server.shutdown.assert_called_once()
    fake_server.server_close.assert_called_once()


@pytest.mark.usefixtures("display_dir")
def test_custom_handler_serves_files_from_display_dir():
    """A live server built from CustomHandler serves index.html from DISPLAY_DIR."""
    server = server_utils._bind_server(server_utils.CustomHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/index.html", timeout=5) as resp:
            assert resp.status == 200
            assert resp.read().decode() == "<html>hello</html>"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_bound_server_accepts_tcp_connections(monkeypatch):
    """A server bound via _bind_server accepts TCP connections."""
    monkeypatch.setattr(server_utils, "_BASE_PORT", 0)
    server = server_utils._bind_server(server_utils.CustomHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with socket.create_connection(("localhost", port), timeout=5) as sock:
            assert sock is not None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
