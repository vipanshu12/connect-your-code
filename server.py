#!/usr/bin/env python3
"""Sharma Interior Construction - site + admin panel.

    python3 server.py                 # http://localhost:8000
    python3 server.py 8080            # custom port
    python3 server.py --lan           # reachable on your network
    python3 server.py --create-admin  # add or reset an admin login

Stdlib + Jinja2 + Pillow. No pip install required on this machine.
Public pages render from SQLite, so anything edited in /admin shows up
immediately on the site.
"""
import getpass
import http.server
import mimetypes
import os
import posixpath
import socket
import socketserver
import sys
import traceback
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import core, db  # noqa: E402
from app import seo  # noqa: E402
from app.views import PUBLIC_ROUTES, admin_router, render_public  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))

# Directories served verbatim. Everything else 404s - the app root is not
# browsable, so app/, templates/ and data/site.db are never exposed.
STATIC_DIRS = ("assets", "images", "static")
STATIC_FILES = {
    "favicon.ico", "favicon-32.png", "favicon-512.png", "apple-touch-icon.png",
    "logo.png", "logo-removebg-preview.png", "logo-white.png", "l.png", "logo.jpg",
    "homeback.jpg", "aboutback.jpg", "cc.jpg", "build.jpg", "site.jpg", "mall.jpg",
}


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "SharmaSite/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------- plumbing
    def _send(self, status, body=b"", ctype="text/html; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def redirect(self, location, extra=None):
        headers = {"Location": location}
        headers.update(extra or {})
        self._send(303, b"", "text/plain", headers)

    def not_found(self):
        try:
            self._send(404, render_public("404.html", {}, self))
        except Exception:
            self._send(404, "<h1>404 - Not found</h1>")

    @property
    def client_ip(self):
        return self.client_address[0] if self.client_address else "?"

    def cookies(self):
        return core.parse_cookies(self.headers.get("Cookie"))

    def session(self):
        return core.load_session(self.cookies().get(core.SESSION_COOKIE))

    # ------------------------------------------------------------- statics
    def try_static(self, path):
        rel = path.lstrip("/")
        if not rel:
            return False

        rel = posixpath.normpath(rel)
        if rel.startswith("..") or rel.startswith("/"):
            return False

        top = rel.split("/", 1)[0]
        allowed = (top in STATIC_DIRS) or (rel in STATIC_FILES)
        # uploaded media lives outside the web root and is mapped explicitly
        if rel.startswith("uploads/"):
            abs_path = os.path.join(db.UPLOAD_DIR, os.path.basename(rel))
            allowed = True
        else:
            abs_path = os.path.join(BASE, rel)

        if not allowed or not os.path.isfile(abs_path):
            return False

        # final guard against traversal
        real = os.path.realpath(abs_path)
        if not (real.startswith(os.path.realpath(BASE)) or
                real.startswith(os.path.realpath(db.UPLOAD_DIR))):
            return False

        ctype = mimetypes.guess_type(abs_path)[0] or "application/octet-stream"
        with open(abs_path, "rb") as fh:
            body = fh.read()

        cache = "public, max-age=2592000" if rel.startswith(("assets/", "images/", "uploads/", "static/")) \
                else "public, max-age=3600"
        self._send(200, body, ctype, {"Cache-Control": cache})
        return True

    # ------------------------------------------------------------- routing
    def route(self):
        path = urlsplit(self.path).path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        if path.startswith("/admin"):
            return admin_router(self, path)

        if self.command in ("GET", "HEAD"):
            # Generated from the database so the admin panel is the only place
            # anyone edits them. Never cached hard - a content change should
            # reach Google on the next crawl, not in a month.
            if path == "/robots.txt":
                return self._send(200, seo.robots_txt(), "text/plain; charset=utf-8",
                                  {"Cache-Control": "public, max-age=3600"})
            if path == "/sitemap.xml":
                return self._send(200, seo.sitemap_xml(), "application/xml; charset=utf-8",
                                  {"Cache-Control": "public, max-age=3600"})

            # An admin-managed 301 beats a 404: a renamed page keeps its rank.
            hit = db.query("SELECT * FROM redirects WHERE from_path = ?", (path,), one=True)
            if hit:
                db.execute("UPDATE redirects SET hits = hits + 1 WHERE id = ?", (hit["id"],))
                return self._send(301, b"", "text/plain", {"Location": hit["to_path"]})

            if path in PUBLIC_ROUTES:
                return self._send(200, render_public(PUBLIC_ROUTES[path], {}, self),
                                  extra={"Cache-Control": "no-cache"})
            if self.try_static(path):
                return
            return self.not_found()

        return self._send(405, "<h1>405 - Method not allowed</h1>")

    def do_GET(self):
        self.safe(self.route)

    def do_HEAD(self):
        self.safe(self.route)

    def do_POST(self):
        self.safe(self.route)

    def safe(self, fn):
        try:
            fn()
        except BrokenPipeError:
            pass
        except Exception:
            traceback.print_exc()
            try:
                self._send(500, "<h1>500 - Something went wrong</h1>")
            except Exception:
                pass

    def log_message(self, fmt, *args):
        try:
            line = fmt % args
        except Exception:
            line = str(fmt)
        sys.stderr.write("  %s\n" % line)


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def create_admin():
    db.init()
    print("\n  Create / reset an admin login\n")
    email = input("  Email: ").strip().lower()
    if not email or "@" not in email:
        print("  ! Not a valid email."); return 1
    name = input("  Name : ").strip() or "Administrator"
    pw = getpass.getpass("  Password (min 10 chars): ")
    if len(pw) < 10:
        print("  ! Too short - use at least 10 characters."); return 1
    if pw != getpass.getpass("  Confirm: "):
        print("  ! Passwords do not match."); return 1

    existing = db.query("SELECT id FROM users WHERE email = ?", (email,), one=True)
    if existing:
        db.execute("UPDATE users SET pw_hash = ?, name = ? WHERE id = ?",
                   (core.hash_password(pw), name, existing["id"]))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (existing["id"],))
        print("\n  Password reset for %s (all sessions revoked).\n" % email)
    else:
        db.execute("INSERT INTO users(email, name, pw_hash) VALUES(?,?,?)",
                   (email, name, core.hash_password(pw)))
        print("\n  Admin created: %s\n" % email)
    return 0


def main():
    if "--create-admin" in sys.argv:
        return create_admin()

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # PaaS hosts assign the port and expect the process to bind every
    # interface; binding loopback there makes the service unreachable and
    # the health check fails with no useful error.
    env_port = os.environ.get("PORT")
    port = int(env_port) if env_port else (int(args[0]) if args else 8000)
    host = "0.0.0.0" if (env_port or "--lan" in sys.argv) else "127.0.0.1"

    db.init()
    core.purge_expired()

    has_admin = db.query("SELECT 1 FROM users LIMIT 1")
    try:
        httpd = Server((host, port), Handler)
    except OSError as exc:
        print("Cannot bind %s:%d - %s" % (host, port, exc))
        return 1

    print("\n  Sharma Interior Construction")
    print("  site   http://localhost:%d" % port)
    print("  admin  http://localhost:%d/admin" % port)
    if host == "0.0.0.0":
        ip = lan_ip()
        if ip:
            print("  lan    http://%s:%d" % (ip, port))
    if not has_admin:
        print("\n  !! No admin user yet. In another terminal run:")
        print("     python3 server.py --create-admin")
    print("\n  Ctrl+C to stop\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
else:
    # Imported, not run - i.e. a serverless host (Vercel) is using this module
    # as its entrypoint. main() never executes there, so the schema would never
    # be created: route() queries the redirects table on EVERY GET, before
    # static files are even considered, so a missing schema turns all 500.
    # Creating it here is idempotent (CREATE TABLE IF NOT EXISTS).
    try:
        db.init()
    except Exception:
        # Must not take the whole module down - log it and let requests report.
        traceback.print_exc()

    # Vercel's Python runtime looks for a module-level `handler` subclassing
    # BaseHTTPRequestHandler. Exporting it here means the deploy works whether
    # the platform picks server.py or api/index.py as the entrypoint.
    handler = Handler
