/* Admin panel behaviour - sidebar, search, delete confirm, copy path. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };

  // sidebar on mobile
  var side = $("#side"), burger = $("#burger");
  if (side && burger) {
    var scrim = document.createElement("div");
    scrim.className = "scrim";
    document.body.appendChild(scrim);
    function toggle(open) {
      side.classList.toggle("open", open);
      scrim.classList.toggle("on", open);
    }
    burger.addEventListener("click", function () { toggle(!side.classList.contains("open")); });
    scrim.addEventListener("click", function () { toggle(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") toggle(false); });
  }

  // live table filter
  var search = document.getElementById("tableSearch");
  var table = document.getElementById("dataTable");
  if (search && table) {
    search.addEventListener("input", function () {
      var q = search.value.toLowerCase().trim();
      Array.prototype.forEach.call(table.tBodies[0].rows, function (row) {
        row.style.display = !q || row.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none";
      });
    });
  }

  // confirm before destructive posts
  document.addEventListener("submit", function (e) {
    var form = e.target.closest(".js-confirm");
    if (!form) return;
    var name = form.getAttribute("data-name") || "this item";
    if (!window.confirm('Delete "' + name + '"?\n\nThis cannot be undone.')) e.preventDefault();
  });

  // copy an image path
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".js-copy");
    if (!btn) return;
    var path = btn.getAttribute("data-path") || "";
    var done = function () {
      var old = btn.innerHTML;
      btn.innerHTML = '<i class="ri-check-line"></i> Copied';
      setTimeout(function () { btn.innerHTML = old; }, 1400);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(path).then(done, function () {});
    } else {
      var t = document.createElement("textarea");
      t.value = path; document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); done(); } catch (err) {}
      document.body.removeChild(t);
    }
  });
})();
