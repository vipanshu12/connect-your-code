#!/usr/bin/env python3
"""WSGI entry point - for hosts that run the app themselves (PythonAnywhere).

`python3 server.py` binds its own socket, which shared hosts don't allow: they
import a module, find `application`, and call it once per request. Rather than
rewrite the router for WSGI, this replays each request through the very same
Handler over an in-memory socket, so local and hosted behaviour cannot drift.

    # PythonAnywhere WSGI config file:
    import sys; sys.path.insert(0, '/home/YOURUSER/sharma-site')
    from wsgi import application
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import Handler  # noqa: E402
from app import db  # noqa: E402

db.init()

# Sent verbatim by the host; re-sending them would duplicate the header.
_HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "upgrade",
               "proxy-authenticate", "proxy-authorization", "te", "trailers"}


class _Socket:
    """Just enough socket for BaseHTTPRequestHandler: read a canned request,
    collect the response in a buffer instead of sending it anywhere."""

    def __init__(self, request_bytes):
        self._in = io.BytesIO(request_bytes)
        self.out = io.BytesIO()

    def makefile(self, mode="rb", bufsize=-1):
        return self._in if "r" in mode else self.out

    def sendall(self, data):        # wbufsize is 0, so writes land here
        self.out.write(data)

    def close(self):
        pass


class _Server:
    """BaseHTTPRequestHandler keeps a reference to its server; nothing in this
    app reads it, but the attribute has to exist."""
    server_name = "wsgi"
    server_port = 0


def _raw_request(environ):
    """Rebuild the original HTTP request bytes from the WSGI environ."""
    path = environ.get("PATH_INFO", "/") or "/"
    query = environ.get("QUERY_STRING", "")
    if query:
        path = "%s?%s" % (path, query)

    body = b""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if length > 0:
        body = environ["wsgi.input"].read(length)

    lines = ["%s %s HTTP/1.1" % (environ.get("REQUEST_METHOD", "GET"), path)]
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            name = key[5:].replace("_", "-").title()
            if name.lower() not in _HOP_BY_HOP:
                lines.append("%s: %s" % (name, value))
    if environ.get("CONTENT_TYPE"):
        lines.append("Content-Type: %s" % environ["CONTENT_TYPE"])
    if length > 0:
        lines.append("Content-Length: %d" % length)
    # Without this the HTTP/1.1 handler waits for a second request on a stream
    # that will never produce one.
    lines.append("Connection: close")

    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


def _parse_response(raw):
    """Split the handler's raw output into (status line, headers, body)."""
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")

    # "HTTP/1.1 404 Not Found" -> "404 Not Found"
    status = lines[0].split(" ", 1)[1] if " " in lines[0] else "500 Internal Server Error"

    headers = []
    for line in lines[1:]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        name, value = name.strip(), value.strip()
        # Date/Server come from the handler; the host adds its own.
        if name.lower() in _HOP_BY_HOP or name.lower() in ("date", "server"):
            continue
        headers.append((name, value))
    return status, headers, body


def application(environ, start_response):
    sock = _Socket(_raw_request(environ))
    client = (environ.get("REMOTE_ADDR", "127.0.0.1"), 0)

    # Instantiating the handler runs the whole request cycle.
    try:
        Handler(sock, client, _Server())
    except Exception:
        import traceback
        traceback.print_exc()

    raw = sock.out.getvalue()
    if not raw:
        start_response("500 Internal Server Error",
                       [("Content-Type", "text/html; charset=utf-8")])
        return [b"<h1>500 - Something went wrong</h1>"]

    status, headers, body = _parse_response(raw)
    if environ.get("REQUEST_METHOD") == "HEAD":
        body = b""
    start_response(status, headers)
    return [body]
