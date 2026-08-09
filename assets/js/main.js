/*==================================================================
  SHARMA INTERIOR CONSTRUCTION - site behaviour
  Vanilla JS, no dependencies. Every module guards for its own markup,
  so the same file is safe to load on every page.

    nav drawer      scroll reveal    project filter + modal
    sticky header   stat counters    testimonial slider
    back to top     form validation  toasts
==================================================================*/
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $  = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /*=============== TOASTS ===============*/
  var toastHost;
  function toast(msg, kind) {
    if (!toastHost) {
      toastHost = document.createElement("div");
      toastHost.className = "toast-host";
      toastHost.setAttribute("role", "status");
      toastHost.setAttribute("aria-live", "polite");
      document.body.appendChild(toastHost);
    }
    var el = document.createElement("div");
    el.className = "toast toast--" + (kind === "err" ? "err" : "ok");
    el.innerHTML =
      '<i class="ri-' + (kind === "err" ? "error-warning-fill" : "checkbox-circle-fill") + '"></i>' +
      "<span></span>";
    $("span", el).textContent = msg;
    toastHost.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("is-in"); });
    setTimeout(function () {
      el.classList.remove("is-in");
      setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 350);
    }, 4200);
  }
  window.siteToast = toast;

  /*=============== MOBILE NAV DRAWER ===============*/
  function initNav() {
    var toggle = $("#navToggle");
    var drawer = $("#navDrawer");
    if (!toggle || !drawer) return;

    function setOpen(open) {
      toggle.setAttribute("aria-expanded", String(open));
      drawer.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
    }

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    // close when a link is tapped, or on Escape, or when resized to desktop
    $$("a", drawer).forEach(function (a) {
      a.addEventListener("click", function () { setOpen(false); });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setOpen(false);
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 992) setOpen(false);
    });
  }

  /*=============== STICKY HEADER + PROGRESS + TO-TOP ===============*/
  function initScrollChrome() {
    var header = $("#siteHeader");
    var bar = document.createElement("div");
    bar.className = "progress";
    document.body.appendChild(bar);

    var top = document.createElement("button");
    top.className = "to-top";
    top.type = "button";
    top.setAttribute("aria-label", "Back to top");
    top.innerHTML = '<i class="ri-arrow-up-line"></i>';
    top.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
    });
    document.body.appendChild(top);

    var ticking = false;
    function update() {
      ticking = false;
      var y = window.scrollY;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      if (header) header.classList.toggle("is-stuck", y > 40);
      top.classList.toggle("is-in", y > 500);
      bar.style.transform = "scaleX(" + (max > 0 ? Math.min(y / max, 1) : 0) + ")";
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  /*=============== SCROLL REVEAL ===============*/
  function initReveal() {
    var items = $$("[data-reveal]");
    if (!items.length) return;

    if (reduced || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("is-in"); });
      return;
    }

    // stagger siblings that share a parent
    var seen = new Map();
    items.forEach(function (el) {
      var p = el.parentNode;
      var n = seen.get(p) || 0;
      seen.set(p, n + 1);
      el.style.setProperty("--d", Math.min(n, 6) * 0.08 + "s");
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });

    items.forEach(function (el) { io.observe(el); });
  }

  /*=============== STAT COUNTERS ===============*/
  function initCounters() {
    var nodes = $$("[data-count]");
    if (!nodes.length) return;

    function run(el) {
      var target = parseFloat(el.getAttribute("data-count"));
      var suffix = el.getAttribute("data-suffix") || "";
      if (!isFinite(target)) return;
      if (reduced) { el.textContent = target.toLocaleString() + suffix; return; }

      var start = null, dur = 1600;
      function step(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        var eased = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
        el.textContent = Math.round(target * eased).toLocaleString() + (p === 1 ? suffix : "");
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    if (!("IntersectionObserver" in window)) { nodes.forEach(run); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { run(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.4 });
    nodes.forEach(function (el) { io.observe(el); });
  }

  /*=============== PROJECT FILTER ===============*/
  function initFilter() {
    var bar = $("#projectFilter");
    var grid = $("#projectGrid");
    if (!bar || !grid) return;

    var cards = $$(".project-card", grid);
    var empty = $("#projectEmpty");

    bar.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-filter]");
      if (!btn) return;

      $$("button", bar).forEach(function (b) {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-pressed", String(b === btn));
      });

      var want = btn.getAttribute("data-filter");
      var shown = 0;
      cards.forEach(function (card) {
        var tags = (card.getAttribute("data-tags") || "").split(/\s+/);
        var match = want === "all" || tags.indexOf(want) !== -1;
        card.classList.toggle("is-hidden", !match);
        if (match) shown++;
      });
      if (empty) empty.classList.toggle("hide", shown > 0);
    });
  }

  /*=============== PROJECT MODAL ===============*/
  function initModal() {
    var modal = $("#projectModal");
    if (!modal) return;

    var box = $(".modal-box", modal);
    var lastFocus = null;

    function open(card) {
      lastFocus = document.activeElement;
      $("#pmImg", modal).src = card.getAttribute("data-img") || "";
      $("#pmImg", modal).alt = card.getAttribute("data-title") || "";
      $("#pmTitle", modal).textContent = card.getAttribute("data-title") || "";
      $("#pmDesc", modal).textContent = card.getAttribute("data-desc") || "";
      $("#pmLocation", modal).textContent = card.getAttribute("data-location") || "-";
      $("#pmType", modal).textContent = card.getAttribute("data-type") || "-";
      $("#pmStatus", modal).textContent = card.getAttribute("data-status") || "-";
      $("#pmDate", modal).textContent = card.getAttribute("data-date") || "-";
      modal.classList.add("is-open");
      document.body.classList.add("nav-open");
      $(".modal-close", modal).focus();
    }

    function close() {
      modal.classList.remove("is-open");
      document.body.classList.remove("nav-open");
      if (lastFocus) lastFocus.focus();
    }

    document.addEventListener("click", function (e) {
      var card = e.target.closest(".project-card[data-title]");
      if (card) { e.preventDefault(); open(card); return; }
      if (e.target.closest(".modal-close")) { close(); return; }
      // click on the backdrop, not the panel
      if (e.target === modal) close();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("is-open")) close();
    });
    if (box) box.addEventListener("click", function (e) { e.stopPropagation(); });
  }

  /*=============== TESTIMONIAL SLIDER ===============*/
  function initSlider() {
    var track = $("#quoteTrack");
    if (!track) return;
    var prev = $("#quotePrev"), next = $("#quoteNext");

    function stride() {
      var first = track.firstElementChild;
      if (!first) return track.clientWidth;
      var gap = parseFloat(getComputedStyle(track).columnGap || getComputedStyle(track).gap) || 0;
      return first.getBoundingClientRect().width + gap;
    }
    if (prev) prev.addEventListener("click", function () { track.scrollBy({ left: -stride(), behavior: "smooth" }); });
    if (next) next.addEventListener("click", function () { track.scrollBy({ left: stride(), behavior: "smooth" }); });
  }

  /*=============== FORM VALIDATION ===============*/
  var RE_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  var RE_PHONE = /^[\d\s+()-]{7,20}$/;

  function fieldOf(input) { return input.closest(".field"); }

  function setError(input, msg) {
    var f = fieldOf(input);
    if (!f) return;
    f.classList.add("has-error");
    var e = $(".err", f);
    if (e) e.textContent = msg;
    input.setAttribute("aria-invalid", "true");
  }
  function clearError(input) {
    var f = fieldOf(input);
    if (!f) return;
    f.classList.remove("has-error");
    input.removeAttribute("aria-invalid");
  }

  function validate(input) {
    var v = (input.value || "").trim();
    var label = input.getAttribute("data-label") || input.name || "This field";

    if (input.required && !v) { setError(input, label + " is required."); return false; }
    if (!v) { clearError(input); return true; }

    if (input.type === "email" && !RE_EMAIL.test(v)) {
      setError(input, "Enter a valid email address."); return false;
    }
    if (input.type === "tel" && !RE_PHONE.test(v)) {
      setError(input, "Enter a valid phone number."); return false;
    }
    if (input.tagName === "TEXTAREA" && v.length < 10) {
      setError(input, "Please write at least 10 characters."); return false;
    }
    clearError(input);
    return true;
  }

  function initForms() {
    $$("form[data-validate]").forEach(function (form) {
      var fields = $$("input, select, textarea", form).filter(function (el) {
        return el.type !== "submit" && el.type !== "hidden";
      });

      fields.forEach(function (el) {
        el.addEventListener("blur", function () { validate(el); });
        el.addEventListener("input", function () {
          if (fieldOf(el) && fieldOf(el).classList.contains("has-error")) validate(el);
        });
      });

      form.addEventListener("submit", function (e) {
        var ok = true, firstBad = null;
        fields.forEach(function (el) {
          if (!validate(el)) { ok = false; if (!firstBad) firstBad = el; }
        });

        if (!ok) {
          e.preventDefault();
          toast("Please fix the highlighted fields.", "err");
          if (firstBad) firstBad.focus();
          return;
        }

        // No backend on this site: hand off to the mail handler and confirm.
        // Remove this block if you wire up a real endpoint.
        if (form.getAttribute("data-demo") === "true") {
          e.preventDefault();
          var btn = $("[type=submit]", form);
          if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }
          setTimeout(function () {
            form.reset();
            fields.forEach(clearError);
            if (btn) { btn.disabled = false; btn.textContent = btn.getAttribute("data-label") || "Send Message"; }
            toast("Thanks — your message has been recorded. We'll be in touch within one business day.");
          }, 700);
        }
      });
    });

    // newsletter
    $$("form[data-newsletter]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var input = $("input", form);
        var v = (input.value || "").trim();
        if (!RE_EMAIL.test(v)) { toast("Enter a valid email address.", "err"); input.focus(); return; }
        form.reset();
        toast("Subscribed. Thanks for signing up.");
      });
    });
  }

  /*=============== ACTIVE NAV ===============*/
  function initActiveNav() {
    var here = (location.pathname.split("/").pop() || "index.html").toLowerCase();
    $$(".nav-links a, .drawer-link").forEach(function (a) {
      var href = (a.getAttribute("href") || "").split("/").pop().toLowerCase();
      if (href && href === here) a.classList.add("is-active");
    });
  }

  /*=============== YEAR ===============*/
  function initYear() {
    $$("[data-year]").forEach(function (el) {
      el.textContent = new Date().getFullYear();
    });
  }

  /*=============== MARQUEE ===============*/
  /* The client strip scrolls continuously. Cloning the run in JS keeps the
     template to a single loop of six logos. */
  function initMarquee() {
    $$(".logos").forEach(function (host) {
      var logos = $$("img", host);
      // below this count the strip is too short to loop without a visible gap
      if (logos.length < 5) return;

      var run = document.createElement("div");
      run.className = "marquee-run";
      logos.forEach(function (img) { run.appendChild(img); });

      var clone = run.cloneNode(true);
      clone.setAttribute("aria-hidden", "true");
      $$("img", clone).forEach(function (img) { img.setAttribute("alt", ""); });

      host.innerHTML = "";
      host.appendChild(run);
      host.appendChild(clone);
      host.classList.add("is-marquee");
    });
  }

  /*=============== BOOT ===============*/
  function init() {
    initNav();
    initScrollChrome();
    initReveal();
    initCounters();
    initFilter();
    initModal();
    initSlider();
    initForms();
    initActiveNav();
    initYear();
    initMarquee();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
