#!/usr/bin/env python3
"""Render the public site to plain files in dist/ for static hosting.

    python3 build.py            # -> dist/

The public pages read from SQLite but nothing on them posts back: the contact
form goes to formsubmit.co and the newsletter is client-side only. So the
server is only needed to *produce* the HTML, not to serve it - which means the
finished pages can sit on any plain web host.

Workflow: edit content in /admin locally, run this, upload dist/.
The admin panel stays on your machine; it is deliberately not exported.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wsgi import application  # noqa: E402  - renders through the real handler
from app import db  # noqa: E402
from app.views import PUBLIC_ROUTES  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(BASE, "dist")

# static/admin is the admin panel's CSS - no reason to publish it.
COPY_DIRS = ("assets", "images")
ROOT_FILES = (
    "favicon.ico", "favicon-32.png", "favicon-512.png", "apple-touch-icon.png",
    "logo.png", "logo-removebg-preview.png", "logo-white.png", "l.png", "logo.jpg",
    "homeback.jpg", "aboutback.jpg", "cc.jpg", "build.jpg", "site.jpg", "mall.jpg",
)


def fetch(path):
    """Run one GET through the app and return (status, body)."""
    import io
    env = {
        "REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": "",
        "SERVER_NAME": "build", "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1", "REMOTE_ADDR": "127.0.0.1",
        "wsgi.input": io.BytesIO(b""), "wsgi.errors": sys.stderr,
        "wsgi.version": (1, 0), "wsgi.url_scheme": "https",
        "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": True,
    }
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    body = b"".join(application(env, start_response))
    return captured.get("status", "500 ?"), body


def write(rel, data):
    dest = os.path.join(DIST, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


def main():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    failures = 0

    # ---- pages. "/" and "/index.html" render the same template; one file
    # serves both because web servers fall back to index.html for a bare "/".
    print("\n  pages")
    for route, template in sorted(PUBLIC_ROUTES.items()):
        name = "index.html" if route == "/" else route.lstrip("/")
        status, body = fetch(route)
        code = int(status.split()[0])
        if code != 200:
            print("    FAIL %-16s %s" % (route, status))
            failures += 1
            continue
        print("    %-16s -> %-16s %6d bytes" % (route, name, write(name, body)))

    # ---- generated from the database, so they must be rendered, not copied
    print("\n  generated")
    for route in ("/robots.txt", "/sitemap.xml"):
        status, body = fetch(route)
        if int(status.split()[0]) != 200:
            print("    FAIL %-16s %s" % (route, status))
            failures += 1
            continue
        print("    %-16s %6d bytes" % (route, write(route.lstrip("/"), body)))

    # ---- assets
    print("\n  assets")
    for d in COPY_DIRS:
        src = os.path.join(BASE, d)
        if not os.path.isdir(src):
            continue
        shutil.copytree(src, os.path.join(DIST, d))
        n = sum(len(f) for _, _, f in os.walk(src))
        print("    %-16s %d files" % (d + "/", n))

    copied = 0
    for f in ROOT_FILES:
        src = os.path.join(BASE, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(DIST, f))
            copied += 1
    print("    %-16s %d files" % ("(root)", copied))

    # ---- admin uploads live outside the web root; the pages reference them
    # at /uploads/, so they have to come along.
    if os.path.isdir(db.UPLOAD_DIR):
        files = [f for f in os.listdir(db.UPLOAD_DIR)
                 if os.path.isfile(os.path.join(db.UPLOAD_DIR, f))]
        if files:
            os.makedirs(os.path.join(DIST, "uploads"), exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(db.UPLOAD_DIR, f),
                             os.path.join(DIST, "uploads", f))
        print("    %-16s %d files" % ("uploads/", len(files)))

    # ---- serve the site's own 404 page instead of the host's default
    # (Apache reads .htaccess; Vercel picks up 404.html on its own)
    write(".htaccess", b"ErrorDocument 404 /404.html\n")
    status, body = fetch("/definitely-missing")
    if int(status.split()[0]) == 404:
        write("404.html", body)

    # ---- host config for Vercel. cleanUrls stays off on purpose: it would
    # rewrite /about.html to /about, and the nav highlighting in main.js
    # compares the last path segment against each link's href.
    # Filenames are not content-hashed, so CSS/JS get a short TTL - otherwise
    # a redeploy leaves returning visitors on a stale stylesheet.
    write("vercel.json", b"""{
  "cleanUrls": false,
  "trailingSlash": false,
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=3600, must-revalidate" }]
    },
    {
      "source": "/images/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=2592000" }]
    },
    {
      "source": "/uploads/(.*)",
      "headers": [{ "key": "Cache-Control", "value": "public, max-age=2592000" }]
    }
  ]
}
""")

    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(DIST) for f in fs)
    print("\n  dist/  %.1f MB" % (total / 1048576.0))
    if failures:
        print("  %d page(s) failed - do not upload.\n" % failures)
        return 1
    print("  Upload the CONTENTS of dist/ to public_html/\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
