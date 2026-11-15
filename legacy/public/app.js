// Cafe & Restaurant Finder front end: crawls an area tile-by-tile through the local server,
// subdividing any tile where the source hit its result cap, and plots results.

const CITY = "mumbai";
const START_TILE_DEG = 0.05;  // initial grid cell (~5 km)
const MIN_TILE_DEG = 0.0025;  // stop subdividing below ~250 m
const CONCURRENCY = 4;
const MAX_CALLS = 3000;       // safety cap on paid API calls per crawl
const PAGE = 200;             // list rows rendered at a time

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const state = {
  source: "osm",
  cafes: new Map(),   // id -> cafe
  markers: new Map(), // id -> marker
  crawl: null,
  shown: PAGE,
  activeId: null,
  category: "all", // all | cafe | restaurant
};

// ---------------------------------------------------------------- map
const map = L.map("map", { zoomControl: true }).setView([19.07, 72.88], 11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
const cluster = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 50 });
map.addLayer(cluster);
const tileLayer = L.layerGroup().addTo(map);
const dot = (hi, cat) => L.divIcon({ className: "", html: `<div class="cafe-dot ${cat || "cafe"}${hi ? " hi" : ""}"></div>`, iconSize: hi ? [18, 18] : [14, 14] });
const catOf = (c) => c.category === "restaurant" ? "restaurant" : "cafe";
const catLabel = (c) => `<span class="cat ${catOf(c)}">${esc(c.kind || (catOf(c) === "cafe" ? "Cafe" : "Restaurant"))}</span>`;

// ---------------------------------------------------------------- links
const isGoogleId = (c) => !String(c.id).startsWith("osm/");
const placeQuery = (c) => {
  const q = `${c.name} ${c.address || ""}`.trim();
  return /mumbai/i.test(q) ? q : `${q} Mumbai`;
};

// Turn-by-turn navigation. Without an origin, Google Maps starts from the
// device's current GPS position (and opens the Maps app on phones).
function directionsUrl(c) {
  const p = new URLSearchParams({ api: "1", destination: `${c.lat},${c.lng}`, travelmode: "driving" });
  if (isGoogleId(c)) p.set("destination_place_id", c.id);
  if (state.me) p.set("origin", `${state.me.lat},${state.me.lng}`);
  return "https://www.google.com/maps/dir/?" + p;
}

// Prefer a real menu link from the data, then a Zomato search for this cafe.
function menuUrl(c) {
  if (c.menu) return c.menu;
  return "https://www.google.com/search?q=" + encodeURIComponent(`${placeQuery(c)} menu zomato`);
}

// Ratings exist only in Google data; in OSM mode link to the Google listing.
function ratingHtml(c) {
  if (c.rating) {
    return `<div class="line"><span class="lbl">Rating</span>
      <span class="star">${"★".repeat(Math.round(c.rating))}${"☆".repeat(5 - Math.round(c.rating))} ${c.rating.toFixed(1)}</span>
      <span class="muted">(${c.reviews.toLocaleString()} reviews)</span></div>`;
  }
  return `<div class="line"><span class="lbl">Rating</span>
    <span class="muted">Not in free map data ·</span>
    <a class="rate-link" href="${esc(c.url)}" target="_blank" rel="noopener">see on Google ★</a></div>`;
}

function foodHtml(c) {
  const d = c.diet || {};
  const t = [];
  if (d.pureVeg) t.push(`<span class="tag veg">● Pure veg</span>`);
  else {
    if (d.vegOptions) t.push(`<span class="tag veg">● Veg options</span>`);
    else if (d.vegOptions === false) t.push(`<span class="tag nonveg">No veg options</span>`);
    if (d.nonVeg) t.push(`<span class="tag nonveg">▲ Non-veg</span>`);
  }
  if (d.jain) t.push(`<span class="tag jain">Jain food</span>`);
  return `<div class="line"><span class="lbl">Food</span>${t.length ? t.join("") : `<span class="muted">Veg / non-veg not listed</span>`}</div>`;
}

function cuisineHtml(c) {
  const tags = c.cuisine.length
    ? c.cuisine.map((x) => `<span class="tag">${esc(x)}</span>`).join("")
    : `<span class="muted">Not listed</span>`;
  return `<div class="line"><span class="lbl">Cuisine</span>${tags}</div>`;
}

// Google gives a per-person price range; "for two" doubles it.
const PRICE_WORDS = ["Free", "Inexpensive", "Moderate", "Expensive", "Very expensive"];
const inr = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
function priceForTwo(c) {
  if (c.priceFrom != null) return c.priceTo != null ? `${inr(c.priceFrom * 2)}–${inr(c.priceTo * 2)}` : `${inr(c.priceFrom * 2)}+`;
  return null;
}
function priceHtml(c) {
  const two = priceForTwo(c);
  const body = two ? `<b>${two}</b> <span class="muted">for two</span>`
    : c.price != null ? `${"₹".repeat(Math.max(1, c.price))} <span class="muted">${PRICE_WORDS[c.price]}, no amount listed</span>`
    : `<span class="muted">Not listed</span>`;
  return `<div class="line"><span class="lbl">Price</span>${body}</div>`;
}

// Rank by rating, but trust ratings backed by more reviews: a 4.9 from 8
// people should not outrank a 4.6 from 3,000. (Bayesian average toward 4.0.)
const PRIOR_REVIEWS = 50, PRIOR_RATING = 4.0;
function score(c) {
  if (!c.rating) return -1;
  const v = c.reviews || 0;
  return (v * c.rating + PRIOR_REVIEWS * PRIOR_RATING) / (v + PRIOR_REVIEWS);
}

// Cheapest first; places with only a price level sort after real amounts, unpriced last.
const priceKey = (c) => c.priceFrom != null ? c.priceFrom : c.price != null ? 1e6 + c.price : 1e9;

// Fill the cuisine filter with what the current results contain.
function refreshCuisineFilter() {
  const sel = $("cuisine");
  const counts = new Map();
  for (const c of state.cafes.values()) if (state.category === "all" || catOf(c) === state.category) for (const x of c.cuisine) counts.set(x, (counts.get(x) || 0) + 1);
  const keep = sel.value;
  const opts = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  sel.innerHTML = `<option value="">All cuisines</option>` +
    opts.map(([x, n]) => `<option value="${esc(x)}">${esc(x)} (${n})</option>`).join("");
  sel.value = counts.has(keep) ? keep : "";
}

function distKm(c) {
  if (!state.me) return null;
  const R = 6371, rad = Math.PI / 180;
  const dLat = (c.lat - state.me.lat) * rad, dLng = (c.lng - state.me.lng) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(state.me.lat * rad) * Math.cos(c.lat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
const fmtKm = (d) => (d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`);

function actionsHtml(c) {
  return `<div class="actions">
    <a class="btn primary" href="${esc(directionsUrl(c))}" target="_blank" rel="noopener">➤ Directions</a>
    <a class="btn" href="${esc(menuUrl(c))}" target="_blank" rel="noopener">${c.menu ? "Menu" : "Find menu"}</a>
    <a class="btn" href="${esc(c.url)}" target="_blank" rel="noopener">Google Maps</a>
  </div>`;
}

function popupHtml(c) {
  const bits = [];
  const d = distKm(c);
  if (d != null) bits.push(`${fmtKm(d)} away`);
  return `<div class="pop"><h3>${esc(c.name)}</h3><p>${catLabel(c)}</p>
    ${ratingHtml(c)}${priceHtml(c)}${foodHtml(c)}${cuisineHtml(c)}
    ${bits.length ? `<p>${bits.join(" · ")}</p>` : ""}
    ${c.address ? `<p>${esc(c.address)}</p>` : ""}
    ${c.hours ? `<p>Hours: ${esc(c.hours)}</p>` : ""}
    ${c.phone ? `<p><a href="tel:${esc(c.phone)}">${esc(c.phone)}</a></p>` : ""}
    ${c.website ? `<p><a href="${esc(c.website)}" target="_blank" rel="noopener">Website</a></p>` : ""}
    <p class="gps">GPS: ${c.lat.toFixed(5)}, ${c.lng.toFixed(5)}</p>
    ${actionsHtml(c)}</div>`;
}

function addCafes(list) {
  const fresh = [];
  for (const c of list) {
    if (state.cafes.has(c.id) || c.lat == null) continue;
    if (!Array.isArray(c.cuisine)) c.cuisine = [];
    state.cafes.set(c.id, c);
    const m = L.marker([c.lat, c.lng], { icon: dot(false, catOf(c)), title: c.name }).bindPopup(() => popupHtml(c));
    m.on("click", () => highlight(c.id, false));
    m.cafeId = c.id;
    state.markers.set(c.id, m);
    fresh.push(m);
  }
  if (fresh.length) {
    cluster.addLayers(state.category === "all" ? fresh : fresh.filter((m) => catOf(state.cafes.get(m.cafeId)) === state.category));
    updateCategoryCounts();
  }
  return fresh.length;
}

function highlight(id, fly) {
  if (state.activeId && state.markers.has(state.activeId)) state.markers.get(state.activeId).setIcon(dot(false, catOf(state.cafes.get(state.activeId))));
  state.activeId = id;
  const m = state.markers.get(id);
  if (!m) return;
  m.setIcon(dot(true, catOf(state.cafes.get(id))));
  if (fly) cluster.zoomToShowLayer(m, () => m.openPopup());
  document.querySelectorAll("#list li").forEach((li) => li.classList.toggle("active", li.dataset.id === id));
}

// ---------------------------------------------------------------- list
function filtered() {
  const text = $("filterText").value.trim().toLowerCase();
  const min = parseFloat($("minRating").value);
  const open = $("openNow").checked;
  const cuisine = $("cuisine").value;
  const sort = $("sortBy").value;
  const ctr = state.me || map.getCenter();
  let rows = [...state.cafes.values()].filter((c) =>
    (!text || (c.name + " " + c.address).toLowerCase().includes(text)) &&
    (!min || (c.rating || 0) >= min) &&
    (!open || c.openNow === true) &&
    (!cuisine || c.cuisine.includes(cuisine)) &&
    (state.category === "all" || catOf(c) === state.category));
  const d = (c) => (c.lat - ctr.lat) ** 2 + ((c.lng - ctr.lng) * Math.cos(ctr.lat * Math.PI / 180)) ** 2;
  const cmp = {
    rating: (a, b) => score(b) - score(a) || b.reviews - a.reviews,
    priceLow: (a, b) => priceKey(a) - priceKey(b) || score(b) - score(a),
    reviews: (a, b) => b.reviews - a.reviews,
    name: (a, b) => a.name.localeCompare(b.name),
    distance: (a, b) => d(a) - d(b),
  }[sort];
  return rows.sort(cmp);
}

function updateCategoryCounts() {
  let cafe = 0, rest = 0;
  for (const c of state.cafes.values()) catOf(c) === "cafe" ? cafe++ : rest++;
  $("nAll").textContent = (cafe + rest).toLocaleString();
  $("nCafe").textContent = cafe.toLocaleString();
  $("nRest").textContent = rest.toLocaleString();
}

// Show only the chosen category's markers on the map.
function syncMarkers() {
  cluster.clearLayers();
  const keep = [];
  for (const [id, m] of state.markers) {
    if (state.category === "all" || catOf(state.cafes.get(id)) === state.category) keep.push(m);
  }
  cluster.addLayers(keep);
}

document.querySelectorAll(".seg [data-cat]").forEach((b) => b.addEventListener("click", () => {
  state.category = b.dataset.cat;
  document.querySelectorAll(".seg [data-cat]").forEach((x) => {
    x.classList.toggle("on", x === b);
    x.setAttribute("aria-checked", x === b);
  });
  state.shown = PAGE;
  refreshCuisineFilter();
  syncMarkers();
  render();
}));

let renderQueued = false;
function render() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(() => {
    renderQueued = false;
    const rows = filtered();
    const total = state.cafes.size;
    $("countLabel").textContent = total
      ? `${rows.length.toLocaleString()} of ${total.toLocaleString()} places`
      : state.crawl ? "Searching…" : "Nothing found yet";
    $("csvBtn").disabled = !rows.length;
    const ranked = $("sortBy").value === "rating";
    const html = rows.slice(0, state.shown).map((c, i) => { const d = distKm(c); return `
      <li data-id="${esc(c.id)}" class="${c.id === state.activeId ? "active" : ""}">
        <div class="name"><span>${ranked && c.rating ? `<span class="rank">#${i + 1}</span> ` : ""}${esc(c.name)} ${catLabel(c)}</span>${d != null ? `<span class="dist">${fmtKm(d)}</span>` : ""}</div>
        ${ratingHtml(c)}${priceHtml(c)}${foodHtml(c)}${cuisineHtml(c)}
        <div class="meta">
          ${c.openNow === true ? `<span class="open">Open now</span>` : c.openNow === false ? `<span class="closed">Closed</span>` : ""}
        </div>
        ${c.address ? `<div class="addr">${esc(c.address)}</div>` : ""}
        ${actionsHtml(c)}
      </li>`; }).join("");
    $("list").innerHTML = html + (rows.length > state.shown
      ? `<li class="more"><button type="button" class="link" id="moreBtn">Show more (${(rows.length - state.shown).toLocaleString()} left)</button></li>` : "");
  });
}

$("list").addEventListener("click", (e) => {
  if (e.target.id === "moreBtn") { state.shown += PAGE; return render(); }
  if (e.target.closest("a")) return; // let Directions / Menu links open normally
  const li = e.target.closest("li[data-id]");
  if (li) highlight(li.dataset.id, true);
});
["filterText", "minRating", "sortBy", "openNow", "cuisine"].forEach((id) =>
  $(id).addEventListener("input", () => { state.shown = PAGE; render(); }));
map.on("moveend", () => { if ($("sortBy").value === "distance") render(); });

$("csvBtn").addEventListener("click", () => {
  const cols = ["name", "category", "kind", "address", "lat", "lng", "rating", "reviews", "cuisine", "price", "priceFrom", "priceTo", "phone", "website", "url"];
  const q = (v) => `"${String(Array.isArray(v) ? v.join("; ") : v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...filtered().map((c) => cols.map((k) => q(c[k])).join(","))].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv" }));
  a.download = `${state.category === "all" ? "cafes-and-restaurants" : state.category === "cafe" ? "cafes" : "restaurants"}-${CITY}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
});

// ---------------------------------------------------------------- crawl
function setStatus(msg, err) {
  $("status").textContent = msg;
  $("status").classList.toggle("err", !!err);
}

function gridTiles(b, step) {
  const rows = Math.max(1, Math.ceil((b.n - b.s) / step));
  const cols = Math.max(1, Math.ceil((b.e - b.w) / step));
  const dh = (b.n - b.s) / rows, dw = (b.e - b.w) / cols;
  const out = [];
  for (let i = 0; i < rows; i++)
    for (let j = 0; j < cols; j++)
      out.push({ s: b.s + i * dh, n: b.s + (i + 1) * dh, w: b.w + j * dw, e: b.w + (j + 1) * dw });
  return out;
}

function split(t) {
  const mlat = (t.s + t.n) / 2, mlng = (t.w + t.e) / 2;
  return [
    { s: t.s, n: mlat, w: t.w, e: mlng }, { s: t.s, n: mlat, w: mlng, e: t.e },
    { s: mlat, n: t.n, w: t.w, e: mlng }, { s: mlat, n: t.n, w: mlng, e: t.e },
  ];
}

function drawTile(t, kind) {
  const style = {
    pending: { color: "#8a4b22", weight: 1, dashArray: "3 4", fillOpacity: 0 },
    done: { color: "#8a4b22", weight: 0.6, fillColor: "#8a4b22", fillOpacity: 0.06 },
    split: { color: "#e0661b", weight: 0.6, fillOpacity: 0 },
    error: { color: "#c0392b", weight: 1.2, fillColor: "#c0392b", fillOpacity: 0.15 },
  }[kind];
  if (t.rect) t.rect.setStyle(style);
  else t.rect = L.rectangle([[t.s, t.w], [t.n, t.e]], { ...style, interactive: false }).addTo(tileLayer);
}

async function crawl(bbox, label) {
  if (state.crawl) state.crawl.stopped = true;
  const job = { stopped: false, queue: [], done: 0, total: 0, calls: 0, errors: 0, label };
  state.crawl = job;
  tileLayer.clearLayers();
  cluster.clearLayers();
  state.cafes.clear();
  state.markers.clear();
  state.shown = PAGE;
  state.activeId = null;
  refreshCuisineFilter();
  updateCategoryCounts();

  map.fitBounds([[bbox.s, bbox.w], [bbox.n, bbox.e]], { padding: [20, 20] });
  // OpenStreetMap returns everything in one query; Google needs tiling.
  job.queue = state.source === "google" ? gridTiles(bbox, START_TILE_DEG) : [{ ...bbox }];
  job.total = job.queue.length;
  job.queue.forEach((t) => drawTile(t, "pending"));
  $("progress").hidden = false;
  $("stopBtn").hidden = false;
  setStatus(`Searching ${label}…`);
  updateStats(job);

  const worker = async () => {
    while (!job.stopped && job.queue.length) {
      if (job.calls >= MAX_CALLS) { job.stopped = true; setStatus(`Stopped at the ${MAX_CALLS} API-call safety cap. Narrow the area for a full sweep.`, true); break; }
      const t = job.queue.shift();
      try {
        const res = await fetch(`/api/tile?s=${t.s}&w=${t.w}&n=${t.n}&e=${t.e}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || res.statusText);
        if (job.stopped || state.crawl !== job) return;
        if (!data.cached) job.calls += data.calls || 0;
        if (addCafes(data.places)) refreshCuisineFilter();
        if (data.saturated && t.n - t.s > MIN_TILE_DEG) {
          // This tile hit the result cap: there may be more places, so look closer.
          drawTile(t, "split");
          const kids = split(t);
          kids.forEach((k) => drawTile(k, "pending"));
          job.queue.unshift(...kids);
          job.total += kids.length;
        } else {
          drawTile(t, "done");
        }
      } catch (err) {
        if (state.crawl !== job) return;
        job.errors++;
        job.lastError = err.message;
        drawTile(t, "error");
        setStatus(`Error: ${err.message}`, true);
      }
      job.done++;
      updateStats(job);
      render();
    }
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
  if (state.crawl !== job) return;
  $("stopBtn").hidden = true;
  if (!job.stopped) {
    const n = state.cafes.size.toLocaleString();
    setStatus(job.errors
      ? `${job.errors} tile(s) failed (red on the map): ${job.lastError} Found ${n} places in ${label}.`
      : `Done: ${n} places in ${label}.`, !!job.errors);
  }
  state.crawl = null;
  render();
}

function updateStats(job) {
  $("stFound").textContent = state.cafes.size.toLocaleString();
  $("stTiles").textContent = job.done;
  $("stTotal").textContent = job.total;
  $("stCalls").textContent = job.calls;
  $("barFill").style.width = `${job.total ? (100 * job.done) / job.total : 0}%`;
}

$("stopBtn").addEventListener("click", () => {
  if (!state.crawl) return;
  state.crawl.stopped = true;
  setStatus(`Stopped. Showing ${state.cafes.size.toLocaleString()} places found so far.`);
  $("stopBtn").hidden = true;
});

async function searchPlace(q) {
  $("place").value = q;
  setStatus("Locating…");
  $("progress").hidden = false;
  try {
    const res = await fetch(`/api/geocode?city=${CITY}&q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    crawl(data.bbox, data.name);
  } catch (err) {
    setStatus(err.message, true);
  }
}

$("searchForm").addEventListener("submit", (e) => { e.preventDefault(); searchPlace($("place").value); });
document.querySelectorAll(".quick [data-q]").forEach((b) => b.addEventListener("click", () => searchPlace(b.dataset.q)));
$("viewBtn").addEventListener("click", () => {
  const b = map.getBounds();
  $("place").value = "";
  crawl({ s: b.getSouth(), w: b.getWest(), n: b.getNorth(), e: b.getEast() }, "this map view");
});

// ---------------------------------------------------------------- GPS
let meMarker = null;
$("meBtn").addEventListener("click", () => {
  if (!navigator.geolocation) return setStatus("This browser can't share its location.", true);
  $("progress").hidden = false;
  setStatus("Getting your location…");
  navigator.geolocation.getCurrentPosition((pos) => {
    state.me = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    if (meMarker) meMarker.remove();
    meMarker = L.circleMarker([state.me.lat, state.me.lng], {
      radius: 8, color: "#fff", weight: 3, fillColor: "#1a73e8", fillOpacity: 1,
    }).addTo(map).bindTooltip("You are here");
    L.circle([state.me.lat, state.me.lng], { radius: Math.min(pos.coords.accuracy, 500), color: "#1a73e8", weight: 1, fillOpacity: 0.1, interactive: false }).addTo(map);
    map.setView([state.me.lat, state.me.lng], 15);
    $("sortBy").value = "distance";
    $("meBtn").textContent = "📍 Near me ✓";
    setStatus(state.cafes.size ? "Sorted by distance from you." : "Location found. Search an area to see places near you.");
    state.shown = PAGE;
    render();
  }, (err) => setStatus(`Couldn't get your location: ${err.message}`, true),
  { enableHighAccuracy: true, timeout: 15000 });
});

// ---------------------------------------------------------------- boot
(async () => {
  const cfg = await fetch("/api/config").then((r) => r.json());
  state.source = cfg.source;
  const badge = $("sourceBadge");
  badge.textContent = cfg.source === "google" ? "Google Places" : "OpenStreetMap demo";
  badge.className = "badge " + cfg.source;
  badge.title = cfg.source === "google"
    ? "Live data from the Google Places API"
    : "No Google API key set. Showing OpenStreetMap data. Add GOOGLE_MAPS_API_KEY to use Google Maps data.";
  render();
})();
