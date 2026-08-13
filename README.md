# Sharma Interior Construction

Construction company website with a small admin panel. Python standard library
plus Jinja2 and Pillow — **no `pip install` needed** on this machine.

## Run it

```bash
python3 server.py              # http://localhost:8000
python3 server.py 8080         # different port
python3 server.py --lan        # reachable from phones on your wifi
```

- Website → <http://localhost:8000>
- Admin → <http://localhost:8000/admin>

## Admin login

Create your own account — no credentials are shipped in this repo:

```bash
python3 server.py --create-admin
```

Run the same command again at any time to reset the password; doing so also
revokes every existing session.

> An earlier revision of this file listed a test login in plain text. It is in
> the git history, so treat that password as burned — if it was ever set on a
> live instance, rotate it with the command above.

Run that again any time to reset a password — it also revokes every existing
session for that user.

## What the admin can edit

| Screen | Controls |
|---|---|
| **Site Content** | hero heading/text/image, about section, mission, vision, values, all four statistics, phone, email, address, hours, map, social links, footer text, SEO title & description |
| **Services** | add / edit / delete, icon or image, bullet features, order, show-hide, feature on home page |
| **Projects** | add / edit / delete, image, location, category, status, completion date, description, order, featured |
| **Team** | add / edit / delete, photo, role, bio, LinkedIn, email |
| **Testimonials** | add / edit / delete, client photo, company, quote, star rating |
| **Careers** | add / edit / delete job openings |
| **Images** | upload, preview, copy path, delete |

Changes appear on the live site immediately — there is no publish step.

## Layout

```
server.py              entry point, routing, static files
app/db.py              SQLite schema + seed content
app/core.py            passwords, sessions, uploads, form parsing
app/views.py           public rendering + admin panel
templates/public/      the website (Jinja)
templates/admin/       the admin panel (Jinja)
assets/css/styles.css  single stylesheet for the public site
assets/js/main.js      nav, filters, modal, slider, validation
static/admin/          admin panel css + js
data/site.db           your content (SQLite)
data/uploads/          uploaded images
_originals/            pre-redesign backups — never served, safe to delete
```

## Editing the design

`assets/css/styles.css` is the only public stylesheet. The palette lives at the
top:

```css
--navy:#0f172a;   /* primary   - headings, header, footer, dark bands */
--navy-700:#1e293b;
--slate:#475569;  /* body text */
--muted:#64748b;
--line:#e2e8f0;   /* borders */
--bg:#f8fafc;     /* page background */
--white:#ffffff;  /* cards */

--accent:#f97316;        /* CTAs, active nav, icons, statistics */
--accent-hover:#ea580c;
--accent-600:#c2410c;    /* the only orange safe for body-sized text */
```

Spacing runs on one scale (`--s-1` … `--s-8`, 4→64px); use those rather than
literal pixels so sections, cards and buttons stay in rhythm.

**Contrast note.** White text on `--accent` (`#f97316`) measures 2.8:1, under
the 4.5:1 WCAG AA minimum — it is the specified brand orange, kept as given.
Two one-line fixes if you want the CTA to pass:

```css
--accent: #c2410c;                        /* darker orange, white text  5.2:1 */
.btn--primary { color: var(--navy); }     /* keep the orange, dark text 6.4:1 */
```

Every other pairing on the site clears AA.

## Security notes

What is actually implemented:

- PBKDF2-HMAC-SHA256 password hashing, 240,000 iterations, random 16-byte salt
- Session tokens are random 32-byte values; only their SHA-256 hash is stored
- Cookies are `HttpOnly` + `SameSite=Strict`
- CSRF token required on every state-changing admin request
- Login rate-limited to 8 attempts per IP per 5 minutes
- Uploads are validated by decoding the image, not by trusting the filename
- Only `assets/`, `images/`, `static/` and `data/uploads/` are web-reachable —
  `app/`, `templates/` and `data/site.db` are not

Before putting this on the public internet:

1. **Put HTTPS in front of it** (nginx or Caddy as a reverse proxy), then set
   `SECURE_COOKIES=1` so the session cookie is marked `Secure`.
2. Change the admin password.
3. Back up `data/site.db` — it is your entire content.

## Deploying

This needs a host that runs Python (a small VPS, Render, Railway, PythonAnywhere).
It will **not** work on GitHub Pages or Netlify, which serve static files only.

If you later want static hosting instead, the pre-CMS static pages are preserved
in `_originals/static-pages/`.
