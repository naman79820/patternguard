"""Capture screenshots for Appendix C: extension highlights on demo and case pages,
the toolbar popup with the Manipulation Score, and the fair page with no detections."""
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from pg_harness import serve_repo, launch, clear_storage, wait_summary, now_ms  # noqa: E402

OUT = ROOT / "report" / "screenshots"


def popup(ctx, page, name):
    url = page.url
    tab_id = ctx.pg_sw.evaluate("""async (u) => { const all = await chrome.storage.local.get(null);
        const k = Object.keys(all).find(k => k.startsWith('pg:tab:') && all[k].href === u); return parseInt(k.slice(7), 10); }""", url)
    p = ctx.new_page()
    p.set_viewport_size({"width": 360, "height": 520})
    p.goto(f"chrome-extension://{ctx.pg_ext_id}/popup.html?tab={tab_id}")
    p.wait_for_selector("#S")
    time.sleep(0.5)
    p.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    p.close()


def main():
    with serve_repo() as base, launch() as ctx:
        clear_storage(ctx)
        page = ctx.new_page()
        t = now_ms(); page.goto(f"{base}/demo/dark-checkout.html"); wait_summary(page, after_ms=t, settle=0.5)
        time.sleep(7)
        t = now_ms(); page.reload(); s = wait_summary(page, after_ms=t, settle=0.5)
        page.screenshot(path=str(OUT / "appc_dark_checkout_reload.png"), full_page=True)
        popup(ctx, page, "appc_popup_dark_checkout")
        print("dark-checkout after reload:", len(s["detections"]), "S =", s["manipulationScore"])

        clear_storage(ctx)
        t = now_ms(); page.goto(f"{base}/demo/fair-checkout.html"); s = wait_summary(page, after_ms=t, settle=0.5)
        page.screenshot(path=str(OUT / "appc_fair_checkout.png"), full_page=True)
        popup(ctx, page, "appc_popup_fair_checkout")
        print("fair-checkout:", len(s["detections"]), "S =", s["manipulationScore"])

        clear_storage(ctx)
        t = now_ms(); page.goto(f"{base}/demo/spa-booking.html#review"); wait_summary(page, after_ms=t, settle=0.3)
        t = now_ms(); page.click("#to-addons"); s = wait_summary(page, after_ms=t, href_contains="#addons", settle=3.5)
        page.screenshot(path=str(OUT / "appc_spa_addons.png"), full_page=True)
        print("spa #addons:", len(s["detections"]))
    print("saved to", OUT)


if __name__ == "__main__":
    main()
