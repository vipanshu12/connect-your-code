#!/usr/bin/env python3
"""Pull content from Supabase into the local SQLite database.

    python3 sync.py            # refresh data/site.db from Supabase

Supabase is the source of truth once the JavaScript admin is in use, but the
renderer, the SEO module and every template already read SQLite and are known
to work. Rather than reimplement those queries against Postgres - and risk the
output drifting - this copies the content down and lets the proven code run
unchanged. build.py calls it automatically.

Credentials come from the environment (SUPABASE_URL / SUPABASE_ANON_KEY) so a
build host can supply them, falling back to admin/config.js for local runs.
Reads only ever use the public key: RLS allows select and nothing else.
"""
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_JS = os.path.join(BASE, "admin", "config.js")

# Order matters only for readability - there are no foreign keys between them.
TABLES = ["settings", "services", "projects", "team", "testimonials",
          "faqs", "jobs", "page_seo", "media", "redirects"]

# Postgres booleans have to go back to the 0/1 the SQLite schema and the
# templates expect.
BOOL_COLS = {"active", "featured", "noindex", "nofollow"}
TS_COLS = {"created_at", "updated_at"}


def credentials():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key

    # Local convenience: read the same values the admin panel uses.
    try:
        with open(CONFIG_JS) as fh:
            src = fh.read()
    except OSError:
        return "", ""
    found = dict(re.findall(
        r'export const (SUPABASE_URL|SUPABASE_ANON_KEY)\s*=\s*"([^"]*)"', src))
    return (url or found.get("SUPABASE_URL", "")).rstrip("/"), \
           key or found.get("SUPABASE_ANON_KEY", "")


def fetch(url, key, table):
    req = urllib.request.Request(
        "%s/rest/v1/%s?select=*" % (url, table),
        headers={"apikey": key, "Authorization": "Bearer %s" % key})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def coerce(col, value):
    if col in BOOL_COLS:
        return 1 if value else 0
    if col in TS_COLS and isinstance(value, str) and value:
        # 2026-08-15T09:21:04.123456+00:00 -> 2026-08-15 09:21:04, the format
        # seo.py hands to the sitemap as <lastmod>.
        return value.replace("T", " ")[:19]
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def main():
    url, key = credentials()
    if not url or not key:
        print("  ! No Supabase credentials.")
        print("    Set SUPABASE_URL and SUPABASE_ANON_KEY, or fill in admin/config.js.")
        return 1

    sys.path.insert(0, BASE)
    from app import db

    db.init()
    con = db.connect()

    print("\n  pulling from %s" % url)
    total = 0
    for table in TABLES:
        try:
            rows = fetch(url, key, table)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:200]
            print("    FAIL %-14s HTTP %s  %s" % (table, exc.code, body))
            return 1
        except urllib.error.URLError as exc:
            print("    FAIL %-14s %s" % (table, exc.reason))
            return 1

        # Only replace the table once the fetch succeeded, so a network error
        # can never leave the site with a half-empty database.
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]
        con.execute("DELETE FROM %s" % table)
        for row in rows:
            keep = [c for c in cols if c in row]
            con.execute(
                "INSERT INTO %s (%s) VALUES (%s)" % (
                    table, ", ".join(keep), ", ".join("?" * len(keep))),
                tuple(coerce(c, row[c]) for c in keep))
        con.commit()
        print("    %-14s %3d rows" % (table, len(rows)))
        total += len(rows)

    print("\n  %d rows into %s\n" % (total, db.DB_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
