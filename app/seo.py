"""SEO: per-page metadata, JSON-LD structured data, sitemap and robots.txt.

Everything here is generated from the database, so the admin panel is the only
place anyone needs to touch. Two rules run through the whole module:

  * Absolute URLs only. Google ignores a relative canonical, and a relative
    og:image will not render as a share card. Every URL goes through abs_url().
  * A blank admin field falls back, it does not blank the tag out. An empty
    meta description is worse than a repeated one.

Stdlib only.
"""
import json
import re
from datetime import date

from . import db

# Routes that exist as real pages, with their sitemap defaults. Anything not
# listed here never reaches the sitemap, which is how /admin stays out of it.
PUBLIC_PAGES = ["/", "/about.html", "/service.html", "/project.html", "/contact.html"]

TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 70, 160


# --------------------------------------------------------------------- helpers
def site_url(s):
    return (s.get("seo_site_url") or "").rstrip("/")


def abs_url(s, path):
    """Absolute URL for a path or already-absolute URL. Never returns a
    protocol-relative or bare-relative string."""
    if not path:
        return ""
    path = str(path).strip()
    if path.startswith(("http://", "https://")):
        return path
    base = site_url(s)
    if not path.startswith("/"):
        path = "/" + path
    return base + path if base else path


def clean(text, limit=None):
    """Collapse whitespace, drop tags, optionally clip on a word boundary."""
    txt = re.sub(r"<[^>]+>", " ", str(text or ""))
    txt = re.sub(r"\s+", " ", txt).strip()
    if limit and len(txt) > limit:
        txt = txt[:limit].rsplit(" ", 1)[0].rstrip(",.;:-") + "..."
    return txt


def page_seo_row(route):
    return db.query("SELECT * FROM page_seo WHERE route = ?", (route,), one=True) or {}


# ------------------------------------------------------------------- metadata
def meta_for(route, s, extra=None):
    """Resolve the head metadata for one route.

    Precedence: explicit per-render values -> page_seo row -> global settings.
    """
    row = page_seo_row(route)
    extra = extra or {}

    suffix = s.get("seo_title_suffix") or ""
    raw_title = extra.get("title") or row.get("title") or ""
    if raw_title:
        # the suffix is part of the brand, but never doubled up
        title = raw_title if raw_title.endswith(suffix.strip()) else raw_title + suffix
    else:
        title = s.get("seo_title") or s.get("site_name") or ""

    desc = clean(extra.get("description") or row.get("description")
                 or s.get("seo_description") or "", DESC_MAX + 40)

    image = extra.get("image") or row.get("og_image") or s.get("seo_default_image") or ""
    canonical = row.get("canonical") or extra.get("canonical") or route
    if canonical == "/index.html":
        canonical = "/"

    # A site-wide noindex switch beats any per-page setting - it exists so a
    # staging copy cannot leak into the index by accident.
    site_off = str(s.get("seo_noindex_site") or "0") == "1"
    noindex = site_off or bool(row.get("noindex"))
    nofollow = bool(row.get("nofollow"))

    return {
        "title": clean(title),
        "description": desc,
        "keyword": row.get("keyword") or "",
        "keywords": s.get("seo_keywords") or "",
        "canonical": abs_url(s, canonical),
        "image": abs_url(s, image),
        "og_title": clean(row.get("og_title") or "") or clean(title),
        "og_desc": clean(row.get("og_desc") or "") or desc,
        "robots": ("noindex" if noindex else "index") + "," + ("nofollow" if nofollow else "follow"),
        "twitter": s.get("seo_twitter_handle") or "",
        "verification": s.get("seo_verification") or "",
        "bing_verification": s.get("seo_bing_verification") or "",
        "ga": s.get("ga_measurement_id") or "",
        "gtm": s.get("gtm_id") or "",
    }


# ------------------------------------------------------------- structured data
def _postal_address(s):
    return {
        "@type": "PostalAddress",
        "streetAddress": s.get("biz_street", ""),
        "addressLocality": s.get("biz_city", ""),
        "addressRegion": s.get("biz_state", ""),
        "postalCode": s.get("biz_postal", ""),
        "addressCountry": s.get("biz_country", "IN"),
    }


def _social(s):
    return [s.get(k) for k in ("facebook", "instagram", "linkedin", "biz_profile_url")
            if s.get(k)]


def _hours(s):
    """'Mo-Sa 09:00-18:00' -> openingHoursSpecification. Returns [] if the
    admin typed something this cannot parse, rather than emitting junk."""
    spec = (s.get("biz_hours_spec") or "").strip()
    m = re.match(r"^([A-Za-z]{2})\s*-\s*([A-Za-z]{2})\s+(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", spec)
    if not m:
        return []
    order = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    names = {"Mo": "Monday", "Tu": "Tuesday", "We": "Wednesday", "Th": "Thursday",
             "Fr": "Friday", "Sa": "Saturday", "Su": "Sunday"}
    a, b, open_t, close_t = m.group(1).title(), m.group(2).title(), m.group(3), m.group(4)
    if a not in order or b not in order:
        return []
    days = order[order.index(a):order.index(b) + 1]
    return [{
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": [names[d] for d in days],
        "opens": open_t,
        "closes": close_t,
    }]


def organization(s):
    base = site_url(s)
    node = {
        "@type": ["Organization", "GeneralContractor", "HomeAndConstructionBusiness"],
        "@id": base + "/#organization",
        "name": s.get("biz_legal_name") or s.get("site_name", ""),
        "url": base or None,
        "logo": abs_url(s, "logo-white.png"),
        "image": abs_url(s, s.get("seo_default_image", "")),
        "description": clean(s.get("seo_description", "")),
        "telephone": s.get("phone", ""),
        "email": s.get("email", ""),
        "address": _postal_address(s),
        "priceRange": s.get("biz_price_range", ""),
    }
    if s.get("biz_founded"):
        node["foundingDate"] = s["biz_founded"]
    if _social(s):
        node["sameAs"] = _social(s)
    return {k: v for k, v in node.items() if v}


def local_business(s):
    base = site_url(s)
    areas = [a.strip() for a in (s.get("biz_areas") or "").split(",") if a.strip()]
    node = {
        "@type": "GeneralContractor",
        "@id": base + "/#localbusiness",
        "name": s.get("site_name", ""),
        "url": base or None,
        "image": abs_url(s, s.get("seo_default_image", "")),
        "telephone": s.get("phone", ""),
        "email": s.get("email", ""),
        "address": _postal_address(s),
        "priceRange": s.get("biz_price_range", ""),
        "parentOrganization": {"@id": base + "/#organization"},
    }
    try:
        node["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(s.get("biz_lat")),
            "longitude": float(s.get("biz_lng")),
        }
    except (TypeError, ValueError):
        pass
    if areas:
        node["areaServed"] = [{"@type": "City", "name": a} for a in areas]
    hours = _hours(s)
    if hours:
        node["openingHoursSpecification"] = hours
    if _social(s):
        node["sameAs"] = _social(s)
    return {k: v for k, v in node.items() if v}


def website(s):
    base = site_url(s)
    return {
        "@type": "WebSite",
        "@id": base + "/#website",
        "url": base,
        "name": s.get("site_name", ""),
        "publisher": {"@id": base + "/#organization"},
        "inLanguage": "en-IN",
    }


def webpage(s, meta, route):
    base = site_url(s)
    return {
        "@type": "WebPage",
        "@id": meta["canonical"] + "#webpage",
        "url": meta["canonical"],
        "name": meta["title"],
        "description": meta["description"],
        "isPartOf": {"@id": base + "/#website"},
        "about": {"@id": base + "/#organization"},
        "inLanguage": "en-IN",
    }


def breadcrumbs(s, trail):
    """trail: [(name, path), ...] - the same list the visible crumbs render."""
    if not trail:
        return None
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name,
             "item": abs_url(s, path)}
            for i, (name, path) in enumerate(trail)
        ],
    }


def service_nodes(s, services):
    base = site_url(s)
    return [{
        "@type": "Service",
        "@id": "%s/service.html#%s" % (base, svc.get("slug") or svc["id"]),
        "name": svc.get("title", ""),
        "description": clean(svc.get("description", ""), 300),
        "serviceType": svc.get("title", ""),
        "provider": {"@id": base + "/#organization"},
        "areaServed": [a.strip() for a in (s.get("biz_areas") or "").split(",") if a.strip()],
    } for svc in services]


def project_nodes(s, projects):
    """Projects are creative works, not products - there is no price or
    availability, and marking them up as Offers would be a lie."""
    out = []
    for p in projects:
        node = {
            "@type": "CreativeWork",
            "name": p.get("title", ""),
            "description": clean(p.get("description", ""), 300),
            "creator": {"@id": site_url(s) + "/#organization"},
        }
        if p.get("image"):
            node["image"] = abs_url(s, p["image"])
        if p.get("location"):
            node["locationCreated"] = {"@type": "Place", "name": p["location"]}
        if p.get("completion"):
            node["dateCreated"] = str(p["completion"])
        out.append(node)
    return out


def job_nodes(s, jobs):
    """JobPosting needs datePosted and validThrough or Google drops it."""
    out = []
    today = date.today()
    valid = date(today.year + 1, today.month, today.day).isoformat()
    for j in jobs:
        out.append({
            "@type": "JobPosting",
            "title": j.get("title", ""),
            "description": clean(j.get("description", "")) or j.get("title", ""),
            "datePosted": str(j.get("created_at", ""))[:10] or today.isoformat(),
            "validThrough": valid,
            "employmentType": (j.get("employment") or "Full time").upper().replace(" ", "_"),
            "hiringOrganization": {"@id": site_url(s) + "/#organization"},
            "jobLocation": {"@type": "Place", "address": _postal_address(s)},
            "experienceRequirements": j.get("experience", ""),
        })
    return out


def faq_node(faqs):
    """Only emit FAQPage when there are real question/answer pairs on the page.
    Marking up an FAQ that a visitor cannot see is a manual-action risk."""
    pairs = [f for f in faqs if f.get("question") and f.get("answer")]
    if not pairs:
        return None
    return {
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": clean(f["question"]),
            "acceptedAnswer": {"@type": "Answer", "text": clean(f["answer"])},
        } for f in pairs],
    }


def graph(s, meta, route, ctx):
    """One @graph per page. A single script tag with cross-referenced @ids
    beats several disconnected blocks - it lets Google resolve the entity."""
    nodes = [organization(s), local_business(s), website(s), webpage(s, meta, route)]

    crumbs = ctx.get("crumbs")
    if crumbs:
        bc = breadcrumbs(s, crumbs)
        if bc:
            nodes.append(bc)

    if route == "/service.html":
        nodes += service_nodes(s, ctx.get("services") or [])
    if route == "/project.html":
        nodes += project_nodes(s, ctx.get("projects") or [])
    if route == "/contact.html":
        nodes += job_nodes(s, ctx.get("jobs") or [])

    faq = faq_node(ctx.get("faqs") or [])
    if faq:
        nodes.append(faq)

    return json.dumps({"@context": "https://schema.org", "@graph": nodes},
                      ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------- sitemap.xml
def sitemap_xml():
    """Built from page_seo, so adding a page in the admin publishes it here.
    Admin, login and asset routes are structurally unable to appear: only
    routes in PUBLIC_PAGES are considered."""
    s = db.get_settings()
    rows = {r["route"]: r for r in db.query("SELECT * FROM page_seo")}

    # Newest content change, as a sane lastmod for pages with no record of
    # their own. Only page_seo carries a timestamp - services and projects
    # were created without one.
    latest = db.query("SELECT MAX(updated_at) d FROM page_seo", one=True) or {}
    fallback = str(latest.get("d") or date.today().isoformat())[:10]

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for route in PUBLIC_PAGES:
        row = rows.get(route, {})
        if row.get("noindex"):
            continue                      # never advertise a page you excluded
        lastmod = str(row.get("updated_at") or fallback)[:10]
        out.append("  <url>")
        out.append("    <loc>%s</loc>" % _xml(abs_url(s, route)))
        out.append("    <lastmod>%s</lastmod>" % _xml(lastmod))
        out.append("    <changefreq>%s</changefreq>" % _xml(row.get("changefreq") or "monthly"))
        out.append("    <priority>%s</priority>" % _xml(row.get("priority") or "0.7"))
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def _xml(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ----------------------------------------------------------------- robots.txt
def robots_txt():
    s = db.get_settings()
    lines = ["User-agent: *"]
    if str(s.get("seo_noindex_site") or "0") == "1":
        # staging switch: refuse everything rather than half-blocking
        lines += ["Disallow: /", "", "# Site-wide noindex is ON in admin > SEO."]
        return "\n".join(lines) + "\n"

    lines += [
        "Allow: /",
        "",
        "# Private routes - these must never be crawled or indexed.",
        "Disallow: /admin",
        "Disallow: /admin/",
        "Disallow: /login",
        "Disallow: /dashboard",
        "Disallow: /uploads/",
        "Disallow: /_originals/",
        "",
        "# Crawl budget: assets do not need to be indexed on their own.",
        "Disallow: /*?m=",
        "Disallow: /*?k=",
    ]
    base = site_url(s)
    if base:
        lines += ["", "Sitemap: %s/sitemap.xml" % base]
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------- admin warnings
def audit(route, s):
    """What the admin SEO screen shows as warnings. Deliberately specific:
    'Title is 74 characters (max 60)' is actionable, 'Title too long' is not."""
    meta = meta_for(route, s)
    row = page_seo_row(route)
    warn = []

    t, d = meta["title"], meta["description"]
    if not t:
        warn.append(("error", "No title. Google will invent one from the page text."))
    elif len(t) > TITLE_MAX:
        warn.append(("warn", "Title is %d characters (max %d) - Google will truncate it." % (len(t), TITLE_MAX)))
    elif len(t) < TITLE_MIN:
        warn.append(("warn", "Title is only %d characters - room for more detail (aim %d-%d)." % (len(t), TITLE_MIN, TITLE_MAX)))

    if not d:
        warn.append(("error", "No meta description. Google will pull a random sentence instead."))
    elif len(d) > DESC_MAX:
        warn.append(("warn", "Description is %d characters (max %d) - it will be cut off." % (len(d), DESC_MAX)))
    elif len(d) < DESC_MIN:
        warn.append(("warn", "Description is only %d characters - aim for %d-%d." % (len(d), DESC_MIN, DESC_MAX)))

    kw = (row.get("keyword") or "").strip().lower()
    if kw:
        if kw not in t.lower():
            warn.append(("warn", 'Focus keyword "%s" is not in the title.' % kw))
        if kw not in d.lower():
            warn.append(("warn", 'Focus keyword "%s" is not in the description.' % kw))
    else:
        warn.append(("info", "No focus keyword set for this page."))

    if row.get("noindex"):
        warn.append(("error", "This page is set to noindex - it will be removed from Google."))
    if not site_url(s):
        warn.append(("error", "Site URL is empty. Canonical tags, the sitemap and all "
                              "structured data need it to produce absolute URLs."))

    # duplicate detection across every page
    others = db.query("SELECT route, title, description FROM page_seo WHERE route != ?", (route,))
    for o in others:
        if o["title"] and row.get("title") and o["title"].strip() == row["title"].strip():
            warn.append(("error", "Title is identical to %s." % o["route"]))
        if o["description"] and row.get("description") and o["description"].strip() == row["description"].strip():
            warn.append(("error", "Description is identical to %s." % o["route"]))

    if not warn:
        warn.append(("ok", "No issues found on this page."))
    return meta, warn


def site_audit(s):
    """The dashboard-level checklist."""
    checks = []

    def add(ok, label, detail=""):
        checks.append({"ok": bool(ok), "label": label, "detail": detail})

    base = site_url(s)
    add(bool(base), "Site URL set", base or "Required for canonical URLs and the sitemap")
    add(base.startswith("https://") if base else False, "HTTPS canonical URL",
        "" if base.startswith("https://") else "Set an https:// site URL before launch")
    add(bool(s.get("seo_verification")), "Search Console verification tag",
        "" if s.get("seo_verification") else "Paste the meta content value from Search Console")
    add(str(s.get("seo_noindex_site") or "0") != "1", "Site is indexable",
        "Site-wide noindex is currently ON" if str(s.get("seo_noindex_site") or "0") == "1" else "")
    add(bool(s.get("seo_default_image")), "Default social share image")
    add(bool(s.get("biz_street") and s.get("biz_city") and s.get("phone")),
        "NAP complete (name, address, phone)")
    add(bool(s.get("biz_lat") and s.get("biz_lng")), "Map coordinates set")
    add(bool(_hours(s)), "Business hours parse for schema",
        "" if _hours(s) else 'Use the exact format "Mo-Sa 09:00-18:00"')
    add(bool(s.get("biz_areas")), "Service areas listed")
    add(bool(db.query("SELECT 1 FROM faqs WHERE active=1 LIMIT 1")), "FAQ content for FAQ schema")

    pages = db.query("SELECT route, title, description, noindex FROM page_seo")
    add(len(pages) >= len(PUBLIC_PAGES), "Every page has an SEO record",
        "%d of %d" % (len(pages), len(PUBLIC_PAGES)))
    add(all(p["title"] for p in pages), "All pages have titles")
    add(all(p["description"] for p in pages), "All pages have descriptions")
    titles = [p["title"].strip() for p in pages if p["title"]]
    add(len(titles) == len(set(titles)), "No duplicate titles")
    descs = [p["description"].strip() for p in pages if p["description"]]
    add(len(descs) == len(set(descs)), "No duplicate descriptions")
    add(bool(s.get("ga_measurement_id") or s.get("gtm_id")), "Analytics configured",
        "" if (s.get("ga_measurement_id") or s.get("gtm_id")) else "Optional - add GA4 or GTM ID")

    return checks
