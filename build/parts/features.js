  // ================================================================== richer browsing
  // Detail panel, smart search, moods, Surprise me, heatmap, compare, walking
  // time, shared lists, top picks, phone bottom sheet. Runs inside the main page
  // script, so it uses that script's places, map, filters and helpers.

  const DAYS_MON = [1, 2, 3, 4, 5, 6, 0];                 // display order Mo..Su
  const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const fmtMin = (m) => { m %= 1440; return String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"); };
  const week = (p) => (p._wk === undefined ? (p._wk = parseHours(p.hours)) : p._wk);

  // ------------------------------------------------------------ walking time / distance label
  const walkMin = (kmv) => Math.max(1, Math.round((kmv * 1.3) / 4.8 * 60));   // street detour 1.3x, 4.8 km/h
  function distLabel(p) {
    if (state.me) return `<span class="dist" title="From your location">${fmtKm(p.d)} · ${walkMin(p.d)} min walk</span>`;
    return `<span class="dist">${fmtKm(p.d)}</span>`;
  }

  // ------------------------------------------------------------ moods
  const PREMIUM = /italian|european|french|japanese|sushi|mediterranean|steak|continental|lebanese|fine dining|asian|thai|korean/i;
  const MOODS = {
    work: { label: "💻 Work-friendly", test: (p) => p.cat === "cafe" && (/coffee|starbucks|third wave|blue tokai|araku|barista|costa|tim hortons|ccd|cafe coffee day|subko|bombay island/i.test(p.name) || p.cuisine.includes("Coffee Shop")) },
    date: { label: "🕯 Date night", test: (p) => p.priceTwo >= 1500 || (p.rating >= 4.5 && p.cat === "rest") || (p.cat === "rest" && p.cuisine.some((c) => PREMIUM.test(c))) },
    budget: { label: "💸 Under ₹500", test: (p) => (p.priceTwo && p.priceTwo <= 500) || (!p.priceTwo && /Fast food|Tea shop|Food court/.test(p.kind)) || p.cuisine.some((c) => /street|chaat|vada|pav|snack|tea/i.test(c)) },
    late: { label: "🌙 Late night", test: (p) => { const w = week(p); return !!w && w.some((d) => d.some(([, b]) => b >= 23 * 60 + 30)); } },
    breakfast: { label: "🍳 Breakfast", test: (p) => { const w = week(p); return (!!w && w.some((d) => d.some(([a]) => a <= 8 * 60 + 30))) || p.cuisine.some((c) => /breakfast|bakery|irani|udupi|south indian/i.test(c)) || p.kind === "Cafe & restaurant"; } },
    dessert: { label: "🍨 Desserts", test: (p) => /Dessert|Bakery/.test(p.kind) || p.cuisine.some((c) => /ice cream|dessert|cake|waffle|bubble tea|chocolate|crepe|bakery/i.test(c)) },
  };
  state.mood = "";
  function moodOk(p) { return !state.mood || MOODS[state.mood].test(p); }
  $("moods").innerHTML = Object.entries(MOODS).map(([k, m]) => `<button type="button" data-mood="${k}" aria-pressed="false">${m.label}</button>`).join("");
  $("moods").addEventListener("click", (e) => {
    const b = e.target.closest("[data-mood]"); if (!b) return;
    state.mood = state.mood === b.dataset.mood ? "" : b.dataset.mood;
    document.querySelectorAll("#moods [data-mood]").forEach((x) => { const on = x.dataset.mood === state.mood; x.classList.toggle("on", on); x.setAttribute("aria-pressed", on); });
    state.shown = PAGE; render();
  });

  // ------------------------------------------------------------ shared lists (#list-key1-key2…)
  state.list = null;
  function showSharedList(keys) {
    const found = keys.filter((k) => byKey.has(k));
    if (!found.length) return;
    state.list = new Set(found);
    $("listBanner").hidden = false;
    $("listBannerText").textContent = `Viewing a shared list of ${found.length} place${found.length > 1 ? "s" : ""}.`;
    setArea(null, "", document.querySelector('#quick [data-area=""]'));
    const b = L.latLngBounds(found.map((k) => [byKey.get(k).lat, byKey.get(k).lng]));
    map.fitBounds(b.pad(0.3), { animate: false, maxZoom: 16 });
  }
  $("listSaveAll").addEventListener("click", () => {
    if (!state.list) return;
    state.list.forEach((k) => favs.add(k)); store.set("cf-favs", [...favs]); syncFavCount();
    document.querySelectorAll("[data-fav]").forEach((b) => { const on = favs.has(b.dataset.fav); b.classList.toggle("on", on); b.textContent = on ? "♥" : "♡"; });
    toast("Saved to your list");
  });
  $("listClose").addEventListener("click", () => {
    state.list = null; $("listBanner").hidden = true;
    if (/^#list-/.test(location.hash)) history.replaceState(null, "", location.pathname + location.search);
    refreshCounts(); render();
  });
  $("shareListBtn").addEventListener("click", async () => {
    const keys = [...favs].slice(0, 60);
    if (!keys.length) return toast("Save some places with ♥ first");
    const url = location.href.split("#")[0] + "#list-" + keys.join("-");
    try { if (navigator.share) { await navigator.share({ title: "My cafe list", url }); return; } } catch (e) { if (e && e.name === "AbortError") return; }
    try { await navigator.clipboard.writeText(url); toast("List link copied"); } catch (e) { toast(url); }
  });
  const syncShareList = () => { $("shareListBtn").hidden = !favs.size; };

  // ------------------------------------------------------------ compare (up to 3)
  const cmp = [];
  function toggleCompare(key) {
    const i = cmp.indexOf(key);
    if (i >= 0) cmp.splice(i, 1);
    else { if (cmp.length >= 3) { toast("Compare up to 3 places"); return; } cmp.push(key); }
    syncCompare();
  }
  function syncCompare() {
    $("cmpTray").hidden = !cmp.length;
    $("cmpCount").textContent = cmp.length;
    document.querySelectorAll("[data-cmp]").forEach((b) => { const on = cmp.includes(b.dataset.cmp); b.classList.toggle("on", on); b.textContent = on ? "✓ Comparing" : "⇄ Compare"; });
  }
  function compareTable() {
    const ps = cmp.map((k) => byKey.get(k));
    const ctr = state.me || map.getCenter();
    const row = (label, f) => `<tr><th scope="row">${label}</th>${ps.map((p) => `<td>${f(p)}</td>`).join("")}</tr>`;
    const o = (p) => { const v = openNow(p.hours); return v === true ? `<span class="tag open">Open now</span>` : v === false ? `<span class="tag shut">Closed now</span>` : `<span class="muted">Hours not listed</span>`; };
    $("cmpBody").innerHTML = `<table class="cmp"><thead><tr><th></th>${ps.map((p) => `<th scope="col">${esc(p.name)}</th>`).join("")}</tr></thead><tbody>
      ${row("Type", (p) => esc(p.kind))}
      ${row("Area", (p) => esc(p.loc === p.sub ? p.sub : p.loc + ", " + p.sub))}
      ${row("Rating", (p) => p.rating ? `<b class="stars">★ ${p.rating.toFixed(1)}</b> <span class="muted">${esc(p.ratingSrc)}</span>` : `<a class="rate" href="${esc(gmaps(p))}" target="_blank" rel="noopener">See on Google</a>`)}
      ${row("For two", (p) => p.priceTwo ? `≈ ₹${p.priceTwo.toLocaleString("en-IN")}` : `<span class="muted">Not listed</span>`)}
      ${row("Food", (p) => p.pureVeg ? `<span class="tag veg">Pure veg</span>` : p.nonVeg ? `<span class="tag nonveg">Non-veg</span>` : `<span class="muted">Not listed</span>`)}
      ${row("Jain", (p) => p.jain ? "Yes" : `<span class="muted">Not listed</span>`)}
      ${row("Now", o)}
      ${row("Distance", (p) => { const d = km(p, ctr); return `${fmtKm(d)}${state.me ? " · " + walkMin(d) + " min walk" : ""}`; })}
      ${row("Cuisine", (p) => p.cuisine.length ? esc(p.cuisine.join(", ")) : `<span class="muted">Not listed</span>`)}
      ${row("", (p) => `<a class="btn go" href="${esc(directions(p))}" target="_blank" rel="noopener">Directions</a>`)}
    </tbody></table>`;
  }
  $("cmpView").addEventListener("click", () => { compareTable(); $("cmpDlg").showModal(); });
  $("cmpClear").addEventListener("click", () => { cmp.length = 0; syncCompare(); });
  $("cmpClose").addEventListener("click", () => $("cmpDlg").close());

  // ------------------------------------------------------------ detail panel
  let detailOpen = null, browseScroll = 0;
  function weeklyHours(p) {
    const w = week(p);
    if (!p.hours) return "";
    if (!w) return `<div class="line"><span class="lbl">Hours</span><span class="muted">${esc(p.hours)}</span></div>`;
    const today = nowIST().day;
    const rows = DAYS_MON.map((d) => {
      const spans = w[d];
      const txt = spans.length ? spans.map(([a, b]) => `${fmtMin(a)}–${fmtMin(b)}`).join(", ") : "Closed";
      return `<tr class="${d === today ? "today" : ""}"><th scope="row">${DAY_NAMES[d]}</th><td>${txt}</td></tr>`;
    }).join("");
    return `<div class="line"><span class="lbl">Hours</span>${hoursLine(p).includes("Open now") ? `<span class="tag open">Open now</span>` : openNow(p.hours) === false ? `<span class="tag shut">Closed now</span>` : ""}</div><table class="week">${rows}</table>`;
  }
  function nearby(p) {
    return places.filter((q) => q !== p && Math.abs(q.lat - p.lat) < 0.006 && Math.abs(q.lng - p.lng) < 0.006)
      .map((q) => [km(p, q), q]).filter(([d]) => d <= 0.5).sort((a, b) => a[0] - b[0]).slice(0, 6);
  }
  function openDetail(p, opts = {}) {
    if (!detailOpen) browseScroll = $("sheetScroll").scrollTop;
    if (typeof resizer !== "undefined") resizer.show();
    detailOpen = p;
    select(p.id, false);
    if (opts.fly !== false) {
      // A pin hidden by the current filters isn't in the cluster layer; just centre on it.
      if (opts.instant || !cluster.hasLayer(markers[p.id])) map.setView([p.lat, p.lng], Math.max(map.getZoom(), 17), { animate: !opts.instant });
      else cluster.zoomToShowLayer(markers[p.id], () => {});
      // On phones the sheet covers the lower half: keep the place in the visible strip above it.
      if (sheet.mq.matches) setTimeout(() => map.panBy([0, Math.round(innerHeight * 0.22)], { animate: !opts.instant }), opts.instant ? 0 : 450);
    }
    const near = nearby(p);
    $("detail").innerHTML = `
      <div class="d-top">
        <button type="button" class="ghost back" id="detailBack" aria-label="Back to results">← Results</button>
        <span class="d-tools">${favBtn(p)}</span>
      </div>
      <h2 class="d-name" tabindex="-1" id="detailName">${esc(p.name)}</h2>
      <div class="d-tags">${catTag(p)}</div>
      <div class="line glive" id="glive-${p.id}" hidden><span class="lbl">Google</span><span class="gval"><span class="muted">Checking Google…</span></span></div>
      ${area(p)}${rating(p)}${price(p)}${food(p)}${weeklyHours(p)}${cuisine(p)}${source(p)}
      ${p.address ? `<p class="meta">${esc(p.address)}</p>` : ""}
      ${p.phone ? `<p class="meta">Phone: <span class="sel">${esc(p.phone)}</span></p>` : ""}
      ${p.website ? `<p class="meta"><a class="rate" href="${esc(p.website)}" target="_blank" rel="noopener">Website ↗</a></p>` : ""}
      <p class="meta">GPS ${p.lat.toFixed(5)}, ${p.lng.toFixed(5)}</p>
      ${actions(p)}
      <div class="actions"><button type="button" class="btn" data-cmp="${p.key}">⇄ Compare</button><button type="button" class="btn ghost" data-report="${p.key}">⚑ Report a problem</button></div>
      ${near.length ? `<h3 class="d-sub">Nearby (within 500 m)</h3><ul class="near">${near.map(([d, q]) =>
        `<li><button type="button" data-open="${q.key}"><span class="dot-sm ${q.cat}"></span><span class="nm">${esc(q.name)}</span><span class="muted">${esc(q.kind)} · ${fmtKm(d)}</span></button></li>`).join("")}</ul>` : ""}`;
    $("browse").hidden = true;
    $("detail").hidden = false;
    $("sheetScroll").scrollTop = 0;
    syncCompare();
    liveLookup(p);
    sheet.set(sheet.state === "full" ? "full" : "half");
    $("detailName").focus({ preventScroll: true });
    if (!opts.keepHash) history.replaceState(null, "", location.pathname + location.search + "#p-" + p.key);
  }
  function closeDetail() {
    if (!detailOpen) return;
    const id = detailOpen.id;
    detailOpen = null;
    $("detail").hidden = true;
    $("browse").hidden = false;
    $("sheetScroll").scrollTop = browseScroll;
    if (/^#p-/.test(location.hash)) history.replaceState(null, "", location.pathname + location.search);
    const li = document.querySelector(`#list li[data-id="${id}"]`);
    if (li) li.focus({ preventScroll: true });
  }
  document.addEventListener("click", (e) => {
    if (e.target.closest("#detailBack")) return closeDetail();
    const o = e.target.closest("[data-open]");
    if (o) { e.preventDefault(); return openDetail(byKey.get(o.dataset.open)); }
    const c = e.target.closest("[data-cmp]");
    if (c) { e.preventDefault(); return toggleCompare(c.dataset.cmp); }
    const r = e.target.closest("[data-report]");
    if (r) { e.preventDefault(); return openReport(byKey.get(r.dataset.report)); }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && detailOpen && !document.querySelector("dialog[open]")) closeDetail(); });

  // ------------------------------------------------------------ top picks
  function renderPicks(rows) {
    const picks = rows.filter((p) => p.rating >= 4.3).sort((a, b) => b.rating - a.rating || (b.priceTwo ? 1 : 0) - (a.priceTwo ? 1 : 0)).slice(0, 12);
    $("picks").hidden = picks.length < 2;
    $("picksWhere").textContent = state.areaName ? `in ${state.areaName}` : "across the city";
    $("picksRow").innerHTML = picks.map((p) => `
      <button type="button" class="pick" data-open="${p.key}">
        <span class="pk-top"><span class="dot-sm ${p.cat}"></span><b class="stars">★ ${p.rating.toFixed(1)}</b></span>
        <span class="pk-name">${esc(p.name)}</span>
        <span class="muted">${esc(p.loc === p.sub ? p.sub : p.loc)}${p.priceTwo ? " · ₹" + p.priceTwo.toLocaleString("en-IN") + " for two" : ""}</span>
      </button>`).join("");
  }

  // ------------------------------------------------------------ Surprise me
  $("surpriseBtn").addEventListener("click", () => {
    const pool = visible();
    if (!pool.length) return toast("Nothing matches your filters. Clear some and try again.");
    const good = pool.filter((p) => p.rating >= 4.2 || openNow(p.hours) === true);
    const from = good.length >= 3 ? good : pool;
    const p = from[Math.floor(Math.random() * from.length)];
    toast(`How about ${p.name}?`);
    openDetail(p);
  });

  // ------------------------------------------------------------ heatmap
  let heat = null;
  const HeatCtl = L.Control.extend({
    options: { position: "topright" },
    onAdd() {
      const box = L.DomUtil.create("div", "leaflet-bar map-tools");
      box.innerHTML = `<button type="button" id="heatBtn" aria-pressed="false" title="Show where places cluster">🔥 Heatmap</button>
        <button type="button" id="surpriseMapBtn" title="Pick a random place">🎲 Surprise me</button>`;
      L.DomEvent.disableClickPropagation(box);
      return box;
    },
  });
  map.addControl(new HeatCtl());
  function drawHeat() {
    if (heat) { heat.remove(); heat = null; }
    if (!$("heatBtn").classList.contains("on") || typeof L.heatLayer !== "function") return;
    heat = L.heatLayer(visible().map((p) => [p.lat, p.lng, p.rating ? 1 : 0.6]), {
      radius: 22, blur: 18, maxZoom: 15, minOpacity: 0.35,
      gradient: { 0.2: "#2b6cd1", 0.45: "#10b981", 0.65: "#facc15", 0.85: "#f97316", 1: "#dc2626" },
    }).addTo(map);
  }
  $("heatBtn").addEventListener("click", (e) => {
    if (typeof L.heatLayer !== "function") return toast("Heatmap isn't available offline");
    const on = !e.currentTarget.classList.contains("on");
    e.currentTarget.classList.toggle("on", on); e.currentTarget.setAttribute("aria-pressed", on);
    if (on) { map.removeLayer(cluster); drawHeat(); toast("Heatmap on: brighter means more places"); }
    else { drawHeat(); map.addLayer(cluster); }
  });
  $("surpriseMapBtn").addEventListener("click", () => $("surpriseBtn").click());

  // ------------------------------------------------------------ smart search
  const allCuisines = [...new Set(places.flatMap((p) => p.cuisine))].sort((a, b) => b.length - a.length);
  const areaIndex = [...new Set([...areas.values()].map((a) => a.name).concat(Object.values(GROUPS).map((g) => g.name)))];
  const areaByLen = [...areaIndex].sort((a, b) => b.length - a.length);
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9& ]+/g, " ").replace(/\s+/g, " ").trim();
  const KEYWORDS = [
    [/\bpure ?veg\b|\bveg(etarian)?\b(?! ?non)/, () => { $("fVeg").checked = true; }],
    [/\bjain\b/, () => { $("fJain").checked = true; }],
    [/\bnon ?veg\b/, () => { $("fNon").checked = true; $("fVeg").checked = false; }],
    [/\bopen( now)?\b/, () => { $("fOpen").checked = true; }],
    [/\bcafe?s?\b|\bcoffee\b/, () => setCat("cafe")],
    [/\brestaurants?\b|\bdinner\b|\blunch\b/, () => setCat("rest")],
    [/\bcheap\b|\bbudget\b/, () => setMood("budget")],
    [/\bdate\b|\bromantic\b/, () => setMood("date")],
    [/\blate( night)?\b/, () => setMood("late")],
    [/\bbreakfast\b/, () => setMood("breakfast")],
    [/\bdesserts?\b|\bice ?cream\b/, () => setMood("dessert")],
    [/\bwork\b|\blaptop\b|\bwifi\b/, () => setMood("work")],
  ];
  function setCat(c) { document.querySelector(`.seg [data-cat="${c}"]`).click(); }
  function setMood(m) { if (state.mood !== m) document.querySelector(`#moods [data-mood="${m}"]`).click(); }

  function smartSearch(raw) {
    let q = " " + norm(raw) + " ";
    if (!q.trim()) return showArea("");
    // An exact place name opens that place; a chain name (several branches) lists them all.
    const exact = places.filter((p) => norm(p.name) === q.trim());
    if (exact.length === 1) { showArea(""); return openDetail(exact[0]); }
    let areaHit = null;
    for (const a of areaByLen) { const n = norm(a); if (n.length > 2 && q.includes(" " + n + " ")) { areaHit = a; q = q.replace(" " + n + " ", " "); break; } }
    // Keywords before cuisines, so "jain" means Jain food rather than a cuisine tag.
    for (const [re, fn] of KEYWORDS) { if (re.test(q)) { fn(); q = q.replace(re, " "); } }
    let cuisineHit = "";
    for (const c of allCuisines) { const n = norm(c); if (n.length > 2 && q.includes(" " + n + " ")) { cuisineHit = c; q = q.replace(" " + n + " ", " "); break; } }
    // A name with no area in it ("starbucks", "irani cafe") searches the whole city.
    const nameLeft = q.replace(/\b(in|near|at|the|and|best|good|places?|food|for|with|mumbai)\b/g, " ").trim();
    if (!areaHit && nameLeft) showArea("");
    q = q.replace(/\b(in|near|at|the|and|best|good|places?|food|for|with|mumbai)\b/g, " ").replace(/\s+/g, " ").trim();
    if (areaHit) showArea(areaHit);
    if (cuisineHit) $("cuisine").value = cuisineHit;      // stays "All" if the area has none of it
    $("filterText").value = q;
    $("place").value = raw;
    state.shown = PAGE; render();
    if (!areaHit && q) { const b = L.latLngBounds(visible().map((p) => [p.lat, p.lng])); if (b.isValid()) map.fitBounds(b.pad(0.1), { maxZoom: 16 }); }
  }

  const box = $("suggestBox");
  let sugItems = [], sugIdx = -1;
  function suggestions(raw) {
    const q = norm(raw);
    if (q.length < 2) return [];
    const out = [];
    areaIndex.filter((a) => norm(a).includes(q)).sort((a, b) => norm(a).indexOf(q) - norm(b).indexOf(q) || a.length - b.length)
      .slice(0, 4).forEach((a) => out.push({ kind: "area", label: a, sub: "Area", value: a }));
    allCuisines.filter((c) => norm(c).includes(q)).slice(0, 2).forEach((c) => out.push({ kind: "cuisine", label: c, sub: "Cuisine", value: c }));
    places.filter((p) => norm(p.name).includes(q)).sort((a, b) => norm(a.name).indexOf(q) - norm(b.name).indexOf(q) || (b.rating || 0) - (a.rating || 0))
      .slice(0, 5).forEach((p) => out.push({ kind: "place", label: p.name, sub: `${p.kind} · ${p.loc === p.sub ? p.sub : p.loc}`, value: p.key, cat: p.cat }));
    if (q.split(" ").length > 1) out.unshift({ kind: "query", label: raw, sub: "Search all", value: raw });
    return out.slice(0, 10);
  }
  function drawSuggestions() {
    box.hidden = !sugItems.length;
    $("place").setAttribute("aria-expanded", !box.hidden);
    box.innerHTML = sugItems.map((s, i) => `<li role="option" id="sug-${i}" class="${i === sugIdx ? "on" : ""}" data-i="${i}" aria-selected="${i === sugIdx}">
      <span class="ic">${s.kind === "area" ? "📍" : s.kind === "cuisine" ? "🍽" : s.kind === "query" ? "🔎" : s.cat === "cafe" ? "☕" : "🍴"}</span>
      <span class="tx"><span>${esc(s.label)}</span><small class="muted">${esc(s.sub)}</small></span></li>`).join("");
    if (sugIdx >= 0) $("place").setAttribute("aria-activedescendant", "sug-" + sugIdx); else $("place").removeAttribute("aria-activedescendant");
  }
  function pickSuggestion(s) {
    box.hidden = true; sugItems = []; $("place").setAttribute("aria-expanded", "false");
    if (s.kind === "area") { $("place").value = s.value; showArea(s.value); }
    else if (s.kind === "cuisine") { refreshCounts(); $("cuisine").value = s.value; state.shown = PAGE; render(); $("place").value = ""; }
    else if (s.kind === "place") { $("place").value = s.label; openDetail(byKey.get(s.value)); }
    else smartSearch(s.value);
  }
  $("place").addEventListener("input", () => { sugItems = suggestions($("place").value); sugIdx = -1; drawSuggestions(); });
  $("place").addEventListener("keydown", (e) => {
    if (box.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); sugIdx = (sugIdx + 1) % sugItems.length; drawSuggestions(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sugIdx = (sugIdx - 1 + sugItems.length) % sugItems.length; drawSuggestions(); }
    else if (e.key === "Escape") { box.hidden = true; sugIdx = -1; }
    else if (e.key === "Enter" && sugIdx >= 0) { e.preventDefault(); pickSuggestion(sugItems[sugIdx]); }
  });
  box.addEventListener("mousedown", (e) => { const li = e.target.closest("[data-i]"); if (li) { e.preventDefault(); pickSuggestion(sugItems[+li.dataset.i]); } });
  $("place").addEventListener("blur", () => setTimeout(() => { box.hidden = true; $("place").setAttribute("aria-expanded", "false"); }, 150));

  // ------------------------------------------------------------ phone bottom sheet
  const sheet = {
    state: "half",
    mq: matchMedia("(max-width: 640px)"),
    set(s) {
      if (!this.mq.matches) return;
      this.state = s;
      const panel = document.querySelector(".panel");
      panel.dataset.sheet = s;
      panel.style.transform = "";
      $("sheetHandle").setAttribute("aria-label", s === "full" ? "Shrink the list" : "Expand the list");
    },
  };
  (function setupSheet() {
    const panel = document.querySelector(".panel");
    const handle = $("sheetHandle");
    let startY = 0, startT = 0, dragging = false, moved = false;
    const current = () => new DOMMatrixReadOnly(getComputedStyle(panel).transform).m42;
    handle.addEventListener("pointerdown", (e) => {
      if (!sheet.mq.matches) return;
      dragging = true; moved = false; startY = e.clientY; startT = current();
      panel.classList.add("dragging"); handle.setPointerCapture(e.pointerId);
    });
    handle.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const dy = e.clientY - startY; if (Math.abs(dy) > 4) moved = true;
      const t = Math.min(panel.offsetHeight - 120, Math.max(0, startT + dy));
      panel.style.transform = `translateY(${t}px)`;
    });
    const end = (e) => {
      if (!dragging) return;
      dragging = false; panel.classList.remove("dragging");
      if (!moved) { sheet.set(sheet.state === "full" ? "peek" : sheet.state === "half" ? "full" : "half"); return; }
      const t = current(), h = panel.offsetHeight;
      const frac = 1 - t / h;                                        // share of the sheet that's showing
      sheet.set(frac > 0.72 ? "full" : frac > 0.32 ? "half" : "peek");
    };
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
    handle.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sheet.set(sheet.state === "full" ? "half" : "full"); } });
    $("place").addEventListener("focus", () => { if (sheet.mq.matches && sheet.state === "peek") sheet.set("half"); });
    map.on("dragstart", () => { if (sheet.mq.matches && sheet.state === "full") sheet.set("half"); });
    sheet.set("half");
    sheet.mq.addEventListener("change", () => { panel.style.transform = ""; if (sheet.mq.matches) sheet.set("half"); });
  })();

  // ------------------------------------------------------------ resizable list / map (desktop)
  // Drag the divider (or use arrow keys) to change the list's width; ‹ hides the list for a full-width map.
  const resizer = (function setupResizer() {
    const app = document.querySelector(".app"), panel = document.querySelector(".panel");
    const rz = $("resizer"), cb = $("collapseBtn");
    const MIN = 280;
    const max = () => Math.max(MIN, Math.min(900, Math.round(app.clientWidth * 0.7)));
    const collapsed = () => app.classList.contains("collapsed");
    let raf = 0;
    const refit = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => map.invalidateSize({ pan: false })); };
    function place() {
      const w = collapsed() ? 0 : panel.offsetWidth;
      rz.style.left = (w - 5) + "px";
      cb.style.left = w + "px";
      rz.setAttribute("aria-valuemin", MIN); rz.setAttribute("aria-valuemax", max()); rz.setAttribute("aria-valuenow", w);
    }
    function setW(w, save) {
      if (w == null) app.style.removeProperty("--panel-w");
      else app.style.setProperty("--panel-w", Math.min(max(), Math.max(MIN, Math.round(w))) + "px");
      place(); refit();
      if (save) store.set("cf-panel-w", w == null ? null : parseInt(app.style.getPropertyValue("--panel-w"), 10));
    }
    function setCollapsed(on, save) {
      app.classList.toggle("collapsed", on);
      cb.textContent = on ? "›" : "‹";
      cb.setAttribute("aria-expanded", String(!on));
      cb.setAttribute("aria-label", on ? "Show the list" : "Hide the list");
      cb.title = on ? "Show the list" : "Hide the list";
      place(); refit();
      if (save) store.set("cf-collapsed", on);
    }
    let startX = 0, startW = 0, dragging = false;
    rz.addEventListener("pointerdown", (e) => {
      if (sheet.mq.matches || e.button !== 0) return;
      dragging = true; startX = e.clientX; startW = panel.offsetWidth;
      rz.setPointerCapture(e.pointerId); app.classList.add("resizing"); e.preventDefault();
    });
    rz.addEventListener("pointermove", (e) => { if (dragging) setW(startW + e.clientX - startX); });
    const end = () => {
      if (!dragging) return;
      dragging = false; app.classList.remove("resizing");
      store.set("cf-panel-w", panel.offsetWidth);
    };
    rz.addEventListener("pointerup", end);
    rz.addEventListener("pointercancel", end);
    rz.addEventListener("dblclick", () => setW(null, true));
    rz.addEventListener("keydown", (e) => {
      const step = e.shiftKey ? 80 : 24, w = panel.offsetWidth;
      const next = { ArrowLeft: w - step, ArrowRight: w + step, Home: MIN, End: max() }[e.key];
      if (next !== undefined) { e.preventDefault(); setW(next, true); }
      else if (e.key === "Enter") { e.preventDefault(); setCollapsed(true, true); cb.focus(); }
    });
    cb.addEventListener("click", () => setCollapsed(!collapsed(), true));
    addEventListener("resize", () => {
      const w = parseInt(app.style.getPropertyValue("--panel-w"), 10);
      if (w > max()) setW(max()); else place();
    });
    sheet.mq.addEventListener("change", () => { place(); refit(); });
    const saved = store.get("cf-panel-w", null);
    if (typeof saved === "number") setW(saved);
    if (store.get("cf-collapsed", false) === true) setCollapsed(true);
    place();
    if (!sheet.mq.matches && !store.get("cf-resize-tip", false)) {
      setTimeout(() => { toast("Tip: drag the line between the list and the map to resize them"); store.set("cf-resize-tip", true); }, 2500);
    }
    // Opening a place brings the list back so its details can show.
    return { show() { if (collapsed() && !sheet.mq.matches) setCollapsed(false, true); } };
  })();

  // ------------------------------------------------------------ about
  $("aboutBtn").addEventListener("click", () => $("aboutDlg").showModal());
  $("aboutClose").addEventListener("click", () => $("aboutDlg").close());
  $("statPlaces").textContent = places.length.toLocaleString("en-IN");
  $("statAreas").textContent = (GEO.locs.length + GEO.zones.length).toLocaleString("en-IN") + "+";
  if (typeof SITE_MODE !== "undefined" && SITE_MODE) { $("areasLink").hidden = false; $("foodLink").hidden = false; }

  // ------------------------------------------------------------ keyboard on result cards
  $("list").addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && e.target.matches("li[data-id]")) { e.preventDefault(); openDetail(places[+e.target.dataset.id]); }
  });

  // ------------------------------------------------------------ report a problem (pre-filled GitHub issue)
  let reporting = null;
  function openReport(p) {
    if (!p) return;
    reporting = p;
    $("rpPlace").textContent = p.name;
    $("reportForm").reset();
    $("rpMsg").textContent = "";
    $("reportDlg").showModal();
  }
  function report() {
    const p = reporting;
    const what = [...document.querySelectorAll('#reportForm [name="rp"]:checked')].map((x) => x.value);
    const notes = $("rpNotes").value.trim();
    return {
      title: `Fix: ${p.name} (${p.loc === p.sub ? p.sub : p.loc + ", " + p.sub})${what.length ? " – " + what.join(", ") : ""}`,
      body: `**Place:** ${p.name}\n**Area:** ${p.loc === p.sub ? p.sub : p.loc + ", " + p.sub}\n**Link:** ${linkFor(p)}\n**Key:** ${p.key} · GPS ${p.lat.toFixed(5)}, ${p.lng.toFixed(5)}\n` +
        `**What's wrong:** ${what.join("; ") || "-"}\n**Details:** ${notes || "-"}\n\n_Reported from the website._`,
      ok: what.length > 0 || notes !== "",
    };
  }
  $("rpCancel").addEventListener("click", () => $("reportDlg").close());
  $("rpCopy").addEventListener("click", async () => {
    const r = report();
    try { await navigator.clipboard.writeText(`${r.title}\n\n${r.body.replace(/\*\*/g, "")}`); $("rpMsg").textContent = "Details copied. Paste them wherever you like to send them."; }
    catch (e) { $("rpMsg").textContent = "Copying isn't allowed here. Use Send on GitHub instead."; }
  });
  $("reportForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const r = report();
    if (!r.ok) { $("rpMsg").textContent = "Tick what's wrong or add a note."; return; }
    const a = document.createElement("a");
    a.href = `${REPO}/issues/new?` + new URLSearchParams({ title: r.title, body: r.body, labels: "data fix" });
    a.target = "_blank"; a.rel = "noopener"; document.body.appendChild(a); a.click(); a.remove();
    $("rpMsg").textContent = "GitHub opened in a new tab. Press “Submit new issue” there to send it. Thank you!";
  });

  // ------------------------------------------------------------ filters in the link (website only)
  // ?area=Bandra&cat=cafe&f=veg,open&mood=date&cuisine=Pizza&t=irani&sort=rating
  const SITE = typeof SITE_MODE !== "undefined" && SITE_MODE;
  const FLAGS = [["veg", "fVeg"], ["jain", "fJain"], ["nonveg", "fNon"], ["rated", "fRated"], ["open", "fOpen"]];
  function viewParams() {
    const ps = new URLSearchParams();
    if (state.area && state.area.names && state.areaName) ps.set("area", state.areaName);
    if (state.cat !== "all") ps.set("cat", state.cat);
    const f = FLAGS.filter(([, id]) => $(id).checked).map(([k]) => k);
    if (f.length) ps.set("f", f.join(","));
    if (state.mood) ps.set("mood", state.mood);
    if ($("cuisine").value) ps.set("cuisine", $("cuisine").value);
    const t = $("filterText").value.trim();
    if (t) ps.set("t", t);
    if ($("sortBy").value !== "near") ps.set("sort", $("sortBy").value);
    return ps;
  }
  let urlTimer;
  function syncUrl() {
    if (!SITE || !state.urlReady) return;
    clearTimeout(urlTimer);
    urlTimer = setTimeout(() => {
      const qs = viewParams().toString().replace(/%2C/g, ",");
      $("shareViewBtn").hidden = !qs;
      const url = location.pathname + (qs ? "?" + qs : "") + location.hash;
      if (url !== location.pathname + location.search + location.hash) { try { history.replaceState(null, "", url); } catch (e) { /* too many updates */ } }
    }, 250);
  }
  function applyUrl(ps) {
    if (ps.get("q")) smartSearch(ps.get("q"));
    else if (ps.get("area")) { $("place").value = ps.get("area"); showArea(ps.get("area")); }
    const cat = ps.get("cat");
    if (cat === "cafe" || cat === "rest") setCat(cat);
    const f = (ps.get("f") || "").split(",");
    FLAGS.forEach(([k, id]) => { if (f.includes(k)) $(id).checked = true; });
    if (MOODS[ps.get("mood")]) setMood(ps.get("mood"));
    const cu = ps.get("cuisine");
    if (cu && [...$("cuisine").options].some((o) => o.value === cu)) $("cuisine").value = cu;
    if (ps.get("t")) $("filterText").value = ps.get("t");
    const so = ps.get("sort");
    if (so && [...$("sortBy").options].some((o) => o.value === so)) $("sortBy").value = so;
    state.urlReady = true;
    state.shown = PAGE; render();
  }
  $("shareViewBtn").addEventListener("click", async () => {
    const url = location.href.split("#")[0];
    try { if (navigator.share) { await navigator.share({ title: document.title, url }); return; } } catch (e) { if (e && e.name === "AbortError") return; }
    try { await navigator.clipboard.writeText(url); toast("Link to this view copied"); } catch (e) { toast(url); }
  });

  // ------------------------------------------------------------ offline notice
  const syncNet = () => { $("netBanner").hidden = navigator.onLine !== false; };
  addEventListener("online", syncNet); addEventListener("offline", syncNet); syncNet();
