// Admin panel - Supabase edition.
//
// Replaces the server-rendered Jinja admin. Every screen is driven by
// schema.js, which is generated from app/views.py, so the fields here are the
// fields the Python admin edited.
import { SCHEMA } from "./schema.js";
import { DEPLOY_HOOK } from "./config.js";
import * as api from "./api.js";

const app = document.getElementById("app");
const toasts = document.getElementById("toasts");

/* ------------------------------------------------------------------- utils */

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === false) return;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2), v);
    } else node.setAttribute(k, v === true ? "" : v);
  });
  (Array.isArray(children) ? children : children ? [children] : [])
    .filter(Boolean)
    .forEach((c) => node.append(c.nodeType ? c : document.createTextNode(c)));
  return node;
}

function toast(message, kind) {
  const node = el("div", { class: `toast ${kind || "ok"}`, text: message });
  toasts.append(node);
  setTimeout(() => {
    node.classList.add("out");
    setTimeout(() => node.remove(), 300);
  }, kind === "err" ? 6000 : 3000);
}

function confirmDialog(message) {
  return new Promise((resolve) => {
    const close = (answer) => {
      scrim.remove();
      resolve(answer);
    };
    const card = el("div", { class: "dialog" }, [
      el("p", { text: message }),
      el("div", { class: "row end" }, [
        el("button", { class: "btn ghost", onclick: () => close(false) }, "Cancel"),
        el("button", { class: "btn danger", onclick: () => close(true) }, "Delete"),
      ]),
    ]);
    const scrim = el("div", {
      class: "scrim",
      onclick: (e) => { if (e.target === scrim) close(false); },
    }, card);
    document.body.append(scrim);
  });
}

// Anything the user typed goes through here before it reaches innerHTML.
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// Publishing is a separate step from saving, so the client needs to be able to
// tell at a glance whether what they are looking at is live yet.
function lastPublished() {
  const at = Number(localStorage.getItem("sharma.published") || 0);
  if (!at) return "Not published from here yet";
  const mins = Math.floor((Date.now() - at) / 60000);
  if (mins < 1) return "Published just now";
  if (mins < 60) return `Published ${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Published ${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  return `Published ${Math.floor(hrs / 24)} day(s) ago`;
}

function truncate(value, max) {
  const s = String(value ?? "");
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

/* ------------------------------------------------------------------- login */

function renderLogin(message) {
  app.className = "login-wrap";
  app.replaceChildren(
    el("form", {
      class: "login-card",
      onsubmit: async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector("button");
        const email = e.target.email.value.trim();
        const password = e.target.password.value;
        btn.disabled = true;
        btn.textContent = "Signing in…";
        try {
          await api.signIn(email, password);
          location.hash = "#/content";
          renderApp();
        } catch (err) {
          btn.disabled = false;
          btn.textContent = "Sign in";
          renderLogin(
            err.status === 400 ? "Wrong email or password." : err.message
          );
        }
      },
    }, [
      el("h1", { text: "Sharma Construction" }),
      el("p", { class: "muted", text: "Sign in to manage the website." }),
      message ? el("div", { class: "alert err", text: message }) : null,
      el("label", {}, [
        el("span", { text: "Email" }),
        el("input", { name: "email", type: "email", required: true, autocomplete: "username" }),
      ]),
      el("label", {}, [
        el("span", { text: "Password" }),
        el("input", { name: "password", type: "password", required: true, autocomplete: "current-password" }),
      ]),
      el("button", { class: "btn primary", type: "submit" }, "Sign in"),
    ])
  );
}

/* -------------------------------------------------------------------- nav */

const NAV = [
  { route: "content", label: "Site Content", icon: "⚙" },
  ...Object.entries(SCHEMA.sections).map(([key, cfg]) => ({
    route: key, label: cfg.label, icon: "■",
  })),
  { route: "seo", label: "SEO", icon: "↑" },
  { route: "media", label: "Media", icon: "▣" },
  { route: "redirects", label: "Redirects", icon: "→" },
];

function currentRoute() {
  const hash = (location.hash || "#/content").replace(/^#\//, "");
  const [route, ...rest] = hash.split("/");
  return { route: route || "content", rest };
}

function renderApp() {
  if (!api.isSignedIn()) return renderLogin();

  const { route } = currentRoute();
  app.className = "shell";

  const side = el("aside", { class: "side" }, [
    el("div", { class: "brand", text: "Sharma Admin" }),
    el("nav", {}, NAV.map((item) =>
      el("a", {
        class: "nav-item" + (item.route === route ? " is-active" : ""),
        href: `#/${item.route}`,
      }, [el("span", { class: "ico", text: item.icon }), item.label])
    )),
    el("div", { class: "side-foot" }, [
      DEPLOY_HOOK ? el("button", {
        class: "btn primary publish",
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          btn.textContent = "Publishing…";
          try {
            // Vercel's deploy hooks accept a bodyless POST and return a job id.
            const res = await fetch(DEPLOY_HOOK, { method: "POST" });
            if (!res.ok) throw new Error(`Vercel returned ${res.status}`);
            toast("Publishing - the live site updates in about a minute.");
            localStorage.setItem("sharma.published", String(Date.now()));
          } catch (err) {
            toast(`Could not publish: ${err.message}`, "err");
          }
          btn.disabled = false;
          btn.textContent = "Publish";
          renderApp();
        },
      }, "Publish") : null,
      DEPLOY_HOOK ? el("span", { class: "published", text: lastPublished() }) : null,
      el("a", { class: "nav-item", href: "/", target: "_blank" },
        "View site ↗"),
      el("button", {
        class: "nav-item as-button",
        onclick: async () => { await api.signOut(); renderLogin(); },
      }, "Sign out"),
    ]),
  ]);

  const main = el("main", { class: "main" }, el("div", { class: "loading", text: "Loading…" }));
  app.replaceChildren(side, main);
  renderRoute(main);
}

async function renderRoute(main) {
  const { route, rest } = currentRoute();
  try {
    if (route === "content") return await renderSettings(main, SCHEMA.settingGroups, "Site Content");
    if (route === "seo") return await renderSeo(main, rest);
    if (route === "media") return await renderMedia(main);
    if (route === "redirects") return await renderRedirects(main);
    if (SCHEMA.sections[route]) return await renderSection(main, route, rest);
    main.replaceChildren(el("div", { class: "panel", text: "Unknown screen." }));
  } catch (err) {
    main.replaceChildren(
      el("div", { class: "panel" }, [
        el("h2", { text: "Could not load this screen" }),
        el("p", { class: "muted", text: err.message }),
        err.status === 401 || err.status === 403
          ? el("p", { class: "muted", text: "Your session may have expired - sign out and back in." })
          : null,
      ])
    );
  }
}

/* --------------------------------------------------------------- form bits */

function fieldInput(field, value, onImagePick) {
  const common = { name: field.name, id: `f_${field.name}` };
  if (field.kind === "bool") {
    return el("input", Object.assign(common, {
      type: "checkbox", checked: !!value,
    }));
  }
  if (field.kind === "number") {
    return el("input", Object.assign(common, { type: "number", value: value ?? 0 }));
  }
  if (field.kind === "textarea") {
    const ta = el("textarea", Object.assign(common, { rows: 4 }));
    ta.value = value ?? "";
    return ta;
  }
  if (field.kind === "image") {
    const input = el("input", Object.assign(common, { type: "text", value: value ?? "" }));
    const preview = el("img", { class: "thumb", alt: "", src: value || "" });
    preview.style.display = value ? "" : "none";
    const wrap = el("div", { class: "image-field" }, [
      input,
      el("button", {
        class: "btn ghost small", type: "button",
        onclick: async () => {
          const picked = await pickMedia();
          if (picked) {
            input.value = picked;
            preview.src = picked;
            preview.style.display = "";
          }
        },
      }, "Choose…"),
      preview,
    ]);
    return wrap;
  }
  const input = el("input", Object.assign(common, { type: "text" }));
  input.value = value ?? "";
  return input;
}

function readField(form, field) {
  const node = form.querySelector(`[name="${field.name}"]`);
  if (!node) return undefined;
  if (field.kind === "bool") return node.checked;
  if (field.kind === "number") return Number(node.value || 0);
  return node.value;
}

/* ------------------------------------------------------- generic CRUD list */

async function renderSection(main, key, rest) {
  const cfg = SCHEMA.sections[key];
  const rows = await api.list(cfg.table, cfg.order);

  if (rest[0] === "edit" || rest[0] === "new") {
    const row = rest[0] === "new" ? {} : rows.find((r) => String(r.id) === rest[1]);
    return renderRecordForm(main, cfg, key, row || {});
  }

  const titleField = cfg.fields.find((f) =>
    ["title", "name", "question"].includes(f.name)) || cfg.fields[0];
  const secondary = cfg.fields.find((f) =>
    ["location", "role", "company", "page", "description"].includes(f.name));

  main.replaceChildren(
    el("header", { class: "topbar" }, [
      el("h1", { text: cfg.label }),
      el("a", { class: "btn primary", href: `#/${key}/new` }, `Add ${cfg.label.replace(/s$/, "")}`),
    ]),
    el("div", { class: "panel" }, rows.length
      ? el("table", { class: "grid" }, [
          el("thead", {}, el("tr", {}, [
            el("th", { text: titleField.label }),
            secondary ? el("th", { text: secondary.label }) : null,
            el("th", { text: "Order" }),
            el("th", { text: "Live" }),
            el("th", { text: "" }),
          ])),
          el("tbody", {}, rows.map((row) =>
            el("tr", {}, [
              el("td", {}, el("a", { href: `#/${key}/edit/${row.id}`, text: truncate(row[titleField.name], 60) })),
              secondary ? el("td", { class: "muted", text: truncate(row[secondary.name], 50) }) : null,
              el("td", { class: "muted", text: String(row.sort ?? "") }),
              el("td", {}, el("span", {
                class: "pill " + (row.active ? "on" : "off"),
                text: row.active ? "Live" : "Hidden",
              })),
              el("td", { class: "end" }, [
                el("a", { class: "btn ghost small", href: `#/${key}/edit/${row.id}` }, "Edit"),
                el("button", {
                  class: "btn danger small",
                  onclick: async () => {
                    if (!(await confirmDialog(`Delete "${row[titleField.name]}"? This cannot be undone.`))) return;
                    try {
                      await api.remove(cfg.table, row.id);
                      toast("Deleted.");
                      renderRoute(main);
                    } catch (err) { toast(err.message, "err"); }
                  },
                }, "Delete"),
              ]),
            ])
          )),
        ])
      : el("p", { class: "muted", text: `No ${cfg.label.toLowerCase()} yet.` })
    )
  );
}

function renderRecordForm(main, cfg, key, row) {
  const isNew = !row.id;
  const form = el("form", { class: "panel form", onsubmit: async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    const payload = {};
    cfg.fields.forEach((f) => {
      const v = readField(form, f);
      if (v !== undefined) payload[f.name] = v;
    });
    // slug is NOT NULL UNIQUE and the Python admin derived it from the title.
    if (isNew && ["services", "projects"].includes(cfg.table)) {
      payload.slug = (payload.title || "")
        .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
        || `item-${Date.now()}`;
    }
    try {
      if (isNew) await api.insert(cfg.table, payload);
      else await api.update(cfg.table, row.id, payload);
      toast("Saved.");
      location.hash = `#/${key}`;
    } catch (err) {
      btn.disabled = false;
      toast(err.message, "err");
    }
  } });

  cfg.fields.forEach((field) => {
    form.append(el("label", { class: field.kind === "bool" ? "check" : "" }, [
      el("span", { text: field.label }),
      fieldInput(field, row[field.name]),
    ]));
  });

  form.append(el("div", { class: "row end sticky-save" }, [
    el("a", { class: "btn ghost", href: `#/${key}` }, "Cancel"),
    el("button", { class: "btn primary", type: "submit" }, "Save"),
  ]));

  main.replaceChildren(
    el("header", { class: "topbar" }, [
      el("h1", { text: `${isNew ? "New" : "Edit"} ${cfg.label.replace(/s$/, "")}` }),
    ]),
    form
  );
}

/* ------------------------------------------------------- settings + SEO */

async function renderSettings(main, groups, heading) {
  const values = await api.getSettings();
  const form = el("form", { onsubmit: async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    const payload = {};
    groups.forEach((g) => g.fields.forEach((f) => {
      const v = readField(form, f);
      if (v !== undefined) payload[f.name] = String(v);
    }));
    try {
      await api.saveSettings(payload);
      toast("Saved.");
    } catch (err) { toast(err.message, "err"); }
    btn.disabled = false;
  } });

  groups.forEach((group) => {
    const panel = el("section", { class: "panel" }, el("h2", { text: group.title }));
    group.fields.forEach((field) => {
      panel.append(el("label", {}, [
        el("span", { text: field.label }),
        fieldInput(field, values[field.name]),
        field.help ? el("small", { class: "muted", text: field.help }) : null,
      ]));
    });
    form.append(panel);
  });

  form.append(el("div", { class: "row end sticky-save" },
    el("button", { class: "btn primary", type: "submit" }, "Save changes")));

  main.replaceChildren(el("header", { class: "topbar" }, el("h1", { text: heading })), form);
}

async function renderSeo(main, rest) {
  if (rest[0] === "page") return renderPageSeo(main);
  const wrap = el("div", {});
  await renderSettings(wrap, SCHEMA.seoGroups, "SEO");
  const header = wrap.querySelector(".topbar");
  header.append(el("a", { class: "btn ghost", href: "#/seo/page" }, "Per-page SEO"));
  main.replaceChildren(...wrap.childNodes);
}

async function renderPageSeo(main) {
  const rows = await api.list("page_seo", "route");
  const byRoute = {};
  rows.forEach((r) => { byRoute[r.route] = r; });

  const form = el("form", { onsubmit: async (e) => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    try {
      for (const route of SCHEMA.routes) {
        const row = { route };
        SCHEMA.pageSeoFields.forEach((name) => {
          const node = form.querySelector(`[name="${route}::${name}"]`);
          if (node) row[name] = node.value;
        });
        await api.savePageSeo(row);
      }
      toast("Saved.");
    } catch (err) { toast(err.message, "err"); }
    btn.disabled = false;
  } });

  SCHEMA.routes.forEach((route) => {
    const existing = byRoute[route] || {};
    const panel = el("section", { class: "panel" }, el("h2", { text: route }));
    SCHEMA.pageSeoFields.forEach((name) => {
      const long = ["description", "og_desc"].includes(name);
      const input = long
        ? el("textarea", { name: `${route}::${name}`, rows: 3 })
        : el("input", { name: `${route}::${name}`, type: "text" });
      input.value = existing[name] ?? "";
      panel.append(el("label", {}, [
        el("span", { text: name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) }),
        input,
      ]));
    });
    form.append(panel);
  });

  form.append(el("div", { class: "row end sticky-save" },
    el("button", { class: "btn primary", type: "submit" }, "Save all pages")));

  main.replaceChildren(
    el("header", { class: "topbar" }, [
      el("h1", { text: "Per-page SEO" }),
      el("a", { class: "btn ghost", href: "#/seo" }, "Back to SEO"),
    ]),
    form
  );
}

/* ------------------------------------------------------------------ media */

async function renderMedia(main) {
  const items = await api.listMedia();
  const grid = el("div", { class: "media-grid" }, items.map((item) =>
    el("figure", { class: "shot" }, [
      el("img", { src: item.url, alt: item.name, loading: "lazy" }),
      el("figcaption", {}, [
        el("span", { class: "muted", text: truncate(item.name, 28) }),
        el("div", { class: "row" }, [
          el("button", {
            class: "btn ghost small",
            onclick: () => {
              navigator.clipboard.writeText(item.url);
              toast("URL copied.");
            },
          }, "Copy URL"),
          el("button", {
            class: "btn danger small",
            onclick: async () => {
              if (!(await confirmDialog(`Delete ${item.name}?`))) return;
              try {
                await api.deleteMedia(item.name);
                toast("Deleted.");
                renderRoute(main);
              } catch (err) { toast(err.message, "err"); }
            },
          }, "Delete"),
        ]),
      ]),
    ])
  ));

  main.replaceChildren(
    el("header", { class: "topbar" }, [
      el("h1", { text: "Media" }),
      el("label", { class: "btn primary" }, [
        "Upload image",
        el("input", {
          type: "file", accept: "image/*", hidden: true,
          onchange: async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            toast("Uploading…");
            try {
              await api.uploadImage(file);
              toast("Uploaded.");
              renderRoute(main);
            } catch (err) { toast(err.message, "err"); }
          },
        }),
      ]),
    ]),
    el("div", { class: "panel" },
      items.length ? grid : el("p", { class: "muted", text: "No images yet." }))
  );
}

// Modal picker used by every image field.
function pickMedia() {
  return new Promise(async (resolve) => {
    const close = (value) => { scrim.remove(); resolve(value); };
    const body = el("div", { class: "loading", text: "Loading…" });
    const card = el("div", { class: "dialog wide" }, [
      el("div", { class: "row between" }, [
        el("h2", { text: "Choose an image" }),
        el("label", { class: "btn ghost small" }, [
          "Upload",
          el("input", {
            type: "file", accept: "image/*", hidden: true,
            onchange: async (e) => {
              const file = e.target.files[0];
              if (!file) return;
              try { close(await api.uploadImage(file)); }
              catch (err) { toast(err.message, "err"); }
            },
          }),
        ]),
      ]),
      body,
      el("div", { class: "row end" },
        el("button", { class: "btn ghost", onclick: () => close(null) }, "Cancel")),
    ]);
    const scrim = el("div", {
      class: "scrim",
      onclick: (e) => { if (e.target === scrim) close(null); },
    }, card);
    document.body.append(scrim);

    try {
      const items = await api.listMedia();
      body.replaceChildren(
        items.length
          ? el("div", { class: "media-grid pick" }, items.map((item) =>
              el("button", {
                class: "shot as-button", type: "button",
                onclick: () => close(item.url),
              }, el("img", { src: item.url, alt: item.name, loading: "lazy" }))))
          : el("p", { class: "muted", text: "No images yet - upload one." })
      );
    } catch (err) {
      body.replaceChildren(el("p", { class: "muted", text: err.message }));
    }
  });
}

/* -------------------------------------------------------------- redirects */

async function renderRedirects(main) {
  const rows = await api.list("redirects", "from_path");
  const form = el("form", { class: "row", onsubmit: async (e) => {
    e.preventDefault();
    try {
      await api.insert("redirects", {
        from_path: form.from_path.value.trim(),
        to_path: form.to_path.value.trim(),
      });
      toast("Added.");
      renderRoute(main);
    } catch (err) { toast(err.message, "err"); }
  } }, [
    el("input", { name: "from_path", placeholder: "/old-page.html", required: true }),
    el("input", { name: "to_path", placeholder: "/new-page.html", required: true }),
    el("button", { class: "btn primary", type: "submit" }, "Add"),
  ]);

  main.replaceChildren(
    el("header", { class: "topbar" }, el("h1", { text: "Redirects" })),
    el("div", { class: "panel" }, [
      el("p", { class: "muted", text:
        "Note: redirects need a server to issue them. On the static site these " +
        "must be added to dist/vercel.json instead - the build writes them there." }),
      form,
      rows.length ? el("table", { class: "grid" }, [
        el("thead", {}, el("tr", {}, [
          el("th", { text: "From" }), el("th", { text: "To" }), el("th", { text: "" }),
        ])),
        el("tbody", {}, rows.map((row) => el("tr", {}, [
          el("td", { text: row.from_path }),
          el("td", { text: row.to_path }),
          el("td", { class: "end" }, el("button", {
            class: "btn danger small",
            onclick: async () => {
              if (!(await confirmDialog(`Delete redirect ${row.from_path}?`))) return;
              await api.remove("redirects", row.id);
              toast("Deleted.");
              renderRoute(main);
            },
          }, "Delete")),
        ]))),
      ]) : null,
    ])
  );
}

/* ------------------------------------------------------------------- boot */

window.addEventListener("hashchange", () => {
  if (!api.isSignedIn()) return renderLogin();
  const main = app.querySelector(".main");
  if (main) {
    app.querySelectorAll(".nav-item").forEach((a) => {
      a.classList.toggle("is-active", a.getAttribute("href") === location.hash);
    });
    main.replaceChildren(el("div", { class: "loading", text: "Loading…" }));
    renderRoute(main);
  } else renderApp();
});

if (!api.configured()) {
  app.className = "login-wrap";
  app.replaceChildren(el("div", { class: "login-card" }, [
    el("h1", { text: "Not configured" }),
    el("p", { class: "muted", text:
      "Set SUPABASE_URL and SUPABASE_ANON_KEY in admin/config.js." }),
  ]));
} else {
  renderApp();
}
