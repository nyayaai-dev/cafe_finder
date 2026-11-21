"""The install page (site/install.html): one link to send to a phone.

- Android (Chrome, Edge, Samsung Internet): an "Install app" button that opens the
  phone's own install prompt; if the browser hasn't offered it yet, the menu steps.
- iPhone / iPad (Safari): the Share -> Add to Home Screen steps.
- Computer: a QR code to scan with the phone.
- Already installed: says so, with a button to open it.

The page links the web app manifest and registers the service worker, so the
browser treats it as part of the installable app."""
import html
import os

ESC = html.escape


def build_install(site_dir, cfg):
    base = cfg["site_url"].rstrip("/") + "/"
    name = cfg["site_name"]
    url = base + "install.html"
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Get the app · {ESC(name)}</title>
<meta name="description" content="Install the Mumbai Cafe &amp; Restaurant Finder on your phone: free, no app store, works offline.">
<link rel="canonical" href="{ESC(url)}">
<meta property="og:title" content="Get the Mumbai Cafe Finder app"><meta property="og:description" content="Free, no app store needed. Tap to install on your phone.">
<meta property="og:image" content="{ESC(base)}og.png"><meta property="og:url" content="{ESC(url)}"><meta name="twitter:card" content="summary_large_image">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#c2410c">
<link rel="icon" href="icons/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Cafe Finder">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=Inter:wght@400;600;700&display=swap">
<style>
:root {{ --bg:#f7f5f2; --panel:#fff; --ink:#241a14; --muted:#76675c; --line:#e7e0d9; --chip:#f1ece6; --accent:#c2410c; --ok:#1e8a3c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#15110e; --panel:#1d1814; --ink:#f0e7de; --muted:#a8998c; --line:#352c25; --chip:#2a231d; --accent:#e0703a; --ok:#5cc77c; color-scheme: dark; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; }}
.wrap {{ max-width: 560px; margin: 0 auto; padding: 32px max(16px, env(safe-area-inset-left, 0px)) 48px; }}
.app {{ display: flex; gap: 16px; align-items: center; }}
.app img {{ width: 76px; height: 76px; border-radius: 18px; box-shadow: 0 6px 18px rgba(0,0,0,.18); }}
h1 {{ font: 700 clamp(24px, 6vw, 30px)/1.15 "Bricolage Grotesque", system-ui, sans-serif; margin: 0; letter-spacing: -.01em; }}
.sub {{ color: var(--muted); margin: 4px 0 0; font-size: 14px; }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 20px; margin-top: 24px; }}
.big {{ display: flex; width: 100%; justify-content: center; align-items: center; gap: 10px; border: 0; border-radius: 12px; padding: 16px;
        background: var(--accent); color: #fff; font: 700 18px "Inter", system-ui, sans-serif; cursor: pointer; text-decoration: none; }}
.big.ghost {{ background: var(--chip); color: var(--ink); font-size: 15px; padding: 12px; margin-top: 10px; }}
ol {{ padding-left: 22px; margin: 10px 0 0; }} li {{ margin: 8px 0; }}
.key {{ display: inline-flex; align-items: center; gap: 4px; background: var(--chip); border: 1px solid var(--line); border-radius: 6px; padding: 0 7px; font-weight: 600; white-space: nowrap; }}
.key svg {{ width: 16px; height: 16px; }}
.ok {{ color: var(--ok); font-weight: 700; }}
.perks {{ list-style: none; padding: 0; margin: 18px 0 0; display: grid; gap: 6px; font-size: 14px; color: var(--muted); }}
.perks li {{ margin: 0; }}
#qr {{ display: flex; justify-content: center; padding: 12px; background: #fff; border-radius: 12px; width: max-content; margin: 12px auto 0; }}
.muted {{ color: var(--muted); font-size: 14px; }}
h2 {{ font: 700 18px/1.2 "Bricolage Grotesque", system-ui, sans-serif; margin: 0 0 6px; }}
[hidden] {{ display: none !important; }}
a {{ color: var(--accent); }}
</style>
</head><body><div class="wrap">
<div class="app"><img src="icons/icon-192.png" alt="" width="76" height="76">
  <div><h1>Mumbai Cafe Finder</h1><p class="sub">Free · no app store · works offline · under 5 MB</p></div></div>

<div class="card" id="installed" hidden>
  <h2 class="ok">✓ It's installed</h2>
  <p class="muted">Open it from your home screen or app drawer any time.</p>
  <a class="big" href="./">Open the app</a>
</div>

<div class="card" id="android" hidden>
  <button class="big" id="installNow" type="button" hidden>📲 Install app</button>
  <div id="androidSteps">
    <h2>Install in 2 taps</h2>
    <ol>
      <li>Tap the <span class="key">⋮</span> menu at the top-right of Chrome.</li>
      <li>Tap <b>Install app</b> (or <b>Add to Home screen</b>), then <b>Install</b>.</li>
    </ol>
    <p class="muted">Using another browser? Open this page in Chrome for the quickest install.</p>
  </div>
  <p id="doneMsg" class="ok" hidden>✓ Installing… you'll find it on your home screen.</p>
</div>

<div class="card" id="ios" hidden>
  <h2>Install on iPhone</h2>
  <ol>
    <li>Open this page in <b>Safari</b>.</li>
    <li>Tap the <span class="key"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>Share</span> button (bottom of the screen).</li>
    <li>Scroll down and tap <b>Add to Home Screen</b>, then <b>Add</b>.</li>
  </ol>
</div>

<div class="card" id="desktop" hidden>
  <h2>Scan with your phone</h2>
  <p class="muted">Point your phone's camera at the code, open the link, and follow the steps there.</p>
  <div id="qr" role="img" aria-label="QR code for {ESC(url)}"></div>
  <p class="muted" style="text-align:center;margin-top:10px">or send yourself this link:<br><b>{ESC(url)}</b></p>
  <button class="big ghost" id="installDesktop" type="button" hidden>💻 Install on this computer</button>
</div>

<ul class="perks">
  <li>🗺️ Opens full-screen like a normal app, straight from your home screen</li>
  <li>📶 Works offline after the first visit; updates itself</li>
  <li>🔒 No sign-up, no ads, no tracking; saved places stay on your phone</li>
</ul>
<p class="muted" style="margin-top:22px"><a href="./">← Back to the map</a></p>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
(() => {{
  const $ = (id) => document.getElementById(id);
  const ua = navigator.userAgent;
  const ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const mobile = ios || /Android|Mobi/i.test(ua);
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (standalone) {{ $("installed").hidden = false; return; }}
  if (ios) $("ios").hidden = false;
  else if (mobile) $("android").hidden = false;
  else {{
    $("desktop").hidden = false;
    try {{ new QRCode($("qr"), {{ text: {url!r}, width: 196, height: 196, correctLevel: QRCode.CorrectLevel.M }}); }}
    catch (e) {{ $("qr").textContent = "QR code unavailable offline."; }}
  }}
  let prompt = null;
  addEventListener("beforeinstallprompt", (e) => {{
    e.preventDefault(); prompt = e;
    if (mobile) {{ $("installNow").hidden = false; $("androidSteps").hidden = true; }}
    else $("installDesktop").hidden = false;
  }});
  const go = async () => {{
    if (!prompt) return;
    prompt.prompt();
    const r = await prompt.userChoice.catch(() => null);
    prompt = null;
    if (r && r.outcome === "accepted") {{ $("installNow").hidden = true; $("installDesktop").hidden = true; $("doneMsg").hidden = false; }}
  }};
  $("installNow").addEventListener("click", go);
  $("installDesktop").addEventListener("click", go);
  addEventListener("appinstalled", () => {{ $("android").hidden = true; $("desktop").hidden = true; $("installed").hidden = false; }});
  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => {{}});
}})();
</script>
</body></html>
"""
    open(os.path.join(site_dir, "install.html"), "w", encoding="utf-8").write(page)
    return url
