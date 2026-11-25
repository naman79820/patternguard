"""PatternGuard regression test.

Loads the unpacked extension in Chromium (new headless mode), serves the repository
with http.server and checks every expected detection count on the demo pages (and on
the reconstructed case pages listed in tests/cases_expected.json, if present).
Exit code 0 = all checks passed.

Usage:  python tests/regression.py [--ext PATH] [--json OUT]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_harness import ROOT, EXT, serve_repo, launch, clear_storage, wait_summary, now_ms, categories  # noqa: E402

RESULTS = []


def check(name, actual, expected):
    ok = actual == expected
    RESULTS.append({"check": name, "expected": expected, "actual": actual, "pass": ok})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: expected {expected}, got {actual}")
    return ok


def goto(page, url, settle=0.5):
    t = now_ms()
    page.goto(url)
    return wait_summary(page, after_ms=t, settle=settle)


def hash_nav(page, selector, frag, settle=3.5):
    t = now_ms()
    page.click(selector)
    return wait_summary(page, after_ms=t, href_contains=frag, settle=settle)


def demo_checks(ctx, base):
    page = ctx.new_page()

    # dark-checkout: 4 on first load, no redraws over 8 s idle, 5 after one reload
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/dark-checkout.html")
    check("dark-checkout first load: count", len(s["detections"]), 4)
    check("dark-checkout first load: categories", categories(s),
          ["basket_sneaking", "confirm_shaming", "interface_interference", "trick_question"])
    r0, n0 = s["redrawCount"], s["scanCount"]
    time.sleep(8)
    s = wait_summary(page)
    check("dark-checkout: automatic redraws during 8 s idle", s["redrawCount"] - r0, 0)
    check("dark-checkout: automatic rescans during 8 s idle", s["scanCount"] - n0, 0)
    t = now_ms()
    page.reload()
    s = wait_summary(page, after_ms=t, settle=0.5)
    check("dark-checkout after one reload: count", len(s["detections"]), 5)
    check("dark-checkout after one reload: has false_urgency", "false_urgency" in categories(s), True)

    # fair-checkout: 0, also after reload
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/fair-checkout.html")
    check("fair-checkout first load: count", len(s["detections"]), 0)
    time.sleep(6)
    t = now_ms()
    page.reload()
    s = wait_summary(page, after_ms=t, settle=0.5)
    check("fair-checkout after reload: count", len(s["detections"]), 0)

    # spa-booking: 0 on review, 3 on #addons, 1 on #payment
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/spa-booking.html#review")
    check("spa-booking #review: count", len(s["detections"]), 0)
    s = hash_nav(page, "#to-addons", "#addons")
    check("spa-booking #addons: count", len(s["detections"]), 3)
    check("spa-booking #addons: categories", categories(s), ["basket_sneaking", "basket_sneaking", "confirm_shaming"])
    s = hash_nav(page, "#to-payment", "#payment")
    check("spa-booking #payment: count", len(s["detections"]), 1)
    check("spa-booking #payment: categories", categories(s), ["drip_pricing"])

    # spa-booking: user ticks the options themselves -> only confirm shaming remains
    page.close()
    page = ctx.new_page()
    clear_storage(ctx)
    goto(page, f"{base}/demo/spa-booking.html#review")
    hash_nav(page, "#to-addons", "#addons")
    t = now_ms()
    for sel in ["#insurance", "#insurance", "#priority", "#priority"]:  # untick and tick again
        page.click(sel)
    s = wait_summary(page, after_ms=t, settle=3.5)
    check("spa-booking #addons after user ticks options: categories", categories(s), ["confirm_shaming"])
    page.close()


def case_checks(ctx, base):
    exp_path = ROOT / "tests" / "cases_expected.json"
    if not exp_path.exists():
        return
    expected = json.loads(exp_path.read_text(encoding="utf-8"))
    page = ctx.new_page()
    for case in expected["cases"]:
        clear_storage(ctx)
        s = goto(page, f"{base}/demo/cases/{case['file']}")
        for step in case["steps"]:
            if step.get("action"):
                s = hash_nav(page, step["action"]["click"], step["action"]["wait_for"])
            check(f"{case['file']} {step['name']}: categories", categories(s), sorted(e["category"] for e in step["expected"]))
    page.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", default=str(EXT))
    ap.add_argument("--json", default=str(ROOT / "report" / "regression_result.json"))
    args = ap.parse_args()
    with serve_repo() as base, launch(args.ext) as ctx:
        demo_checks(ctx, base)
        case_checks(ctx, base)
    failed = [r for r in RESULTS if not r["pass"]]
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps({"passed": len(RESULTS) - len(failed), "failed": len(failed),
                                           "checks": RESULTS}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRegression: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
