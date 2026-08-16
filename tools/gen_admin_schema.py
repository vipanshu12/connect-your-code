#!/usr/bin/env python3
"""Emit admin/schema.js from app/views.py so the JS admin can't drift from the
Python one it replaces."""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from app.views import SECTIONS, SETTING_GROUPS, SEO_GROUPS, PAGE_SEO_FIELDS, PUBLIC_ROUTES

OUT = os.path.join(BASE, "admin", "schema.js")

# Columns that are booleans in Postgres (were 0/1 in SQLite).
BOOL = {"active", "featured", "noindex", "nofollow"}
# Columns that need a bigger input than a single line.
LONG = {"description", "bio", "quote", "answer", "features", "body"}
# Columns that hold an image path and get the picker.
IMAGE = {"image", "og_image"}


def field_spec(table, name):
    if name in BOOL:
        kind = "bool"
    elif name in IMAGE:
        kind = "image"
    elif name in LONG:
        kind = "textarea"
    elif name in ("sort", "rating"):
        kind = "number"
    else:
        kind = "text"
    return {"name": name, "kind": kind, "label": name.replace("_", " ").title()}


def main():
    sections = {}
    for key, cfg in SECTIONS.items():
        sections[key] = {
            "table": cfg["table"],
            "label": cfg["label"],
            "icon": cfg["icon"],
            "order": cfg["order"],
            "fields": [field_spec(cfg["table"], f) for f in cfg["fields"]],
        }

    # faqs has a table and is rendered on the public site but the Python admin
    # never exposed it - add it here rather than leave it uneditable.
    sections["faqs"] = {
        "table": "faqs",
        "label": "FAQs",
        "icon": "ri-question-line",
        "order": "sort, id",
        "fields": [field_spec("faqs", f) for f in
                   ["question", "answer", "page", "sort", "active"]],
    }

    def groups(src, with_help):
        out = []
        for title, items in src:
            fields = []
            for item in items:
                key, label, kind = item[0], item[1], item[2]
                help_ = item[3] if with_help and len(item) > 3 else ""
                fields.append({"name": key, "label": label, "kind": kind, "help": help_})
            out.append({"title": title, "fields": fields})
        return out

    js = {
        "sections": sections,
        "settingGroups": groups(SETTING_GROUPS, False),
        "seoGroups": groups(SEO_GROUPS, True),
        "pageSeoFields": PAGE_SEO_FIELDS,
        "routes": sorted(set(PUBLIC_ROUTES.keys())),
    }

    body = json.dumps(js, indent=2, ensure_ascii=False)
    with open(OUT, "w") as fh:
        fh.write("// Generated from app/views.py - do not edit by hand.\n")
        fh.write("// Regenerate: python3 tools/gen_admin_schema.py\n")
        fh.write("//\n")
        fh.write("// Mirrors SECTIONS, SETTING_GROUPS, SEO_GROUPS and PAGE_SEO_FIELDS so the\n")
        fh.write("// JavaScript admin edits exactly the fields the Python admin edited.\n")
        fh.write("export const SCHEMA = ")
        fh.write(body)
        fh.write(";\n")

    print("  wrote %s" % OUT)
    print("  sections:       %d" % len(sections))
    for k, v in sections.items():
        print("    %-14s %-14s %2d fields" % (k, v["table"], len(v["fields"])))
    print("  setting groups: %d (%d fields)" % (
        len(js["settingGroups"]), sum(len(g["fields"]) for g in js["settingGroups"])))
    print("  seo groups:     %d (%d fields)" % (
        len(js["seoGroups"]), sum(len(g["fields"]) for g in js["seoGroups"])))
    print("  page seo fields:%d   routes: %d" % (len(PAGE_SEO_FIELDS), len(js["routes"])))


if __name__ == "__main__":
    main()
