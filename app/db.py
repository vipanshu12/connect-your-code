"""SQLite schema, connection handling and first-run seed data.

Stdlib only. The database file lives at data/site.db and is created on first
run. Seed content mirrors what the static pages shipped with, so the site looks
identical the moment the CMS takes over.
"""
import json
import os
import sqlite3
import threading

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, "data")
DB_PATH = os.path.join(DATA_DIR, "site.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

_local = threading.local()

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  email      TEXT    NOT NULL UNIQUE,
  name       TEXT    NOT NULL DEFAULT '',
  pw_hash    TEXT    NOT NULL,
  role       TEXT    NOT NULL DEFAULT 'admin',
  created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT    PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  csrf       TEXT    NOT NULL,
  expires_at TEXT    NOT NULL,
  created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS services (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  slug        TEXT    NOT NULL UNIQUE,
  title       TEXT    NOT NULL,
  description TEXT    NOT NULL DEFAULT '',
  icon        TEXT    NOT NULL DEFAULT '',
  image       TEXT    NOT NULL DEFAULT '',
  features    TEXT    NOT NULL DEFAULT '[]',
  sort        INTEGER NOT NULL DEFAULT 0,
  active      INTEGER NOT NULL DEFAULT 1,
  featured    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS projects (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  slug        TEXT    NOT NULL UNIQUE,
  title       TEXT    NOT NULL,
  location    TEXT    NOT NULL DEFAULT '',
  category    TEXT    NOT NULL DEFAULT 'residential',
  status      TEXT    NOT NULL DEFAULT 'completed',
  completion  TEXT    NOT NULL DEFAULT '',
  description TEXT    NOT NULL DEFAULT '',
  image       TEXT    NOT NULL DEFAULT '',
  sort        INTEGER NOT NULL DEFAULT 0,
  active      INTEGER NOT NULL DEFAULT 1,
  featured    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS team (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  name     TEXT    NOT NULL,
  role     TEXT    NOT NULL DEFAULT '',
  bio      TEXT    NOT NULL DEFAULT '',
  image    TEXT    NOT NULL DEFAULT '',
  linkedin TEXT    NOT NULL DEFAULT '',
  email    TEXT    NOT NULL DEFAULT '',
  sort     INTEGER NOT NULL DEFAULT 0,
  active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS testimonials (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  name    TEXT    NOT NULL,
  company TEXT    NOT NULL DEFAULT '',
  quote   TEXT    NOT NULL DEFAULT '',
  rating  INTEGER NOT NULL DEFAULT 5,
  image   TEXT    NOT NULL DEFAULT '',
  sort    INTEGER NOT NULL DEFAULT 0,
  active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS jobs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT    NOT NULL,
  location    TEXT    NOT NULL DEFAULT '',
  experience  TEXT    NOT NULL DEFAULT '',
  employment  TEXT    NOT NULL DEFAULT 'Full time',
  description TEXT    NOT NULL DEFAULT '',
  sort        INTEGER NOT NULL DEFAULT 0,
  active      INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  filename   TEXT NOT NULL,
  path       TEXT NOT NULL,
  width      INTEGER NOT NULL DEFAULT 0,
  height     INTEGER NOT NULL DEFAULT 0,
  bytes      INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Per-page SEO overrides. A row here beats the global defaults in settings;
-- blank columns fall back rather than blanking the tag out.
CREATE TABLE IF NOT EXISTS page_seo (
  route       TEXT PRIMARY KEY,
  title       TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  keyword     TEXT NOT NULL DEFAULT '',
  og_title    TEXT NOT NULL DEFAULT '',
  og_desc     TEXT NOT NULL DEFAULT '',
  og_image    TEXT NOT NULL DEFAULT '',
  canonical   TEXT NOT NULL DEFAULT '',
  noindex     INTEGER NOT NULL DEFAULT 0,
  nofollow    INTEGER NOT NULL DEFAULT 0,
  changefreq  TEXT NOT NULL DEFAULT 'monthly',
  priority    TEXT NOT NULL DEFAULT '0.7',
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 301s, so a renamed slug does not drop the ranking it already earned.
CREATE TABLE IF NOT EXISTS redirects (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  from_path  TEXT NOT NULL UNIQUE,
  to_path    TEXT NOT NULL,
  hits       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS faqs (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT    NOT NULL DEFAULT '',
  answer   TEXT    NOT NULL DEFAULT '',
  page     TEXT    NOT NULL DEFAULT '/contact.html',
  sort     INTEGER NOT NULL DEFAULT 0,
  active   INTEGER NOT NULL DEFAULT 1
);
"""

DEFAULT_SETTINGS = {
    "site_name": "Sharma Interior Construction",
    "tagline": "We Build Landmarks That Last Generations",
    "hero_heading": "We Build <em>Landmarks</em><br>That Last Generations",
    "hero_text": "From residential towers to industrial plants and public infrastructure - Sharma Interior Construction delivers projects on time, on budget and to specification, with safety built into every stage.",
    "hero_image": "homeback.jpg",
    "about_heading": "A Contractor Built On Engineering Discipline",
    "about_text": "Founded on a simple principle - do the work properly the first time - Sharma Interior Construction has grown into a full-service contractor delivering across residential, commercial, industrial and infrastructure sectors.",
    "about_image": "cc.jpg",
    "mission": "To deliver construction that performs for decades - built to specification, handed over on programme, and priced without games.",
    "vision": "To be the contractor clients call first because the last project went right, not because we were the cheapest bid on the table.",
    "values": "Safety before schedule. Accuracy before speed. Straight answers before comfortable ones. Ownership of our mistakes.",
    "stat_years": "10",
    "stat_projects": "1500",
    "stat_clients": "790",
    "stat_workforce": "450",
    "phone": "+91 98765 43210",
    "phone_alt": "+91 11 4567 8900",
    "email": "info@sharmaconstruction.com",
    "email_careers": "careers@sharmaconstruction.com",
    "address": "123 Main Street, Tughlakabad Institutional Area, New Delhi 110062, India",
    "hours": "Mon - Sat, 9:00 AM - 6:00 PM",
    "facebook": "https://www.facebook.com/",
    "instagram": "https://www.instagram.com/",
    "linkedin": "https://www.linkedin.com/",
    "whatsapp": "https://wa.me/919876543210",
    "seo_title": "Sharma Interior Construction | Building & Infrastructure Contractors",
    "seo_description": "Sharma Interior Construction delivers residential, commercial, industrial and infrastructure projects across India. 10+ years, 1500+ completed projects.",

    # --- SEO -----------------------------------------------------------
    # seo_site_url is the single most important setting here: canonical URLs,
    # sitemap entries, JSON-LD @id values and og:url are all built from it.
    # Absolute URLs are required by Google - a relative canonical is ignored.
    "seo_site_url": "https://sharmaconstruction.com",
    "seo_default_image": "homeback.jpg",
    "seo_keywords": "construction company, building contractor, residential construction, commercial construction, industrial construction, civil contractor Delhi NCR",
    "seo_title_suffix": " | Sharma Construction",
    "seo_verification": "",          # Google Search Console meta content
    "seo_bing_verification": "",
    "seo_twitter_handle": "",
    "seo_noindex_site": "0",         # kill switch while the site is staging

    # --- analytics (blank = tag not emitted) ---------------------------
    "ga_measurement_id": "",         # G-XXXXXXXXXX
    "gtm_id": "",                    # GTM-XXXXXXX

    # --- local SEO / NAP -----------------------------------------------
    # These feed LocalBusiness schema. They must match the Google Business
    # Profile character for character - inconsistent NAP is the single most
    # common reason local rankings stall.
    "biz_legal_name": "Sharma Interior Construction",
    "biz_street": "123 Main Street, Tughlakabad Institutional Area",
    "biz_city": "New Delhi",
    "biz_state": "Delhi",
    "biz_postal": "110062",
    "biz_country": "IN",
    "biz_lat": "28.5135",
    "biz_lng": "77.2430",
    "biz_price_range": "$$",
    "biz_founded": "2015",
    "biz_areas": "New Delhi, Gurugram, Noida, Faridabad, Ghaziabad, Greater Noida",
    "biz_hours_spec": "Mo-Sa 09:00-18:00",
    "biz_profile_url": "",           # Google Business Profile link
    "footer_text": "A full-service construction contractor delivering residential, commercial, industrial and infrastructure projects across India.",
    "map_embed": "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3505.871796286783!2d77.2429713242177!3d28.513504689478324!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce174a3adccd3%3A0xcea21e67b7cdb14b!2sNew%20Delhi!5e0!3m2!1sen!2sin!4v1742616755822!5m2!1sen!2sin",
}

SEED_SERVICES = [
    ("building", "Building Construction", "Complete structures from foundation to finish - RCC frame, masonry, waterproofing, services and finishes under one contract.", "", "images/service-1.png", ["Turnkey design-and-build option", "Structural and finishing packages", "Single point of accountability"], 1),
    ("residential", "Residential Construction", "Villas, apartment blocks and housing developments built for the way people actually live in them.", "", "images/service-2.png", ["Independent villas and duplexes", "Multi-storey apartment blocks", "Gated community development"], 1),
    ("commercial", "Commercial Construction", "Offices, retail and hospitality built around your opening date and your operating hours.", "", "images/service-3.png", ["Office towers and business parks", "Retail and showroom builds", "Phased works in occupied buildings"], 1),
    ("industrial", "Industrial Construction", "Factories, warehouses and process facilities engineered for heavy loads and hard use.", "", "images/service-4.png", ["Pre-engineered steel buildings", "Heavy-duty industrial flooring", "Plant and utility coordination"], 1),
    ("civil", "Civil Construction", "Earthworks, foundations, retaining structures and the civil scope that everything else depends on.", "", "images/service-5.png", ["Excavation and ground improvement", "Piling and deep foundations", "Retaining walls and drainage"], 1),
    ("infrastructure", "Infrastructure Development", "Roads, external services and site development delivered to public-sector specification.", "", "images/service-6.png", ["Internal roads and pavements", "Stormwater and sewerage networks", "Site grading and external works"], 1),
    ("renovation", "Renovation & Remodelling", "Structural repair, extension and modernisation of buildings already in service.", "", "images/service-7.png", ["Structural strengthening and repair", "Facade and roof replacement", "Change-of-use conversions"], 0),
    ("interior", "Interior Construction", "Fit-out that is detailed to be built, not just rendered - joinery, services, finishes and handover.", "", "images/service-8.png", ["Corporate and retail fit-out", "Bespoke joinery and millwork", "MEP coordination and testing"], 0),
    ("pm", "Project Management", "Independent programme, cost and contract management when you are running your own trades.", "ri-node-tree", "", ["Programme and milestone control", "Cost reporting and forecasting", "Contract and variation administration"], 0),
    ("engineering", "Engineering Services", "Design review, temporary works and value engineering by our in-house structural team.", "ri-compasses-2-line", "", ["Structural design and review", "Temporary works design", "Value engineering studies"], 0),
    ("maintenance", "Maintenance Services", "Planned and reactive maintenance that keeps completed assets performing.", "ri-tools-fill", "", ["Annual maintenance contracts", "Reactive repair callout", "Facade and waterproofing upkeep"], 0),
]

SEED_PROJECTS = [
    ("skyline-residency", "Skyline Residency", "Pune, Maharashtra", "residential", "completed", "March 2025", "A 14-storey residential tower with 96 units, twin basements and a podium amenity deck. Delivered three weeks ahead of programme.", "images/project-1.jpg", 1),
    ("meridian-corporate-park", "Meridian Corporate Park", "Bengaluru, Karnataka", "commercial", "completed", "November 2024", "Two office blocks totalling 180,000 sq ft including core-and-shell, facade and full MEP coordination.", "images/project-2.jpg", 1),
    ("northgate-logistics-hub", "Northgate Logistics Hub", "Delhi NCR", "industrial", "ongoing", "Est. August 2026", "A 240,000 sq ft pre-engineered warehouse with heavy-duty flooring, 42 dock levellers and an on-site substation.", "images/project-3.jpg", 1),
    ("grand-central-mall", "Grand Central Mall", "Gurugram, Haryana", "commercial", "completed", "July 2024", "Retail development with three trading levels, a food court and structured parking for 600 vehicles.", "images/project-4.jpg", 1),
    ("riverfront-development", "Riverfront Development", "Ranchi, Jharkhand", "infrastructure", "ongoing", "Est. December 2026", "Public riverfront works covering embankment protection, stormwater drainage, internal roads and landscaping.", "images/project-5.jpg", 1),
    ("harbour-view-villas", "Harbour View Villas", "Chennai, Tamil Nadu", "residential", "completed", "January 2025", "Eighteen independent villas with private plots, a shared clubhouse and full external infrastructure.", "images/project-6.jpg", 1),
    ("aster-medical-centre", "Aster Medical Centre", "New Delhi", "commercial", "completed", "September 2024", "A four-storey diagnostic and outpatient facility built to healthcare finish and hygiene standards.", "cc.jpg", 0),
    ("westline-industrial-estate", "Westline Industrial Estate", "Chennai, Tamil Nadu", "industrial", "ongoing", "Est. May 2026", "Site development and civil works for six industrial plots including roads, drainage and utility corridors.", "site.jpg", 0),
    ("civic-plaza-redevelopment", "Civic Plaza Redevelopment", "Gurugram, Haryana", "infrastructure", "completed", "February 2024", "Public plaza rebuild with new paving, underground services diversion, lighting and street furniture.", "mall.jpg", 0),
]

SEED_TEAM = [
    ("Vikram Sharma", "Founder & Managing Director", "Civil engineer with 22 years across high-rise residential and public infrastructure.", "images/pic-1.png"),
    ("Anita Deshpande", "Director, Operations", "Runs programme, procurement and subcontractor performance across all live sites.", "images/pic-2.png"),
    ("Rohit Nair", "Head of Engineering", "Structural design review, temporary works and value engineering.", "images/pic-3.png"),
    ("Meera Iyer", "Head of Quality & HSE", "Owns the inspection regime, testing schedule and site safety audits.", "images/pic-4.png"),
    ("Sanjay Gupta", "Senior Project Manager", "Delivers commercial and industrial packages from mobilisation to handover.", "images/pic-5.png"),
    ("Kavita Reddy", "Head of Interiors", "Leads fit-out delivery, finishes coordination and client sign-off.", "images/pic-6.png"),
]

SEED_TESTIMONIALS = [
    ("Rajesh Kumar", "MD, Meridian Developers", "They handed over three weeks early and the snag list was under twenty items across forty thousand square feet. That is unusual in this industry.", 5, "images/pic-1.png"),
    ("Priya Sharma", "Project Head, Northgate Logistics", "What impressed us was the documentation. Every pour, every test certificate, every variation was traceable. The audit was painless.", 5, "images/pic-2.png"),
    ("Anil Mehta", "Director, Harbour Estates", "We have used four contractors in ten years. Sharma is the only one we did not have to chase. The site was clean and the crew was disciplined.", 5, "images/pic-3.png"),
    ("Sunita Verma", "CFO, Grand Central Retail", "Costing was transparent from day one. No inflated variations at the end, which is exactly why we have given them our next two sites.", 5, "images/pic-4.png"),
]

SEED_JOBS = [
    ("Site Engineer (Civil)", "New Delhi NCR", "3-6 years", "Full time", "Day-to-day execution, setting out, quality checks and subcontractor coordination on an active residential site. Diploma or B.E. in Civil Engineering required."),
    ("Project Manager", "Bengaluru", "8-12 years", "Full time", "Own programme, cost and client reporting for a commercial package. Proven record delivering 100,000+ sq ft builds end to end."),
    ("Safety Officer (HSE)", "Chennai", "2-5 years", "Full time", "Run inductions, toolbox talks, permits to work and incident reporting across two industrial sites. Recognised safety qualification required."),
    ("Quantity Surveyor", "New Delhi NCR", "4-8 years", "Full time", "Prepare BOQs, valuations and variation assessments. Strong measurement skills and familiarity with standard methods of measurement."),
    ("Interior Site Supervisor", "Gurugram", "3-5 years", "Full time", "Supervise joinery, finishes and MEP coordination on corporate fit-out projects. Snagging and handover experience essential."),
]


SEED_FAQS = [
    ("What types of construction projects do you take on?",
     "We deliver residential, commercial, industrial and infrastructure projects - "
     "from independent villas and apartment blocks through to factories, warehouses "
     "and public works. Any of these can be run as a turnkey design-and-build "
     "contract or as a structure-only or finishing package.",
     "/contact.html"),
    ("Which areas do you work in?",
     "Our primary service area is Delhi NCR - New Delhi, Gurugram, Noida, Faridabad, "
     "Ghaziabad and Greater Noida. We take projects elsewhere in India where the "
     "scope justifies mobilising a site team.",
     "/contact.html"),
    ("How long does a construction project usually take?",
     "An independent villa typically runs 8-14 months from foundation to handover; "
     "an apartment block or commercial fit-out runs 14-30 months depending on floor "
     "count and services. We issue a programme with milestone dates before work "
     "starts and report against it every month.",
     "/contact.html"),
    ("How do you price a project?",
     "We quote against a measured bill of quantities, not a rate per square foot. "
     "That takes longer to prepare but means the number you approve is the number "
     "you pay, barring scope changes you sign off yourself.",
     "/contact.html"),
    ("Are you licensed and insured?",
     "Yes. We carry contractor's all-risk and third-party liability cover on every "
     "site, and our supervisors hold current safety certification. Documentation is "
     "available on request before contract signature.",
     "/contact.html"),
    ("Do you handle approvals and drawings?",
     "On turnkey contracts, yes - structural design, MEP coordination and the "
     "municipal approval trail are included. On structure-only contracts we build "
     "to the consultant's drawings and coordinate with their team.",
     "/service.html"),
]

# Route-level SEO. Titles stay under 60 characters and descriptions under 160
# so Google shows them whole rather than truncating mid-sentence.
SEED_PAGE_SEO = [
    ("/", "Construction Company in Delhi NCR",
     "Sharma Interior Construction builds residential, commercial and industrial "
     "projects across Delhi NCR. 10+ years, 1500+ projects delivered on programme.",
     "construction company delhi ncr", "weekly", "1.0"),
    ("/about.html", "About Our Construction Company",
     "Ten years of building across Delhi NCR. Meet the engineers and site teams "
     "behind 1500+ completed residential, commercial and infrastructure projects.",
     "construction company about", "monthly", "0.7"),
    ("/service.html", "Construction Services in Delhi NCR",
     "Building construction, residential and commercial projects, industrial sheds, "
     "interior fit-out, renovation and infrastructure works across Delhi NCR.",
     "construction services delhi ncr", "weekly", "0.9"),
    ("/project.html", "Our Construction Projects",
     "Browse completed and ongoing construction projects across Delhi NCR - "
     "residential towers, commercial builds, industrial plants and public works.",
     "construction projects delhi", "weekly", "0.8"),
    ("/contact.html", "Contact Us and Get a Free Quote",
     "Talk to our estimating team about your construction project. Free measured "
     "quote, site visit across Delhi NCR, and a written programme before work starts.",
     "construction company contact quote", "monthly", "0.7"),
]


def connect():
    """One connection per thread; the HTTP server is threaded."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


def query(sql, args=(), one=False):
    cur = connect().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def execute(sql, args=()):
    conn = connect()
    cur = conn.execute(sql, args)
    conn.commit()
    last = cur.lastrowid
    cur.close()
    return last


def get_settings():
    return {r["key"]: r["value"] for r in query("SELECT key, value FROM settings")}


def set_setting(key, value):
    execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def init(seed=True):
    """Create tables and, on a genuinely empty database, load seed content."""
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()

    if not seed:
        return

    if not query("SELECT 1 FROM settings LIMIT 1"):
        for k, v in DEFAULT_SETTINGS.items():
            set_setting(k, v)

    if not query("SELECT 1 FROM services LIMIT 1"):
        for i, (slug, title, desc, icon, img, feats, feat) in enumerate(SEED_SERVICES):
            execute(
                "INSERT INTO services(slug,title,description,icon,image,features,sort,featured)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (slug, title, desc, icon, img, json.dumps(feats), i, feat),
            )

    if not query("SELECT 1 FROM projects LIMIT 1"):
        for i, (slug, title, loc, cat, st, comp, desc, img, feat) in enumerate(SEED_PROJECTS):
            execute(
                "INSERT INTO projects(slug,title,location,category,status,completion,"
                "description,image,sort,featured) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (slug, title, loc, cat, st, comp, desc, img, i, feat),
            )

    if not query("SELECT 1 FROM team LIMIT 1"):
        for i, (name, role, bio, img) in enumerate(SEED_TEAM):
            execute(
                "INSERT INTO team(name,role,bio,image,linkedin,email,sort)"
                " VALUES(?,?,?,?,?,?,?)",
                (name, role, bio, img, "https://www.linkedin.com/", "info@sharmaconstruction.com", i),
            )

    if not query("SELECT 1 FROM testimonials LIMIT 1"):
        for i, (name, company, quote, rating, img) in enumerate(SEED_TESTIMONIALS):
            execute(
                "INSERT INTO testimonials(name,company,quote,rating,image,sort)"
                " VALUES(?,?,?,?,?,?)",
                (name, company, quote, rating, img, i),
            )

    if not query("SELECT 1 FROM jobs LIMIT 1"):
        for i, (title, loc, exp, emp, desc) in enumerate(SEED_JOBS):
            execute(
                "INSERT INTO jobs(title,location,experience,employment,description,sort)"
                " VALUES(?,?,?,?,?,?)",
                (title, loc, exp, emp, desc, i),
            )

    if not query("SELECT 1 FROM faqs LIMIT 1"):
        for i, (q, a, page) in enumerate(SEED_FAQS):
            execute("INSERT INTO faqs(question,answer,page,sort) VALUES(?,?,?,?)",
                    (q, a, page, i))

    if not query("SELECT 1 FROM page_seo LIMIT 1"):
        for route, title, desc, kw, freq, pri in SEED_PAGE_SEO:
            execute(
                "INSERT INTO page_seo(route,title,description,keyword,changefreq,priority)"
                " VALUES(?,?,?,?,?,?)",
                (route, title, desc, kw, freq, pri),
            )

    # Adding a settings key to DEFAULT_SETTINGS must reach databases that were
    # created before it existed - the seed block above only fires when the
    # table is completely empty.
    existing = set(get_settings())
    for k, v in DEFAULT_SETTINGS.items():
        if k not in existing:
            set_setting(k, v)


def counts():
    """Dashboard tiles."""
    def n(sql, args=()):
        row = query(sql, args, one=True)
        return list(row.values())[0] if row else 0

    return {
        "projects": n("SELECT COUNT(*) c FROM projects"),
        "projects_completed": n("SELECT COUNT(*) c FROM projects WHERE status='completed'"),
        "projects_ongoing": n("SELECT COUNT(*) c FROM projects WHERE status='ongoing'"),
        "services": n("SELECT COUNT(*) c FROM services"),
        "team": n("SELECT COUNT(*) c FROM team"),
        "testimonials": n("SELECT COUNT(*) c FROM testimonials"),
        "jobs": n("SELECT COUNT(*) c FROM jobs WHERE active=1"),
        "media": n("SELECT COUNT(*) c FROM media"),
    }
