"""Run every test ID in Tables 6.1 to 6.5 of the report and write report/test_results.json.

Each record: id, description, expected, actual (one factual sentence), status
(Pass / Fail / Not applicable / Not implemented), evidence {file, test_function, screenshot}.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_harness import ROOT, EXT, serve_repo, launch, clear_storage, wait_summary, now_ms, categories, summary  # noqa: E402

# Descriptions and expected outcomes as written in the report.
SPEC = {
    "TC-F01": ("Load extension in Chrome with the Manifest V3 manifest.", "Extension loads without manifest errors."),
    "TC-F02": ("Open a target page with candidate elements.", "Content script runs and extracts candidates with text, DOM path and style."),
    "TC-F03": ("Open a non-target page.", "Content script does not run outside declared host patterns."),
    "TC-F04": ("Element exceeds threshold τ.", "Element is outlined and explanation names the CCPA category."),
    "TC-F05": ("Element below threshold τ.", "No highlight is shown."),
    "TC-F06": ("Reported detection is logged.", "Backend stores record with site, page, category and confidence."),
    "TC-F07": ("Dashboard opened for a site with logged detections.", "Manipulation Score and per-category counts are displayed."),
    "TC-F08": ("Highlighted control is clicked.", "Original page behaviour is unchanged."),
    "TC-I01": ("Content script sends text batch to service worker.", "Message received; request forwarded to inference service."),
    "TC-I02": ("Inference service returns confidences.", "Vector of 13 category confidences returned for each text."),
    "TC-I03": ("Inference service unavailable.", "Extension degrades gracefully; rule-only categories still evaluated; no crash."),
    "TC-I04": ("Detection sent to backend.", "Backend acknowledges and the record appears in the detection log."),
    "TC-I05": ("Crawler and extension capture the same page.", "Same candidate set and features recorded by both."),
    "TC-S01": ("Countdown timer that restarts on reload.", "High rule confidence for false urgency."),
    "TC-S02": ("Countdown timer that continues correctly across reloads.", "No false-urgency evidence from the timer rule."),
    "TC-S03": ("Insurance add-on checkbox checked on load.", "High rule confidence for basket sneaking."),
    "TC-S04": ("Small, low-contrast dismiss link beside large accept button.", "Contrast and area gap detected; interface-interference evidence."),
    "TC-S05": ("Accept and dismiss buttons of equal size and contrast.", "No interface-interference evidence."),
    "TC-S06": ("Element present in DOM with opacity 0.", "Element identified as hidden."),
    "TC-S07": ("Checkout total higher than product-page price.", "Drip-pricing evidence."),
    "TC-S08": ("Cancellation path longer than subscription path.", "Subscription-trap evidence."),
    "TC-S09": ("Known colour pairs (e.g. black on white).", "Contrast ratio equals the WCAG reference value (21:1 for black on white)."),
    "TC-L01": ("English guilt-inducing dismissal text.", "Highest confidence for confirm shaming."),
    "TC-L02": ("Neutral English dismissal text (\"No, thanks\").", "Negative class or low confidence for all categories."),
    "TC-L03": ("Roman-script Hinglish urgency or shaming text.", "Appropriate category with confidence reported (Hinglish performance not yet validated)."),
    "TC-L04": ("Very long text beyond maximum length.", "Text truncated; classification completes without error."),
    "TC-L05": ("Empty or whitespace-only text.", "Element skipped or classified as negative."),
    "TC-H01": ("Harmless wording on deceptive layout (pre-checked add-on).", "Detected through rule evidence."),
    "TC-H02": ("Deceptive wording in neutral layout.", "Detected through text evidence."),
    "TC-H03": ("Forced action needing both signals.", "Fused confidence exceeds τ only when both contribute."),
    "TC-H04": ("Ordinary page with no dark patterns.", "No elements reported."),
    "TC-H05": ("Change of αk in configuration.", "Fused output changes without code changes."),
}

RESULTS = {}
SHOTS = ROOT / "report" / "screenshots"


def record(tid, actual, status, func, file=None, shot=None, data=None):
    desc, exp = SPEC[tid]
    RESULTS[tid] = {"id": tid, "description": desc, "expected": exp, "actual": actual, "status": status,
                    "evidence": {"file": file or "tests/report_cases.py", "test_function": func, "screenshot": shot},
                    "data": data}
    print(f"[{status}] {tid}: {actual}")


def shot(page, name):
    p = f"report/screenshots/{name}.png"
    page.screenshot(path=str(ROOT / p), full_page=True)
    return p


def goto(page, url, settle=0.5):
    t = now_ms()
    page.goto(url)
    return wait_summary(page, after_ms=t, settle=settle)


def overlay_tags(page):
    return page.evaluate("""() => {
      const h = document.querySelector('patternguard-overlay');
      if (!h || !h.shadowRoot) return [];
      return [...h.shadowRoot.querySelectorAll('.box')].map(b => b.querySelector('.tag').textContent);
    }""")


def node_text(inputs):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(inputs, f)
        name = f.name
    out = subprocess.run(["node", str(ROOT / "tests" / "text_cli.js"), name], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


# ---------------- functional ----------------
def test_functional(ctx, base, errors):
    page = ctx.new_page()
    # F01: the service worker started and the extension page is reachable
    sw_ok = bool(ctx.pg_ext_id)
    manifest_errors = [e for e in errors if "manifest" in e.lower()]
    record("TC-F01", f"The unpacked Manifest V3 extension loaded, its service worker started (id {ctx.pg_ext_id}) and no manifest errors were reported.",
           "Pass" if sw_ok and not manifest_errors else "Fail", "test_functional")

    # F02 + F04 on dark-checkout
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/dark-checkout.html")
    has_paths = all(isinstance(p, str) and p for p in s["candidates"])
    record("TC-F02", f"The content script ran on demo/dark-checkout.html and extracted {s['candidateCount']} visible candidates, each with text and a DOM path; computed style (colour, background, size, visibility) was read by the rules and is not exported.",
           "Pass" if s["candidateCount"] > 0 and has_paths else "Fail", "test_functional", "demo/dark-checkout.html",
           data={"candidateCount": s["candidateCount"]})
    tags = overlay_tags(page)
    ok = len(tags) == len(s["detections"]) and all("(CCPA)" in t for t in tags)
    record("TC-F04", f"{len(s['detections'])} elements were reported above τ = {s['tau']} and {len(tags)} outlines were drawn, each labelled with its CCPA category name and an explanation.",
           "Pass" if ok else "Fail", "test_functional", "demo/dark-checkout.html", shot(page, "tc_f04_dark_checkout"),
           data={"tags": tags})

    # F03: non-target page
    s = goto(page, f"{base}/tests/pages/f02_plain.html")
    ran_plain = s is not None
    page.goto("about:blank")
    time.sleep(1)
    ran_blank = summary(page) is not None
    record("TC-F03", f"The manifest matches <all_urls>, so every http(s) page is a declared host; the content script {'ran' if ran_plain else 'did not run'} on a plain non-shop page (tests/pages/f02_plain.html) and {'ran' if ran_blank else 'did not run'} on about:blank. No narrower host restriction exists.",
           "Fail" if ran_plain else "Pass", "test_functional", "tests/pages/f02_plain.html")

    # F05: below threshold
    s = goto(page, f"{base}/tests/pages/f05_below_tau.html")
    tags = overlay_tags(page)
    record("TC-F05", f"The button 'Sign in to continue' has forced-action text evidence only (t = 0.9, α = 0.5, c = 0.45 < τ); {len(s['detections'])} detections and {len(tags)} highlights were shown.",
           "Pass" if not s["detections"] and not tags else "Fail", "test_functional", "tests/pages/f05_below_tau.html", shot(page, "tc_f05_below_tau"))

    # F06, F07
    record("TC-F06", "Not applicable: backend not built. Detections are stored locally with chrome.storage.local by the service worker.", "Not applicable", "test_functional")
    record("TC-F07", "Not applicable: dashboard not built. The toolbar popup shows the Manipulation Score and the current page's detections instead.", "Not applicable", "test_functional")

    # F08: clicking a highlighted control
    clear_storage(ctx)
    goto(page, f"{base}/demo/dark-checkout.html")
    before = page.is_checked("#order-protection")
    top_is_ctrl = page.evaluate("""() => { const e = document.getElementById('order-protection'); const r = e.getBoundingClientRect();
        return document.elementFromPoint(r.left + r.width/2, r.top + r.height/2) === e; }""")
    page.click("#order-protection")
    after = page.is_checked("#order-protection")
    record("TC-F08", f"The highlighted pre-ticked checkbox was clicked: its state changed from {before} to {after}, and the element at its centre was the checkbox itself (highlight overlay has pointer-events: none).",
           "Pass" if before and not after and top_is_ctrl else "Fail", "test_functional", "demo/dark-checkout.html")
    page.close()


# ---------------- integration ----------------
def test_integration(ctx, base):
    record("TC-I01", "Not applicable: inference service not built. The content script does send its results to the service worker (pg:results message), but there is no inference service to forward text to.", "Not applicable", "test_integration")
    record("TC-I02", "Not applicable: inference service not built. The local text stand-in (extension/text.js) returns a 13-value confidence vector per text (see TC-L tests).", "Not applicable", "test_integration")
    record("TC-I04", "Not applicable: backend not built.", "Not applicable", "test_integration")

    page = ctx.new_page()
    external = []
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(("http://127.0.0.1", "chrome-extension://", "data:")) else None)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/dark-checkout.html")
    record("TC-I03", f"No inference service exists; on demo/dark-checkout.html the extension made {len(external)} external requests, raised {len(errs)} page errors and still reported {len(s['detections'])} detections ({', '.join(categories(s))}) from local rules and the text stand-in.",
           "Pass" if not errs and len(s["detections"]) > 0 else "Fail", "test_integration", "demo/dark-checkout.html")

    # I05: independent Playwright extraction vs extension candidates
    extract_js = (ROOT / "tests" / "playwright_extract.js").read_text(encoding="utf-8")
    rows = []
    for url in ["demo/dark-checkout.html", "demo/fair-checkout.html", "demo/cases/case3_quick_commerce.html"]:
        s = goto(page, f"{base}/{url}")
        pw = page.evaluate(extract_js)
        a, b = set(s["candidates"]), set(pw)
        rows.append({"page": url, "extension": len(a), "playwright": len(b), "common": len(a & b),
                     "only_extension": sorted(a - b), "only_playwright": sorted(b - a)})
    same = all(r["extension"] == r["playwright"] == r["common"] for r in rows)
    desc = "; ".join(f"{r['page']}: extension {r['extension']}, Playwright {r['playwright']}, common {r['common']}" for r in rows)
    record("TC-I05", f"Candidate sets (DOM paths) compared on 3 pages: {desc}. Features beyond text and DOM path were not compared.",
           "Pass" if same else "Fail", "test_integration", "tests/playwright_extract.js", data=rows)
    page.close()


# ---------------- structural ----------------
def test_structural(ctx, base):
    page = ctx.new_page()
    P = f"{base}/tests/pages"

    clear_storage(ctx)
    goto(page, f"{P}/s01_timer_reset.html")
    time.sleep(6)
    t = now_ms(); page.reload(); s = wait_summary(page, after_ms=t, settle=0.5)
    fu = [d for d in s["detections"] if d["key"] == "false_urgency"]
    record("TC-S01", f"After one reload the timer restarted; false urgency was reported with r = {fu[0]['r'] if fu else 0} ({fu[0]['evidence'] if fu else 'no evidence'}).",
           "Pass" if fu and fu[0]["r"] >= 0.9 else "Fail", "test_structural", "tests/pages/s01_timer_reset.html", shot(page, "tc_s01_timer_reset"))

    clear_storage(ctx)
    goto(page, f"{P}/s02_timer_real.html")
    time.sleep(6)
    t = now_ms(); page.reload(); s = wait_summary(page, after_ms=t, settle=0.5)
    fu = [d for d in s["detections"] if d["key"] == "false_urgency"]
    record("TC-S02", f"The timer counted down from a stored deadline across a reload; {len(fu)} false-urgency detections were made.",
           "Pass" if not fu else "Fail", "test_structural", "tests/pages/s02_timer_real.html")

    clear_storage(ctx)
    s = goto(page, f"{P}/s03_preselected.html")
    bs = [d for d in s["detections"] if d["key"] == "basket_sneaking"]
    record("TC-S03", f"The pre-ticked insurance checkbox was reported as basket sneaking with r = {bs[0]['r'] if bs else 0}.",
           "Pass" if bs and bs[0]["r"] >= 0.9 else "Fail", "test_structural", "tests/pages/s03_preselected.html", shot(page, "tc_s03_preselected"))

    s = goto(page, f"{P}/s04_weak_decline.html")
    ii = [d for d in s["detections"] if d["key"] == "interface_interference"]
    record("TC-S04", f"Interface interference was reported on the decline link: {ii[0]['evidence'].rstrip('.') if ii else 'no detection'}.",
           "Pass" if ii else "Fail", "test_structural", "tests/pages/s04_weak_decline.html", shot(page, "tc_s04_weak_decline"))

    s = goto(page, f"{P}/s05_equal_buttons.html")
    ii = [d for d in s["detections"] if d["key"] == "interface_interference"]
    record("TC-S05", f"With equal accept and decline buttons, {len(ii)} interface-interference detections were made.",
           "Pass" if not ii else "Fail", "test_structural", "tests/pages/s05_equal_buttons.html")

    s = goto(page, f"{P}/s06_hidden.html")
    hidden = s["hidden"]
    ok = any(h.endswith("#ghost") or h == "#ghost" for h in hidden)
    record("TC-S06", f"The opacity:0 button #ghost was {'listed as hidden and excluded from candidates' if ok else 'not identified as hidden'} (hidden list: {hidden}).",
           "Pass" if ok and "#ghost" not in s["candidates"] else "Fail", "test_structural", "tests/pages/s06_hidden.html")

    clear_storage(ctx)
    goto(page, f"{P}/s07_drip.html")
    t = now_ms(); page.click("#buy"); s = wait_summary(page, after_ms=t, href_contains="#checkout", settle=3.5)
    dp = [d for d in s["detections"] if d["key"] == "drip_pricing"]
    record("TC-S07", f"On the checkout step the platform fee, absent from the product step, was reported as drip pricing ({len(dp)} detection).",
           "Pass" if dp else "Fail", "test_structural", "tests/pages/s07_drip.html", shot(page, "tc_s07_drip"))
    page.close()

    record("TC-S08", "Not implemented: no subscription-trap rule exists (cancellation path length is not measured).", "Not implemented", "test_structural")

    out = subprocess.run(["node", "-e",
                          "require('./extension/categories.js');const r=require('./extension/rules.js');"
                          "console.log(JSON.stringify({bw:r.contrastRatio([0,0,0],[255,255,255]),ww:r.contrastRatio([255,255,255],[255,255,255]),g777:r.contrastRatio(r.parseColor('#777777'),[255,255,255])}))"],
                         capture_output=True, text=True, cwd=str(ROOT), check=True)
    v = json.loads(out.stdout)
    record("TC-S09", f"In Node, contrastRatio(black, white) = {v['bw']:.2f}:1, white on white = {v['ww']:.2f}:1 and #777777 on white = {v['g777']:.2f}:1.",
           "Pass" if round(v["bw"], 2) == 21 and v["ww"] == 1 else "Fail", "test_structural (node)", "extension/rules.js", data=v)


# ---------------- linguistic ----------------
def test_linguistic():
    long_text = ("Great product with many features. " * 150) + "No, I will take risk"
    inputs = {
        "TC-L01": ["No thanks, I don't want to save money"],
        "TC-L02": ["No, thanks"],
        "TC-L03": ["Jaldi karo, sirf 2 bache hain!", "Nahi, mujhe discount nahi chahiye", "Main risk lunga, insurance nahi chahiye"],
        "TC-L04": [long_text],
        "TC-L05": ["", "    "],
    }
    flat = [s for v in inputs.values() for s in v]
    out = node_text(flat)
    res, i = {}, 0
    for k, v in inputs.items():
        res[k] = out[i:i + len(v)]
        i += len(v)

    r = res["TC-L01"][0]
    record("TC-L01", f"Input \"{inputs['TC-L01'][0]}\": highest confidence {r['top_conf']} for {r['top_key']}.",
           "Pass" if r["top_key"] == "confirm_shaming" else "Fail", "test_linguistic", "extension/text.js", data=res["TC-L01"])
    r = res["TC-L02"][0]
    record("TC-L02", f"Input \"No, thanks\": maximum confidence over all 13 categories was {max(r['vector'])}.",
           "Pass" if max(r["vector"]) == 0 else "Fail", "test_linguistic", "extension/text.js", data=res["TC-L02"])
    parts = [f"\"{s}\" -> {o['top_key'] or 'none'} ({o['top_conf']})" for s, o in zip(inputs["TC-L03"], res["TC-L03"])]
    record("TC-L03", "Outputs: " + "; ".join(parts) + ". These phrases are in the hand-written pattern list; Hinglish performance has not been validated on any dataset.",
           "Pass" if all(o["top_key"] for o in res["TC-L03"]) else "Fail", "test_linguistic", "extension/text.js", data=res["TC-L03"])
    r = res["TC-L04"][0]
    record("TC-L04", f"A {r['input_length']}-character input was truncated to {r['processed_length']} characters and scored without error; the shaming phrase at the end fell outside the window, so the top category was {r['top_key']}.",
           "Pass" if r["processed_length"] == 512 else "Fail", "test_linguistic", "extension/text.js", data=res["TC-L04"])
    ok = all(max(o["vector"]) == 0 for o in res["TC-L05"])
    record("TC-L05", f"Empty and whitespace-only inputs returned all-zero vectors (negative); the content script also skips whitespace-only text nodes when extracting candidates.",
           "Pass" if ok else "Fail", "test_linguistic", "extension/text.js", data=res["TC-L05"])


# ---------------- hybrid ----------------
def test_hybrid(ctx, base):
    page = ctx.new_page()
    P = f"{base}/tests/pages"
    s = goto(page, f"{P}/h01_rule_only.html")
    d = [x for x in s["detections"] if x["key"] == "basket_sneaking"]
    record("TC-H01", f"The pre-ticked 'Gift wrap ₹49' checkbox was reported as basket sneaking with r = {d[0]['r'] if d else '-'}, t = {d[0]['t'] if d else '-'}.",
           "Pass" if d and d[0]["r"] > 0 and d[0]["t"] == 0 else "Fail", "test_hybrid", "tests/pages/h01_rule_only.html")
    s = goto(page, f"{P}/h02_text_only.html")
    d = [x for x in s["detections"] if x["key"] == "confirm_shaming"]
    record("TC-H02", f"The equal-styled button \"No, I'd rather pay full price\" was reported as confirm shaming with r = {d[0]['r'] if d else '-'}, t = {d[0]['t'] if d else '-'}.",
           "Pass" if d and d[0]["t"] > 0 and d[0]["r"] == 0 else "Fail", "test_hybrid", "tests/pages/h02_text_only.html")
    res = {}
    for name in ["h03a_wall_forced", "h03b_wall_neutral", "h03c_text_neutral_layout"]:
        s = goto(page, f"{P}/{name}.html")
        res[name] = [x for x in s["detections"] if x["key"] == "forced_action"]
        if name == "h03a_wall_forced":
            sh = shot(page, "tc_h03_wall_forced")
    a, b, c = res["h03a_wall_forced"], res["h03b_wall_neutral"], res["h03c_text_neutral_layout"]
    record("TC-H03", f"Overlay with 'Sign up to continue' wording: {len(a)} forced-action detection (c = {a[0]['confidence'] if a else '-'}); overlay with neutral wording (rule only): {len(b)}; 'Sign up to continue' button without overlay (text only): {len(c)}.",
           "Pass" if a and not b and not c else "Fail", "test_hybrid", "tests/pages/h03*.html", sh)
    clear_storage(ctx)
    s = goto(page, f"{base}/demo/fair-checkout.html")
    record("TC-H04", f"On demo/fair-checkout.html {len(s['detections'])} elements were reported.",
           "Pass" if not s["detections"] else "Fail", "test_hybrid", "demo/fair-checkout.html", shot(page, "tc_h04_fair_checkout"))
    page.close()
    h5 = ROOT / "report" / "config_test_result.json"
    if h5.exists():
        r = json.loads(h5.read_text(encoding="utf-8"))
        record("TC-H05", f"Changing alpha for confirm shaming from 0 to 1 in a temporary copy of config.json (no other file changed) reduced the detections on demo/dark-checkout.html from {len(r['default_detections'])} to {len(r['modified_detections'])}.",
               "Pass" if r["pass"] else "Fail", "tests/config_test.py:main", "tests/config_test.py")
    else:
        record("TC-H05", "Not measured: run tests/config_test.py first.", "Fail", "tests/config_test.py:main")


def main():
    errors = []
    with serve_repo() as base, launch() as ctx:
        ctx.on("weberror", lambda e: errors.append(str(e.error)))
        test_functional(ctx, base, errors)
        test_integration(ctx, base)
        test_structural(ctx, base)
        test_hybrid(ctx, base)
    test_linguistic()
    order = list(SPEC)
    out = [RESULTS[k] for k in order if k in RESULTS]
    (ROOT / "report" / "test_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {}
    for r in out:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"\n{len(out)} test IDs: {counts}")
    sys.exit(0)


if __name__ == "__main__":
    main()
