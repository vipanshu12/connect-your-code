"""Public page rendering and the admin panel.

The admin is deliberately small: a login, a dashboard, one editable settings
screen, and add/edit/delete for the four repeating sections plus image uploads.
No analytics, no inbox, no user management beyond the CLI.
"""
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import core, db, seo

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(BASE, "templates")

def media(path):
    """Resolve an image field to a usable src.

    Two kinds of value live in these columns now: repo-relative paths that
    shipped with the code ("images/hero.jpg"), and absolute URLs returned by
    Supabase Storage for anything uploaded through the admin. Templates used to
    hardcode a leading slash, which turned the second kind into
    "/https://..." and broke every uploaded image.
    """
    path = (path or "").strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://", "//", "data:")):
        return path
    return "/" + path.lstrip("/")


def _env(subdir):
    environment = Environment(
        loader=FileSystemLoader(os.path.join(TEMPLATES, subdir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["media"] = media
    return environment


# Separate environments on purpose: both trees contain a base.html, and a
# shared search path made admin templates inherit the public one.
env = _env("public")
env_admin = _env("admin")

# The visible breadcrumbs and the BreadcrumbList schema are generated from
# this one table, so they can never drift apart.
CRUMBS = {
    "/about.html":   [("Home", "/"), ("About Us", "/about.html")],
    "/service.html": [("Home", "/"), ("Services", "/service.html")],
    "/project.html": [("Home", "/"), ("Projects", "/project.html")],
    "/contact.html": [("Home", "/"), ("Contact", "/contact.html")],
}

PUBLIC_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/about.html": "about.html",
    "/service.html": "service.html",
    "/project.html": "project.html",
    "/contact.html": "contact.html",
}

# Which table each admin section maps to, and the columns its form writes.
SECTIONS = {
    "services": {
        "table": "services",
        "label": "Services",
        "icon": "ri-hammer-line",
        "fields": ["title", "description", "icon", "image", "features", "sort", "active", "featured"],
        "order": "sort, id",
    },
    "projects": {
        "table": "projects",
        "label": "Projects",
        "icon": "ri-building-2-line",
        "fields": ["title", "location", "category", "status", "completion",
                   "description", "image", "sort", "active", "featured"],
        "order": "sort, id",
    },
    "team": {
        "table": "team",
        "label": "Team",
        "icon": "ri-team-line",
        "fields": ["name", "role", "bio", "image", "linkedin", "email", "sort", "active"],
        "order": "sort, id",
    },
    "testimonials": {
        "table": "testimonials",
        "label": "Testimonials",
        "icon": "ri-chat-quote-line",
        "fields": ["name", "company", "quote", "rating", "image", "sort", "active"],
        "order": "sort, id",
    },
    "jobs": {
        "table": "jobs",
        "label": "Careers",
        "icon": "ri-briefcase-line",
        "fields": ["title", "location", "experience", "employment", "description", "sort", "active"],
        "order": "sort, id",
    },
}

SETTING_GROUPS = [
    ("Hero Section", [
        ("hero_heading", "Headline (HTML allowed)", "textarea"),
        ("hero_text", "Sub-heading", "textarea"),
        ("hero_image", "Background image", "image"),
    ]),
    ("About Section", [
        ("about_heading", "Heading", "text"),
        ("about_text", "Body copy", "textarea"),
        ("about_image", "Image", "image"),
    ]),
    ("Mission, Vision & Values", [
        ("mission", "Mission", "textarea"),
        ("vision", "Vision", "textarea"),
        ("values", "Values", "textarea"),
    ]),
    ("Statistics", [
        ("stat_years", "Years of experience", "text"),
        ("stat_projects", "Projects completed", "text"),
        ("stat_clients", "Satisfied clients", "text"),
        ("stat_workforce", "Workforce size", "text"),
    ]),
    ("Contact Details", [
        ("phone", "Primary phone", "text"),
        ("phone_alt", "Secondary phone", "text"),
        ("email", "General email", "text"),
        ("email_careers", "Careers email", "text"),
        ("address", "Office address", "textarea"),
        ("hours", "Working hours", "text"),
        ("map_embed", "Google Maps embed URL", "textarea"),
    ]),
    ("Social Links", [
        ("facebook", "Facebook URL", "text"),
        ("instagram", "Instagram URL", "text"),
        ("linkedin", "LinkedIn URL", "text"),
        ("whatsapp", "WhatsApp URL", "text"),
    ]),
    ("Footer & SEO", [
        ("site_name", "Company name", "text"),
        ("footer_text", "Footer description", "textarea"),
        ("seo_title", "Default page title", "text"),
        ("seo_description", "Meta description", "textarea"),
    ]),
]

# The SEO screen is separate from Site Content: these settings change how the
# site appears in Google rather than what it says.
SEO_GROUPS = [
    ("Global SEO", [
        ("seo_site_url", "Website address (https://...)", "text",
         "Everything absolute is built from this: canonical tags, the sitemap, "
         "share images and all structured data. Google ignores relative URLs."),
        ("seo_title", "Default page title", "text",
         "Used when a page has no title of its own."),
        ("seo_title_suffix", "Title suffix", "text",
         "Appended to every page title, e.g. ' | Sharma Interior Construction'."),
        ("seo_description", "Default meta description", "textarea", ""),
        ("seo_default_image", "Default share image", "image",
         "Shown when a page is posted to WhatsApp, Facebook or LinkedIn. 1200x630 is ideal."),
        ("seo_keywords", "Keywords", "textarea",
         "Google ignores this tag, but Bing still reads it and it keeps your target "
         "terms written down in one place."),
        ("seo_noindex_site", "Hide the whole site from Google (0 or 1)", "text",
         "Set to 1 while the site is unfinished. Remember to set it back to 0 at launch."),
    ]),
    ("Search Console & Analytics", [
        ("seo_verification", "Google Search Console verification code", "text",
         "Paste only the content value from the meta tag Google gives you."),
        ("seo_bing_verification", "Bing Webmaster verification code", "text", ""),
        ("ga_measurement_id", "Google Analytics 4 ID", "text", "Looks like G-XXXXXXXXXX. Leave blank for no tracking."),
        ("gtm_id", "Google Tag Manager ID", "text", "Looks like GTM-XXXXXXX."),
        ("seo_twitter_handle", "X / Twitter handle", "text", "With the @."),
    ]),
    ("Local SEO - business details", [
        ("biz_legal_name", "Registered business name", "text",
         "Must match your Google Business Profile exactly."),
        ("biz_street", "Street address", "text", ""),
        ("biz_city", "City", "text", ""),
        ("biz_state", "State", "text", ""),
        ("biz_postal", "PIN code", "text", ""),
        ("biz_country", "Country code", "text", "Two letters, e.g. IN."),
        ("biz_lat", "Latitude", "text", ""),
        ("biz_lng", "Longitude", "text", ""),
        ("biz_hours_spec", "Opening hours", "text",
         'Exact format "Mo-Sa 09:00-18:00" - anything else is skipped in the schema.'),
        ("biz_areas", "Service areas", "textarea", "Comma separated. Only list places you actually work."),
        ("biz_price_range", "Price range", "text", "$ to $$$$."),
        ("biz_founded", "Year founded", "text", ""),
        ("biz_profile_url", "Google Business Profile URL", "text", ""),
    ]),
]

PAGE_SEO_FIELDS = ["title", "description", "keyword", "og_title", "og_desc",
                   "og_image", "canonical", "changefreq", "priority"]


# --------------------------------------------------------------- public side
def site_context():
    s = db.get_settings()
    services = db.query("SELECT * FROM services WHERE active=1 ORDER BY sort, id")
    for svc in services:
        try:
            svc["features"] = json.loads(svc.get("features") or "[]")
        except Exception:
            svc["features"] = []
    projects = db.query("SELECT * FROM projects WHERE active=1 ORDER BY sort, id")
    for p in projects:
        p["tags"] = "%s %s" % (p.get("category", ""), p.get("status", ""))
    return {
        "s": s,
        "services": services,
        "featured_services": [x for x in services if x.get("featured")][:6],
        "projects": projects,
        "featured_projects": [x for x in projects if x.get("featured")][:6],
        "team": db.query("SELECT * FROM team WHERE active=1 ORDER BY sort, id"),
        "testimonials": db.query("SELECT * FROM testimonials WHERE active=1 ORDER BY sort, id"),
        "jobs": db.query("SELECT * FROM jobs WHERE active=1 ORDER BY sort, id"),
        "faqs_all": db.query("SELECT * FROM faqs WHERE active=1 ORDER BY sort, id"),
    }


ROUTE_FOR_TEMPLATE = {
    "index.html": "/", "about.html": "/about.html", "service.html": "/service.html",
    "project.html": "/project.html", "contact.html": "/contact.html",
}


def render_public(template, extra, handler=None):
    ctx = site_context()
    ctx.update(extra or {})
    ctx["page"] = template

    route = ROUTE_FOR_TEMPLATE.get(template, "/" + template)
    s = ctx["s"]
    ctx["crumbs"] = CRUMBS.get(route, [])
    # only the FAQs assigned to this page, so the schema matches what is visible
    ctx["faqs"] = [f for f in ctx.get("faqs_all", []) if f.get("page") == route]
    ctx["meta"] = seo.meta_for(route, s)
    ctx["route"] = route
    ctx["jsonld"] = seo.graph(s, ctx["meta"], route, ctx)
    return env.get_template(template).render(**ctx)


# --------------------------------------------------------------- admin side
def _admin_render(name, ctx):
    return env_admin.get_template(name).render(**ctx)


def _require_login(handler):
    sess = handler.session()
    if not sess:
        handler.redirect("/admin/login")
        return None
    return sess


def _check_csrf(handler, sess, fields):
    token = fields.get("csrf", "")
    if not token or token != sess["csrf"]:
        handler._send(403, "<h1>403 - Invalid or expired form token</h1>"
                           "<p><a href='/admin'>Back to admin</a></p>")
        return False
    return True


def _flash_redirect(handler, path, msg=None, kind="ok"):
    if msg:
        from urllib.parse import quote
        path += ("&" if "?" in path else "?") + "m=%s&k=%s" % (quote(msg), kind)
    handler.redirect(path)


def _coerce(section, fields, files):
    """Build the column->value map for an insert/update."""
    cfg = SECTIONS[section]
    data = {}
    for col in cfg["fields"]:
        if col in ("active", "featured"):
            data[col] = 1 if fields.get(col) in ("1", "on", "true") else 0
        elif col in ("sort", "rating"):
            try:
                data[col] = int(fields.get(col) or 0)
            except ValueError:
                data[col] = 0
        elif col == "features":
            lines = [l.strip() for l in (fields.get("features") or "").splitlines() if l.strip()]
            data[col] = json.dumps(lines)
        else:
            data[col] = (fields.get(col) or "").strip()

    # image upload wins over the typed path
    up = files.get("image_file")
    if up and up[1]:
        data["image"] = core.save_image(up[0], up[1])
    return data


def admin_router(handler, path):
    method = handler.command
    qs = core.parse_qs(urlsplit_query(handler.path))

    # ---- login ----------------------------------------------------------
    if path == "/admin/login":
        if method == "GET":
            if handler.session():
                return handler.redirect("/admin")
            return handler._send(200, _admin_render("login.html", {"error": qs.get("e", "")}))
        fields, _ = core.parse_body(handler)
        ip = handler.client_ip
        if core.rate_limited(ip):
            return handler._send(429, _admin_render(
                "login.html", {"error": "Too many attempts. Wait five minutes."}))
        email = (fields.get("email") or "").strip().lower()
        user = db.query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user or not core.verify_password(fields.get("password") or "", user["pw_hash"]):
            core.record_attempt(ip)
            return handler._send(401, _admin_render(
                "login.html", {"error": "Incorrect email or password."}))
        core.clear_attempts(ip)
        token, _csrf = core.create_session(user["id"])
        cookie = "%s=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d%s" % (
            core.SESSION_COOKIE, token, core.SESSION_DAYS * 86400,
            "; Secure" if core.SECURE_COOKIES else "")
        return handler.redirect("/admin", {"Set-Cookie": cookie})

    if path == "/admin/logout":
        core.destroy_session(handler.cookies().get(core.SESSION_COOKIE))
        expire = "%s=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0" % core.SESSION_COOKIE
        return handler.redirect("/admin/login", {"Set-Cookie": expire})

    # ---- everything below needs a session -------------------------------
    sess = _require_login(handler)
    if not sess:
        return

    base_ctx = {
        "user": sess,
        "csrf": sess["csrf"],
        "sections": SECTIONS,
        "counts": db.counts(),
        "msg": qs.get("m", ""),
        "kind": qs.get("k", "ok"),
    }

    # dashboard
    if path in ("/admin", "/admin/"):
        base_ctx["active"] = "dashboard"
        return handler._send(200, _admin_render("dashboard.html", base_ctx))

    # site content / settings
    if path == "/admin/content":
        if method == "POST":
            fields, files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return
            for _group, rows in SETTING_GROUPS:
                for key, _label, kind in rows:
                    if kind == "image":
                        up = files.get(key + "_file")
                        if up and up[1]:
                            db.set_setting(key, core.save_image(up[0], up[1]))
                            continue
                    if key in fields:
                        db.set_setting(key, fields[key].strip())
            return _flash_redirect(handler, "/admin/content", "Site content saved.")
        base_ctx.update({"active": "content", "groups": SETTING_GROUPS,
                         "values": db.get_settings()})
        return handler._send(200, _admin_render("content.html", base_ctx))

    # ---- SEO ------------------------------------------------------------
    if path == "/admin/seo":
        if method == "POST":
            fields, files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return
            for _group, rows in SEO_GROUPS:
                for key, _label, kind, _hint in rows:
                    if kind == "image":
                        up = files.get(key + "_file")
                        if up and up[1]:
                            db.set_setting(key, core.save_image(up[0], up[1]))
                            continue
                    if key in fields:
                        value = fields[key].strip()
                        if key == "seo_site_url":
                            value = value.rstrip("/")
                        db.set_setting(key, value)
            return _flash_redirect(handler, "/admin/seo", "SEO settings saved.")

        settings = db.get_settings()
        base_ctx.update({
            "active": "seo",
            "groups": SEO_GROUPS,
            "values": settings,
            "checks": seo.site_audit(settings),
            "pages": [dict(seo.page_seo_row(r), route=r) for r in seo.PUBLIC_PAGES],
        })
        return handler._send(200, _admin_render("seo.html", base_ctx))

    # per-page SEO editor
    if path == "/admin/seo/page":
        route = qs.get("route", "/")
        if route not in seo.PUBLIC_PAGES:
            return handler.not_found()

        if method == "POST":
            fields, _files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return
            data = {f: (fields.get(f) or "").strip() for f in PAGE_SEO_FIELDS}
            data["noindex"] = 1 if fields.get("noindex") in ("1", "on", "true") else 0
            data["nofollow"] = 1 if fields.get("nofollow") in ("1", "on", "true") else 0
            cols = list(data) + ["route", "updated_at"]
            db.execute(
                "INSERT INTO page_seo(%s) VALUES(%s) ON CONFLICT(route) DO UPDATE SET %s"
                % (",".join(cols), ",".join(["?"] * len(cols)),
                   ",".join("%s=excluded.%s" % (c, c) for c in cols if c != "route")),
                tuple(data.values()) + (route, db.query("SELECT datetime('now') d", one=True)["d"]),
            )
            return _flash_redirect(handler, "/admin/seo/page?route=" + route,
                                   "SEO for %s saved." % route)

        settings = db.get_settings()
        meta, warnings = seo.audit(route, settings)
        base_ctx.update({
            "active": "seo",
            "route": route,
            "row": seo.page_seo_row(route),
            "meta": meta,
            "warnings": warnings,
            "values": settings,
            "pages": seo.PUBLIC_PAGES,
            "limits": {"title": seo.TITLE_MAX, "desc": seo.DESC_MAX},
        })
        return handler._send(200, _admin_render("seo_page.html", base_ctx))

    # 301 redirects
    if path == "/admin/redirects":
        if method == "POST":
            fields, _files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return
            if fields.get("delete"):
                db.execute("DELETE FROM redirects WHERE id = ?", (fields["delete"],))
                return _flash_redirect(handler, "/admin/redirects", "Redirect removed.")
            src = (fields.get("from_path") or "").strip()
            dst = (fields.get("to_path") or "").strip()
            if not src.startswith("/") or not dst.startswith("/"):
                return _flash_redirect(handler, "/admin/redirects",
                                       "Both paths must start with /", "err")
            if src == dst:
                return _flash_redirect(handler, "/admin/redirects",
                                       "That redirect points at itself.", "err")
            if src in seo.PUBLIC_PAGES:
                return _flash_redirect(handler, "/admin/redirects",
                                       "%s is a real page - redirecting it would hide it." % src, "err")
            db.execute("INSERT INTO redirects(from_path,to_path) VALUES(?,?) "
                       "ON CONFLICT(from_path) DO UPDATE SET to_path = excluded.to_path",
                       (src, dst))
            return _flash_redirect(handler, "/admin/redirects", "Redirect saved.")

        base_ctx.update({"active": "seo",
                         "redirects": db.query("SELECT * FROM redirects ORDER BY from_path")})
        return handler._send(200, _admin_render("redirects.html", base_ctx))

    # media library
    if path == "/admin/media":
        if method == "POST":
            fields, files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return
            if fields.get("delete"):
                core.delete_image(fields["delete"])
                return _flash_redirect(handler, "/admin/media", "Image deleted.")
            up = files.get("image_file")
            if up and up[1]:
                try:
                    core.save_image(up[0], up[1])
                    return _flash_redirect(handler, "/admin/media", "Image uploaded.")
                except ValueError as exc:
                    return _flash_redirect(handler, "/admin/media", str(exc), "err")
            return _flash_redirect(handler, "/admin/media", "No file selected.", "err")
        base_ctx.update({"active": "media",
                         "media": db.query("SELECT * FROM media ORDER BY id DESC")})
        return handler._send(200, _admin_render("media.html", base_ctx))

    # section list / new / edit / delete
    parts = [p for p in path.split("/") if p]        # ['admin', <section>, <action?>]
    if len(parts) >= 2 and parts[1] in SECTIONS:
        section = parts[1]
        cfg = SECTIONS[section]
        action = parts[2] if len(parts) > 2 else "list"

        if method == "POST":
            fields, files = core.parse_body(handler)
            if not _check_csrf(handler, sess, fields):
                return

            if action == "delete":
                rid = int(fields.get("id") or 0)
                row = db.query("SELECT image FROM %s WHERE id=?" % cfg["table"], (rid,), one=True)
                if row and (row.get("image") or "").startswith("uploads/"):
                    core.delete_image(row["image"])
                db.execute("DELETE FROM %s WHERE id=?" % cfg["table"], (rid,))
                return _flash_redirect(handler, "/admin/%s" % section, "Item deleted.")

            try:
                data = _coerce(section, fields, files)
            except ValueError as exc:
                return _flash_redirect(handler, "/admin/%s" % section, str(exc), "err")

            title_col = "title" if "title" in cfg["fields"] else "name"
            if not data.get(title_col):
                return _flash_redirect(handler, "/admin/%s" % section,
                                       "A title or name is required.", "err")

            rid = int(fields.get("id") or 0)
            if rid:
                sets = ", ".join("%s=?" % c for c in data)
                db.execute("UPDATE %s SET %s WHERE id=?" % (cfg["table"], sets),
                           tuple(data.values()) + (rid,))
                note = "Changes saved."
            else:
                if "slug" in table_columns(cfg["table"]):
                    data["slug"] = unique_slug(cfg["table"], core.slugify(data[title_col]))
                cols = ", ".join(data)
                marks = ", ".join("?" * len(data))
                db.execute("INSERT INTO %s(%s) VALUES(%s)" % (cfg["table"], cols, marks),
                           tuple(data.values()))
                note = "Item added."
            return _flash_redirect(handler, "/admin/%s" % section, note)

        # GET
        if action == "new" or action == "edit":
            rid = int(qs.get("id") or 0)
            item = db.query("SELECT * FROM %s WHERE id=?" % cfg["table"], (rid,), one=True) if rid else None
            if item and "features" in item:
                try:
                    item["features"] = "\n".join(json.loads(item["features"] or "[]"))
                except Exception:
                    item["features"] = ""
            base_ctx.update({"active": section, "section": section, "cfg": cfg,
                             "item": item or {},
                             "media": db.query("SELECT * FROM media ORDER BY id DESC LIMIT 60")})
            return handler._send(200, _admin_render("form.html", base_ctx))

        rows = db.query("SELECT * FROM %s ORDER BY %s" % (cfg["table"], cfg["order"]))
        base_ctx.update({"active": section, "section": section, "cfg": cfg, "rows": rows})
        return handler._send(200, _admin_render("list.html", base_ctx))

    return handler.not_found()


# --------------------------------------------------------------- helpers
_col_cache = {}


def table_columns(table):
    if table not in _col_cache:
        _col_cache[table] = [r["name"] for r in db.query("PRAGMA table_info(%s)" % table)]
    return _col_cache[table]


def unique_slug(table, base):
    slug, n = base, 2
    while db.query("SELECT 1 FROM %s WHERE slug=?" % table, (slug,), one=True):
        slug = "%s-%d" % (base, n)
        n += 1
    return slug


def urlsplit_query(url):
    from urllib.parse import urlsplit as u
    return u(url).query
