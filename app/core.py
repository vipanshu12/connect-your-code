"""Auth, request helpers and media handling. Stdlib + Pillow only.

Security notes (what is real here, and what is not):
  * Passwords are PBKDF2-HMAC-SHA256, 240k iterations, 16-byte random salt.
  * Session tokens are 32 random bytes; only their SHA-256 hash is stored, so a
    database leak does not hand over live sessions.
  * Cookies are HttpOnly + SameSite=Strict. Set SECURE_COOKIES=1 behind HTTPS.
  * Every state-changing admin request requires a CSRF token bound to the session.
  * Login is rate-limited per IP to slow credential stuffing.
There is no protection here against a compromised host, and this is not meant
to sit on the public internet without HTTPS in front of it.
"""
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import time
from email.parser import BytesParser
from email.policy import default as email_policy

from . import db

SESSION_COOKIE = "sid"
SESSION_DAYS = 14
PBKDF2_ROUNDS = 240_000
MAX_UPLOAD = 12 * 1024 * 1024          # 12 MB
IMAGE_MAX_W = 1920
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "0") == "1"


# ----------------------------------------------------------------- passwords
def hash_password(password):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return "pbkdf2_sha256$%d$%s$%s" % (PBKDF2_ROUNDS, salt.hex(), dk.hex())


def verify_password(password, stored):
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ----------------------------------------------------------------- sessions
def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    db.execute(
        "INSERT INTO sessions(token_hash, user_id, csrf, expires_at) "
        "VALUES(?,?,?, datetime('now', ?))",
        (_token_hash(token), user_id, csrf, "+%d days" % SESSION_DAYS),
    )
    return token, csrf


def load_session(token):
    if not token:
        return None
    row = db.query(
        "SELECT s.token_hash, s.csrf, s.expires_at, u.id, u.email, u.name, u.role "
        "FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > datetime('now')",
        (_token_hash(token),),
        one=True,
    )
    return row


def destroy_session(token):
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def purge_expired():
    db.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")


# ----------------------------------------------------------------- rate limit
_attempts = {}


def rate_limited(ip, limit=8, window=300):
    now = time.time()
    hits = [t for t in _attempts.get(ip, []) if now - t < window]
    _attempts[ip] = hits
    return len(hits) >= limit


def record_attempt(ip):
    _attempts.setdefault(ip, []).append(time.time())


def clear_attempts(ip):
    _attempts.pop(ip, None)


# ----------------------------------------------------------------- requests
def parse_cookies(header):
    out = {}
    for part in (header or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def parse_qs(query):
    out = {}
    for part in (query or "").split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        out[unquote_plus(k)] = unquote_plus(v)
    return out


def unquote_plus(s):
    from urllib.parse import unquote_plus as u
    return u(s)


def parse_body(handler):
    """Returns (fields, files). Handles urlencoded and multipart/form-data."""
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}, {}
    if length > MAX_UPLOAD:
        raise ValueError("Payload too large")

    ctype = handler.headers.get("Content-Type", "")
    raw = handler.rfile.read(length)

    if ctype.startswith("application/json"):
        try:
            return json.loads(raw.decode("utf-8")), {}
        except Exception:
            return {}, {}

    if ctype.startswith("application/x-www-form-urlencoded"):
        return parse_qs(raw.decode("utf-8", "replace")), {}

    if ctype.startswith("multipart/form-data"):
        # Rebuild a MIME document so email.parser can do the heavy lifting;
        # cgi.FieldStorage is deprecated and gone in 3.13.
        head = b"Content-Type: " + ctype.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n"
        msg = BytesParser(policy=email_policy).parsebytes(head + raw)
        fields, files = {}, {}
        if msg.is_multipart():
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if not name:
                    continue
                filename = part.get_filename()
                payload = part.get_payload(decode=True) or b""
                if filename:
                    files[name] = (filename, payload)
                else:
                    fields[name] = payload.decode("utf-8", "replace")
        return fields, files

    return {}, {}


# ----------------------------------------------------------------- media
_SAFE = re.compile(r"[^a-z0-9._-]+")


def safe_name(filename):
    base = os.path.basename(filename or "").lower().strip()
    root, ext = os.path.splitext(base)
    root = _SAFE.sub("-", root).strip("-") or "image"
    ext = ext if ext in ALLOWED_IMAGE else ".jpg"
    return root[:60] + ext


def save_image(filename, blob):
    """Validate, downscale and store an upload. Returns a web path or raises."""
    from PIL import Image, ImageOps

    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE:
        raise ValueError("Only JPG, PNG, WEBP or GIF images are allowed.")
    if len(blob) > MAX_UPLOAD:
        raise ValueError("Image must be under 12 MB.")

    # Decode before trusting the extension - a renamed .exe fails here.
    try:
        probe = Image.open(io.BytesIO(blob))
        probe.verify()
    except Exception:
        raise ValueError("That file is not a readable image.")

    im = Image.open(io.BytesIO(blob))
    im = ImageOps.exif_transpose(im)
    is_png = ext == ".png" or im.mode in ("RGBA", "LA", "P")

    if im.width > IMAGE_MAX_W:
        im = im.resize((IMAGE_MAX_W, round(im.height * IMAGE_MAX_W / im.width)),
                       Image.LANCZOS)

    name = safe_name(filename)
    root, _ = os.path.splitext(name)
    out_ext = ".png" if is_png else ".jpg"
    unique = "%s-%s%s" % (root, secrets.token_hex(4), out_ext)
    abs_path = os.path.join(db.UPLOAD_DIR, unique)

    if is_png:
        im.convert("RGBA").save(abs_path, "PNG", optimize=True)
    else:
        im.convert("RGB").save(abs_path, "JPEG", quality=82, optimize=True,
                               progressive=True)

    web_path = "uploads/" + unique
    db.execute(
        "INSERT INTO media(filename, path, width, height, bytes) VALUES(?,?,?,?,?)",
        (unique, web_path, im.width, im.height, os.path.getsize(abs_path)),
    )
    return web_path


def delete_image(web_path):
    """Only ever deletes inside data/uploads - never site images."""
    if not web_path or not web_path.startswith("uploads/"):
        return False
    name = os.path.basename(web_path)
    abs_path = os.path.join(db.UPLOAD_DIR, name)
    if os.path.commonpath([os.path.abspath(abs_path), db.UPLOAD_DIR]) != db.UPLOAD_DIR:
        return False
    if os.path.exists(abs_path):
        os.remove(abs_path)
    db.execute("DELETE FROM media WHERE path = ?", (web_path,))
    return True


# ----------------------------------------------------------------- misc
def slugify(text, fallback="item"):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:70] or fallback


def b64(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")
