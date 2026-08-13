"""Vercel serverless entrypoint.

Vercel's Python runtime accepts a module-level `handler` that subclasses
BaseHTTPRequestHandler - which is exactly what server.py already defines, so
the routing, static allowlist and admin panel are reused untouched. Nothing
here calls serve_forever(); the platform owns the request loop.

Read this before trusting a deploy:

  Vercel's filesystem is read-only apart from /tmp, and /tmp is per-instance
  and wiped without warning. SQLite therefore works for READS only - the
  database bundled with the deployment is served fine, but every admin edit,
  every login session and every uploaded image is discarded, sometimes
  mid-session. Point the app at Turso (see app/db.py) before treating the
  admin panel as usable here.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The only writable path in the sandbox. Set before importing db, which
# resolves DATA_DIR at import time.
os.environ.setdefault("DATA_DIR", "/tmp/site-data")

from app import db          # noqa: E402
from server import Handler  # noqa: E402

# Cold start: create the schema in /tmp so reads work. A warm instance skips
# this. If the DB is unwritable the site must still render, so failure here
# is logged and swallowed rather than turning every page into a 500.
try:
    db.init()
except Exception as exc:  # pragma: no cover - platform-dependent
    print("db.init() failed on cold start: %r" % (exc,), file=sys.stderr)

handler = Handler
