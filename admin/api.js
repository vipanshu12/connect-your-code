// Supabase client - auth, PostgREST and Storage over plain fetch.
//
// Deliberately no SDK: this project has never had a build step, and the three
// endpoints below are the whole surface the admin needs.
import { SUPABASE_URL, SUPABASE_ANON_KEY, MEDIA_BUCKET } from "./config.js";

const SESSION_KEY = "sharma.session";

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

/* ------------------------------------------------------------------ session */

let session = null;
try {
  session = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
} catch (_) {
  session = null;
}

function store(next) {
  session = next;
  if (next) localStorage.setItem(SESSION_KEY, JSON.stringify(next));
  else localStorage.removeItem(SESSION_KEY);
}

export function currentUser() {
  return session && session.user ? session.user : null;
}

export function isSignedIn() {
  return !!(session && session.access_token);
}

async function readError(res) {
  let body = null;
  try {
    body = await res.json();
  } catch (_) {
    /* non-JSON error page */
  }
  const msg =
    (body && (body.message || body.error_description || body.error || body.hint)) ||
    `${res.status} ${res.statusText}`;
  return new ApiError(msg, res.status, body);
}

export async function signIn(email, password) {
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw await readError(res);
  const data = await res.json();
  store({
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    // Renew a minute early so a request never races the expiry.
    expires_at: Date.now() + (data.expires_in - 60) * 1000,
    user: data.user,
  });
  return data.user;
}

export async function signOut() {
  if (session && session.access_token) {
    try {
      await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
        method: "POST",
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${session.access_token}`,
        },
      });
    } catch (_) {
      /* the local session is cleared regardless */
    }
  }
  store(null);
}

async function refresh() {
  if (!session || !session.refresh_token) return false;
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });
  if (!res.ok) {
    store(null);
    return false;
  }
  const data = await res.json();
  store({
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + (data.expires_in - 60) * 1000,
    user: data.user || session.user,
  });
  return true;
}

async function authHeaders(extra) {
  if (session && session.expires_at && Date.now() > session.expires_at) {
    await refresh();
  }
  return Object.assign(
    {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${
        session && session.access_token ? session.access_token : SUPABASE_ANON_KEY
      }`,
    },
    extra || {}
  );
}

/* ------------------------------------------------------------------ tables */

// "sort, id" (the Python admin's ORDER BY) -> "sort.asc,id.asc"
function orderParam(order) {
  return order
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const bits = part.split(/\s+/);
      const dir = (bits[1] || "asc").toLowerCase() === "desc" ? "desc" : "asc";
      return `${bits[0]}.${dir}`;
    })
    .join(",");
}

async function rest(path, options) {
  const opts = options || {};
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method: opts.method || "GET",
    headers: await authHeaders(
      Object.assign(
        opts.body ? { "Content-Type": "application/json" } : {},
        opts.headers || {}
      )
    ),
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw await readError(res);
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export function list(table, order) {
  const q = order ? `?select=*&order=${orderParam(order)}` : "?select=*";
  return rest(`${table}${q}`);
}

export async function insert(table, row) {
  const rows = await rest(table, {
    method: "POST",
    body: row,
    headers: { Prefer: "return=representation" },
  });
  return rows && rows[0];
}

export async function update(table, id, patch, key) {
  const col = key || "id";
  const rows = await rest(`${table}?${col}=eq.${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: patch,
    headers: { Prefer: "return=representation" },
  });
  return rows && rows[0];
}

export function remove(table, id, key) {
  const col = key || "id";
  return rest(`${table}?${col}=eq.${encodeURIComponent(id)}`, { method: "DELETE" });
}

/* ---------------------------------------------------------------- settings */

// settings is a key/value table; the UI edits it as one flat object.
export async function getSettings() {
  const rows = await rest("settings?select=key,value");
  const out = {};
  (rows || []).forEach((r) => {
    out[r.key] = r.value;
  });
  return out;
}

export function saveSettings(map) {
  const rows = Object.keys(map).map((key) => ({ key, value: map[key] ?? "" }));
  if (!rows.length) return Promise.resolve(null);
  return rest("settings", {
    method: "POST",
    body: rows,
    headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
  });
}

export function savePageSeo(row) {
  return rest("page_seo", {
    method: "POST",
    body: [row],
    headers: { Prefer: "resolution=merge-duplicates,return=minimal" },
  });
}

/* ----------------------------------------------------------------- storage */

export async function uploadImage(file) {
  // Random prefix so re-uploading the same filename can never serve a stale
  // cached image, matching what core.py did with secrets.token_hex.
  const safe = file.name.replace(/[^a-zA-Z0-9._-]/g, "-").toLowerCase();
  const name = `${Math.random().toString(16).slice(2, 10)}-${safe}`;
  const res = await fetch(
    `${SUPABASE_URL}/storage/v1/object/${MEDIA_BUCKET}/${name}`,
    {
      method: "POST",
      headers: await authHeaders({ "x-upsert": "false" }),
      body: file,
    }
  );
  if (!res.ok) throw await readError(res);
  return publicUrl(name);
}

export function publicUrl(name) {
  return `${SUPABASE_URL}/storage/v1/object/public/${MEDIA_BUCKET}/${name}`;
}

export async function listMedia() {
  const res = await fetch(`${SUPABASE_URL}/storage/v1/object/list/${MEDIA_BUCKET}`, {
    method: "POST",
    headers: await authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ prefix: "", limit: 500, sortBy: { column: "created_at", order: "desc" } }),
  });
  if (!res.ok) throw await readError(res);
  const items = await res.json();
  return (items || [])
    .filter((it) => it.name && it.id !== null)
    .map((it) => ({
      name: it.name,
      url: publicUrl(it.name),
      bytes: (it.metadata && it.metadata.size) || 0,
      created: it.created_at || "",
    }));
}

export async function deleteMedia(name) {
  const res = await fetch(
    `${SUPABASE_URL}/storage/v1/object/${MEDIA_BUCKET}/${name}`,
    { method: "DELETE", headers: await authHeaders() }
  );
  if (!res.ok) throw await readError(res);
}

export function configured() {
  return !!(SUPABASE_URL && SUPABASE_ANON_KEY);
}
