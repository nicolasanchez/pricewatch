/* PriceWatch · interacción de la web (sin dependencias salvo htmx) */
(function () {
  "use strict";

  var SYMBOLS = { EUR: "€", USD: "US$", GBP: "£", CHF: "CHF", SEK: "kr", PLN: "zł", MXN: "MX$", BRL: "R$" };
  var dateFmt = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", year: "numeric" });

  function money(value, symbol) {
    var parts = Number(value).toFixed(2).split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return parts[0] + "," + parts[1] + " " + symbol;
  }
  function parseAmount(text) {
    var s = String(text || "").replace(/[^\d.,]/g, "");
    if (s.indexOf(",") >= 0) s = s.replace(/\./g, "").replace(",", ".");
    var v = parseFloat(s);
    return isFinite(v) && v > 0 ? v : null;
  }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  /* ---------- Desplegables (avisos) ---------- */
  function initDropdowns() {
    $$("[data-dropdown]").forEach(function (btn) {
      var panel = document.getElementById(btn.getAttribute("data-dropdown"));
      if (!panel || btn._pw) return;
      btn._pw = true;
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var open = panel.hidden;
        panel.hidden = !open;
        btn.setAttribute("aria-expanded", String(open));
        if (open) { var dot = $(".dot", btn); if (dot) dot.remove(); }
      });
      panel.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { panel.hidden = true; btn.setAttribute("aria-expanded", "false"); btn.focus(); }
      });
      document.addEventListener("click", function (e) {
        if (!panel.hidden && !panel.contains(e.target)) { panel.hidden = true; btn.setAttribute("aria-expanded", "false"); }
      });
    });
  }

  /* ---------- Avisos temporales ---------- */
  function initToasts(root) {
    $$("[data-autohide]", root).forEach(function (el) {
      if (el._pw) return;
      el._pw = true;
      setTimeout(function () { el.style.transition = "opacity 300ms"; el.style.opacity = "0"; }, 7000);
      setTimeout(function () { el.remove(); }, 7400);
    });
  }

  /* ---------- Buscador de la portada ---------- */
  function initSearch() {
    var box = $(".search");
    if (!box) return;
    var results = $("#search-results", box), input = $("input[type=search]", box);
    document.addEventListener("click", function (e) { if (!box.contains(e.target)) results.innerHTML = ""; });
    input.addEventListener("keydown", function (e) { if (e.key === "Escape") { results.innerHTML = ""; } });
  }

  /* ---------- Acceso: cambio suave entre iniciar sesión y crear cuenta ---------- */
  function initAccess() {
    var card = $("[data-access]");
    if (!card) return;
    var panes = $(".panes", card);
    var titles = { login: "Iniciar sesión · PriceWatch", signup: "Crear cuenta · PriceWatch" };

    function setMode(mode) {
      if (card.dataset.mode === mode) return;
      var from = $("#pane-" + card.dataset.mode), to = $("#pane-" + mode);
      card.dataset.mode = mode;
      $$("[role=tab]", card).forEach(function (t) { t.setAttribute("aria-selected", String(t.dataset.tab === mode)); });
      $(".t-login", card).setAttribute("aria-hidden", String(mode !== "login"));
      $(".t-signup", card).setAttribute("aria-hidden", String(mode !== "signup"));
      document.title = titles[mode];
      history.replaceState(null, "", card.dataset[mode + "Url"] + location.search);

      panes.style.height = from.offsetHeight + "px";
      from.classList.add("leaving");
      to.hidden = false;
      to.classList.add("entering");
      requestAnimationFrame(function () {
        panes.style.height = to.offsetHeight + "px";
        requestAnimationFrame(function () { to.classList.remove("entering"); });
      });
      setTimeout(function () {
        from.hidden = true;
        from.classList.remove("leaving");
        panes.style.height = "";
        var first = $("input:not([type=hidden])", to);
        if (first) first.focus({ preventScroll: true });
      }, 330);
    }
    $$("[data-tab]", card).forEach(function (b) { b.addEventListener("click", function () { setMode(b.dataset.tab); }); });
  }

  /* ---------- Ficha: filtro de tiendas oficiales ---------- */
  function initOfficialFilter() {
    var cb = $("[data-official-filter]");
    if (!cb) return;
    cb.addEventListener("change", function () {
      $$(".deal-row").forEach(function (row) { row.hidden = cb.checked && row.dataset.official === "0"; });
    });
  }

  /* ---------- Ficha: gráfica del histórico ---------- */
  function initChart() {
    var host = $("#price-chart"), dataEl = $("#timeline-data");
    if (!host || !dataEl) return;
    var all = JSON.parse(dataEl.textContent).map(function (d) { return { t: new Date(d.t), p: d.p, s: d.s }; });
    var symbol = SYMBOLS[host.dataset.currency] || host.dataset.currency;
    var xLabels = $("#price-chart-x");
    var seg = $(".segmented"), ind = $(".thumb-ind", seg), buttons = $$("button", seg);

    function moveIndicator(btn) {
      ind.style.left = btn.offsetLeft + "px";
      ind.style.width = btn.offsetWidth + "px";
    }

    function draw(days) {
      host.innerHTML = "";
      xLabels.innerHTML = "";
      var now = new Date();
      var from = days ? new Date(now.getTime() - days * 864e5) : (all.length ? all[0].t : now);
      var pts = all.filter(function (d) { return d.t >= from; });
      var before = all.filter(function (d) { return d.t < from; }).pop();
      if (before) pts.unshift({ t: from, p: before.p, s: before.s, carried: true });
      if (!pts.length) {
        host.innerHTML = '<p class="chart-empty">Aún no hay histórico para este periodo.</p>';
        return;
      }
      var t0 = pts[0].t.getTime(), t1 = Math.max(now.getTime(), t0 + 864e5);
      var prices = pts.map(function (d) { return d.p; });
      var lo = Math.min.apply(null, prices), hi = Math.max.apply(null, prices);
      var pad = Math.max((hi - lo) * 0.25, hi * 0.08, 0.5);
      lo = Math.max(0, lo - pad); hi = hi + pad;
      var X = function (t) { return 2 + ((t - t0) / (t1 - t0)) * 94; };
      var Y = function (p) { return 6 + ((hi - p) / (hi - lo)) * 88; };
      var minP = Math.min.apply(null, pts.filter(function (d) { return !d.carried; }).map(function (d) { return d.p; }).concat([Infinity]));

      [0.25, 0.5, 0.75].forEach(function (f) {
        var v = hi - (hi - lo) * f;
        var g = document.createElement("div"); g.className = "grid"; g.style.top = Y(v) + "%"; host.appendChild(g);
        var l = document.createElement("span"); l.className = "ylab"; l.style.top = Y(v) + "%"; l.textContent = money(v, symbol); host.appendChild(l);
      });

      var xy = pts.map(function (d) { return [X(d.t.getTime()), Y(d.p)]; });
      var line = "M" + xy[0][0] + "," + xy[0][1];
      for (var i = 1; i < xy.length; i++) {
        var mx = (xy[i][0] - xy[i - 1][0]) / 2;
        line += " C" + (xy[i - 1][0] + mx) + "," + xy[i - 1][1] + " " + (xy[i][0] - mx) + "," + xy[i][1] + " " + xy[i][0] + "," + xy[i][1];
      }
      line += " L98," + xy[xy.length - 1][1];
      var area = line + " L98,100 L" + xy[0][0] + ",100 Z";
      var ns = "http://www.w3.org/2000/svg";
      var svg = document.createElementNS(ns, "svg");
      svg.setAttribute("viewBox", "0 0 100 100");
      svg.setAttribute("preserveAspectRatio", "none");
      svg.setAttribute("aria-hidden", "true");
      svg.innerHTML =
        '<defs><linearGradient id="pwArea" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0" stop-color="var(--accent)" stop-opacity="0.28"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>' +
        '<path d="' + area + '" fill="url(#pwArea)"/>' +
        '<path d="' + line + '" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
      host.appendChild(svg);

      var guide = document.createElement("div"); guide.className = "guide"; guide.hidden = true; host.appendChild(guide);
      var tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; tip.setAttribute("role", "status"); host.appendChild(tip);

      pts.forEach(function (d, idx) {
        if (d.carried) return;
        var b = document.createElement("button");
        b.type = "button";
        b.className = "pt" + (d.p === minP ? " min" : "");
        b.style.left = xy[idx][0] + "%";
        b.style.top = xy[idx][1] + "%";
        b.setAttribute("aria-label", dateFmt.format(d.t) + ": " + money(d.p, symbol) + " en " + d.s);
        b.appendChild(document.createElement("span"));
        function show() {
          $$(".pt.on", host).forEach(function (o) { o.classList.remove("on"); });
          b.classList.add("on");
          guide.hidden = false; guide.style.left = xy[idx][0] + "%";
          tip.innerHTML = "<span>" + dateFmt.format(d.t) + "</span><strong>" + money(d.p, symbol) + "</strong><span>en " + d.s + "</span>";
          tip.hidden = false;
          var x = xy[idx][0], y = xy[idx][1];
          tip.style.left = x + "%"; tip.style.top = y + "%";
          tip.style.transform = "translate(" + (x < 15 ? "-12%" : x > 85 ? "-88%" : "-50%") + "," + (y < 30 ? "24px" : "calc(-100% - 24px)") + ")";
        }
        function hide() { b.classList.remove("on"); guide.hidden = true; tip.hidden = true; }
        b.addEventListener("mouseenter", show); b.addEventListener("focus", show);
        b.addEventListener("mouseleave", hide); b.addEventListener("blur", hide);
        host.appendChild(b);
      });

      var mid = new Date((t0 + t1) / 2);
      [new Date(t0), mid, new Date(t1)].forEach(function (d, k) {
        var s = document.createElement("span"); s.textContent = k === 2 ? "Hoy" : dateFmt.format(d); xLabels.appendChild(s);
      });
    }

    buttons.forEach(function (b) {
      b.addEventListener("click", function () {
        buttons.forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
        moveIndicator(b);
        draw(Number(b.dataset.range));
      });
    });
    var active = $("[aria-pressed=true]", seg) || buttons[0];
    requestAnimationFrame(function () { moveIndicator(active); });
    window.addEventListener("resize", function () { moveIndicator($("[aria-pressed=true]", seg)); });
    draw(Number(active.dataset.range));
  }

  /* ---------- Ficha: ventana de crear alerta ---------- */
  function initAlertForm(root) {
    var form = $(".alert-form", root);
    if (!form || form._pw) return;
    form._pw = true;
    var symbol = form.dataset.symbol, low = parseFloat(form.dataset.low);
    var input = $("#id_target_price", form), hint = $("#target-hint", form), quick = $("[data-quick]", form);

    function selected() {
      var r = $("input[name=store]:checked", form);
      return { price: parseFloat(r.dataset.price), name: r.dataset.name || "" };
    }
    function update() {
      var sel = selected(), v = parseAmount(input.value);
      if (!v) hint.textContent = "Escribe el precio al que quieres comprarlo o elige una sugerencia.";
      else if (v >= sel.price) hint.textContent = "Ya está por debajo de ese precio: te avisaríamos en la próxima comprobación.";
      else hint.textContent = "Faltan " + money(sel.price - v, symbol) + " (−" + Math.round((1 - v / sel.price) * 100) + " %) para llegar a tu precio.";
    }
    function chips() {
      var p = selected().price, list = [];
      if (isFinite(low)) list.push(["Mínimo histórico", low]);
      list.push(["−10 %", Math.floor(p * 90) / 100], ["−25 %", Math.floor(p * 75) / 100]);
      quick.innerHTML = "";
      list.forEach(function (q) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "quick"; b.textContent = q[0] + " · " + money(q[1], symbol);
        b.addEventListener("click", function () { input.value = q[1].toFixed(2).replace(".", ","); update(); input.focus(); });
        quick.appendChild(b);
      });
    }
    $$("input[name=store]", form).forEach(function (r) { r.addEventListener("change", function () { chips(); update(); }); });
    input.addEventListener("input", update);
    chips(); update();
  }

  function initDialogs() {
    $$("[data-open]").forEach(function (btn) {
      var dlg = document.getElementById(btn.dataset.open);
      if (!dlg || btn._pw) return;
      btn._pw = true;
      var body = $("#alert-dialog-body", dlg), pristine = body ? body.innerHTML : "";
      btn.addEventListener("click", function () { dlg.showModal(); var i = $("#id_target_price", dlg); if (i) i.focus(); });
      dlg.addEventListener("click", function (e) {
        if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
      });
      dlg.addEventListener("close", function () {
        if (body && $(".done", body)) {
          body.innerHTML = pristine;
          if (window.htmx) htmx.process(body);
          initAlertForm(body);
        }
      });
    });
  }

  /* ---------- Legal: pestañas y preferencias de cookies ---------- */
  function initLegal() {
    var page = $("[data-legal]");
    if (!page) return;
    var tabs = $$("[data-doc]", page);
    function show(doc, focus) {
      if (!$("[data-panel=" + doc + "]", page)) doc = "aviso";
      tabs.forEach(function (t) { t.setAttribute("aria-selected", String(t.dataset.doc === doc)); });
      $$("[data-panel]", page).forEach(function (p) { p.hidden = p.dataset.panel !== doc; });
      if (focus) history.replaceState(null, "", "#" + doc);
    }
    tabs.forEach(function (t) { t.addEventListener("click", function () { show(t.dataset.doc, true); }); });
    window.addEventListener("hashchange", function () { show(location.hash.slice(1)); });
    show(location.hash.slice(1) || "aviso");

    var prefs = {};
    try { prefs = JSON.parse(decodeURIComponent((document.cookie.match(/(?:^|; )pw_cookies=([^;]*)/) || [])[1] || "{}")); } catch (e) { prefs = {}; }
    $$("[data-cookie]", page).forEach(function (sw) {
      sw.setAttribute("aria-checked", String(!!prefs[sw.dataset.cookie]));
      sw.addEventListener("click", function () {
        sw.setAttribute("aria-checked", String(sw.getAttribute("aria-checked") !== "true"));
        $("[data-cookie-status]", page).textContent = "";
      });
    });
    var save = $("[data-cookie-save]", page);
    if (save) save.addEventListener("click", function () {
      var out = {};
      $$("[data-cookie]", page).forEach(function (sw) { out[sw.dataset.cookie] = sw.getAttribute("aria-checked") === "true"; });
      document.cookie = "pw_cookies=" + encodeURIComponent(JSON.stringify(out)) + "; path=/; max-age=" + 60 * 60 * 24 * 180 + "; SameSite=Lax";
      $("[data-cookie-status]", page).textContent = "Preferencias guardadas.";
    });
  }

  /* Imagen que no carga: se oculta y queda el fondo neutro del hueco */
  document.addEventListener("error", function (e) {
    if (e.target && e.target.tagName === "IMG") e.target.style.visibility = "hidden";
  }, true);

  document.addEventListener("DOMContentLoaded", function () {
    $$("img").forEach(function (img) { if (img.complete && !img.naturalWidth) img.style.visibility = "hidden"; });
    initDropdowns(); initToasts(document); initSearch(); initAccess();
    initOfficialFilter(); initChart(); initAlertForm(document); initDialogs(); initLegal();
  });
  document.addEventListener("htmx:afterSwap", function (e) {
    initToasts(e.target);
    initAlertForm(e.target);
    var auto = e.target.querySelector && e.target.querySelector("[autofocus]");
    if (auto) { auto.focus(); if (auto.select) auto.select(); }
  });
  /* Formularios con errores devuelven 422: htmx debe pintarlos igualmente */
  document.addEventListener("htmx:beforeSwap", function (e) {
    if (e.detail.xhr.status === 422) { e.detail.shouldSwap = true; e.detail.isError = false; }
  });
})();
