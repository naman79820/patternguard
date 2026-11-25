"""Record the demo video (media/patternguard_demo.webm) and a short preview GIF
(media/patternguard_demo.gif) with the real extension loaded in Chromium.

Only local pages are opened (the repository is served on 127.0.0.1). Captions are
drawn inside a shadow root, which the content script does not scan, and are added
after the page's first scan, so they do not change any detection.

Usage:  .venv\\Scripts\\python tools\\demo_video.py
"""
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from pg_harness import EXT, serve_repo, wait_summary, now_ms  # noqa: E402

OUT = ROOT / "media"
W, H = 1280, 720
frames = []

CARD = """<html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#0f172a;color:#e2e8f0;font-family:Segoe UI,Arial,sans-serif">
<div style="max-width:980px;padding:40px">
<div style="color:#38bdf8;font-size:22px;letter-spacing:2px;text-transform:uppercase">{kicker}</div>
<div style="font-size:48px;font-weight:700;margin:12px 0 24px">{title}</div>
<div style="font-size:24px;line-height:1.6;color:#cbd5e1">{body}</div>
</div></body></html>"""

CAPTION_JS = """(t) => {
  let host = document.getElementById('pg-demo-caption');
  if (!host) {
    host = document.createElement('div');
    host.id = 'pg-demo-caption';
    host.style.cssText = 'position:fixed;left:0;right:0;bottom:24px;z-index:2147483647;pointer-events:none;display:flex;justify-content:center';
    host.attachShadow({mode: 'open'});
    document.documentElement.appendChild(host);
  }
  host.shadowRoot.innerHTML = '<div style="max-width:1100px;background:rgba(15,23,42,.92);color:#f8fafc;' +
    'font:500 21px Segoe UI,Arial,sans-serif;padding:12px 22px;border-radius:10px;border-left:6px solid #38bdf8">' + t + '</div>';
}"""


def card(page, kicker, title, body, secs=4.0):
    if not page.url.startswith(("about:", "http")):
        page.goto("about:blank")
    page.set_content(CARD.format(kicker=kicker, title=title, body=body))
    snap(page)
    time.sleep(secs)


def caption(page, text, secs=0.0):
    try:
        page.evaluate(CAPTION_JS, text)
    except Exception:
        pass
    if secs:
        time.sleep(secs)


def snap(page):
    p = Path(tempfile.mkdtemp()) / "f.png"
    page.screenshot(path=str(p))
    frames.append(Image.open(p).convert("RGB").resize((960, 540), Image.LANCZOS))


def scroll(page, total_secs=4.0, steps=40):
    h = page.evaluate("document.documentElement.scrollHeight - innerHeight")
    for i in range(1, steps + 1):
        page.evaluate(f"scrollTo(0, {int(h * i / steps)})")
        time.sleep(total_secs / steps)


def show_popup(page, ctx_sw, ext_id, url, text):
    tab_id = ctx_sw.evaluate("""async (u) => { const all = await chrome.storage.local.get(null);
        const k = Object.keys(all).find(k => k.startsWith('pg:tab:') && all[k].href === u); return parseInt(k.slice(7), 10); }""", url)
    page.goto(f"chrome-extension://{ext_id}/popup.html?tab={tab_id}")
    page.wait_for_selector("#S")
    page.evaluate("""() => { document.documentElement.style.background = '#e2e8f0';
        document.body.style.cssText += ';zoom:1.35;width:360px;margin:20px auto;background:#fff;box-shadow:0 8px 30px rgba(0,0,0,.25);border-radius:8px'; }""")
    caption(page, text)
    time.sleep(0.6)
    snap(page)
    time.sleep(5)


def main():
    OUT.mkdir(exist_ok=True)
    vid_dir = Path(tempfile.mkdtemp(prefix="pg-video-"))
    user_dir = tempfile.mkdtemp(prefix="pg-profile-")
    with serve_repo() as base, sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_dir, channel="chromium", headless=True,
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
            viewport={"width": W, "height": H},
            record_video_dir=str(vid_dir), record_video_size={"width": W, "height": H})
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
        ext_id = sw.url.split("/")[2]
        sw.evaluate("chrome.storage.local.clear()")
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        card(page, "Minor Project ES-451", "PatternGuard",
             "A Chrome extension that finds dark patterns on shopping and travel pages and maps each one "
             "to the 13 categories in India's CCPA Dark Patterns Guidelines, 2023.<br><br>"
             "This video shows how to set it up and run it.", 5)
        card(page, "Step 1", "Get the code and serve it",
             "<code>git clone https://github.com/naman79820/patternguard</code><br>"
             "<code>cd patternguard</code><br>"
             "<code>python -m http.server 8000</code><br><br>"
             "The demo pages must be opened over http, not as files.", 5)
        card(page, "Step 2", "Load the extension",
             "Open <code>chrome://extensions</code>, turn on <b>Developer mode</b>, click "
             "<b>Load unpacked</b> and choose the <code>extension/</code> folder.", 4)

        page.goto("chrome://extensions")
        time.sleep(1.5)
        snap(page)
        time.sleep(3)

        card(page, "Step 3", "Open a page with dark patterns",
             "<code>http://localhost:8000/demo/dark-checkout.html</code><br><br>"
             "PatternGuard scans the page when it loads and highlights what it finds.", 4)
        url = f"{base}/demo/dark-checkout.html"
        t = now_ms(); page.goto(url); s = wait_summary(page, after_ms=t, settle=0.5)
        caption(page, f"Dark checkout demo: {len(s['detections'])} detections on the first load. Each box names the CCPA category.")
        snap(page)
        time.sleep(2)
        scroll(page, 5)
        snap(page)
        caption(page, "The countdown timer is checked across reloads. Waiting a few seconds, then reloading...", 5)
        page.evaluate("scrollTo(0,0)")
        t = now_ms(); page.reload(); s = wait_summary(page, after_ms=t, settle=0.5)
        caption(page, f"After the reload the timer started again from the top, so false urgency is reported too: {len(s['detections'])} detections.")
        snap(page)
        time.sleep(4)
        show_popup(page, sw, ext_id, url,
                   f"The toolbar popup lists every finding and the site's Manipulation Score S = {s['manipulationScore']}.")

        card(page, "Step 4", "Compare with a fair page",
             "<code>http://localhost:8000/demo/fair-checkout.html</code><br><br>"
             "Same shop, same products, no manipulative design.", 3)
        sw.evaluate("chrome.storage.local.clear()")
        url = f"{base}/demo/fair-checkout.html"
        t = now_ms(); page.goto(url); s = wait_summary(page, after_ms=t, settle=0.5)
        caption(page, f"Fair checkout: {len(s['detections'])} detections.")
        snap(page)
        time.sleep(3)
        show_popup(page, sw, ext_id, url, f"The popup shows S = {s['manipulationScore']} for the fair page.")

        card(page, "Step 5", "Multi-step booking flow",
             "<code>http://localhost:8000/demo/spa-booking.html</code><br><br>"
             "A single-page app. PatternGuard rescans when the page changes and remembers earlier steps.", 4)
        sw.evaluate("chrome.storage.local.clear()")
        t = now_ms(); page.goto(f"{base}/demo/spa-booking.html#review"); s = wait_summary(page, after_ms=t, settle=0.3)
        caption(page, f"Review step: {len(s['detections'])} detections. Clicking Continue...", 3)
        snap(page)
        t = now_ms(); page.click("#to-addons"); s = wait_summary(page, after_ms=t, href_contains="#addons", settle=3.5)
        caption(page, f"Add-ons step: {len(s['detections'])} detections, found after the page changed without a reload.")
        snap(page)
        time.sleep(4)

        card(page, "Step 6", "Reconstructed CCPA cases",
             "<code>http://localhost:8000/demo/cases/</code><br><br>"
             "Five pages that rebuild practices from CCPA actions, with made-up shop names.", 3)
        sw.evaluate("chrome.storage.local.clear()")
        t = now_ms(); page.goto(f"{base}/demo/cases/case2_airline_risk.html"); s = wait_summary(page, after_ms=t, settle=0.5)
        caption(page, f"Case 2, an airline booking: step 1 has {len(s['detections'])} detections. Clicking Continue...", 3)
        t = now_ms(); page.click("#to-addons"); s = wait_summary(page, after_ms=t, settle=3.5)
        caption(page, f"Add-on step: the opt-out 'No I will take risk' is reported as confirm shaming. Detections: {len(s['detections'])}.")
        snap(page)
        time.sleep(5)

        card(page, "Step 7", "Run the tests",
             "<code>py -3.12 -m venv .venv</code><br>"
             "<code>.venv\\Scripts\\python -m pip install playwright pandas scikit-learn matplotlib numpy python-docx</code><br>"
             "<code>.venv\\Scripts\\python -m playwright install chromium</code><br>"
             "<code>powershell -ExecutionPolicy Bypass -File tests\\run_all.ps1</code><br><br>"
             "Full steps are in SETUP.md in the repository.", 6)
        video = page.video
        ctx.close()
        src = Path(video.path())
    shutil.copy(src, OUT / "patternguard_demo.webm")
    shutil.rmtree(vid_dir, ignore_errors=True)
    shutil.rmtree(user_dir, ignore_errors=True)
    frames[0].save(OUT / "patternguard_demo.gif", save_all=True, append_images=frames[1:],
                   duration=2200, loop=0, optimize=True)
    for f in ("patternguard_demo.webm", "patternguard_demo.gif"):
        print(f, round((OUT / f).stat().st_size / 1e6, 2), "MB")
    print("frames in gif:", len(frames))


if __name__ == "__main__":
    main()
