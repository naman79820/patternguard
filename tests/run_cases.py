"""Run the extension on the reconstructed case pages and compare with
tests/cases_expected.json at element level. Saves screenshots and a JSON result.

Usage: python tests/run_cases.py --tag before|after
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_harness import ROOT, EXT, serve_repo, launch, clear_storage, wait_summary, now_ms  # noqa: E402

MATCH_JS = """([detPath, sel]) => {
  const a = document.querySelector(detPath), b = document.querySelector(sel);
  return !!a && a === b;
}"""


def match(page, detections, expected):
    """Element-level comparison. Returns tp, fp, fn lists."""
    used = set()
    tp, fn = [], []
    for e in expected:
        hit = None
        for i, d in enumerate(detections):
            if i in used or d["key"] != e["category"]:
                continue
            if page.evaluate(MATCH_JS, [d["path"], e["selector"]]):
                hit = i
                break
        if hit is None:
            fn.append(e)
        else:
            used.add(hit)
            tp.append({**e, "confidence": detections[hit]["confidence"], "evidence": detections[hit]["evidence"]})
    fp = [d for i, d in enumerate(detections) if i not in used]
    return tp, fp, fn


def run(ext=EXT, tag="run", shots=True):
    expected = json.loads((ROOT / "tests" / "cases_expected.json").read_text(encoding="utf-8"))
    out = []
    shot_dir = ROOT / "report" / "screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    with serve_repo() as base, launch(ext) as ctx:
        for case in expected["cases"]:
            clear_storage(ctx)
            page = ctx.new_page()
            t = now_ms()
            page.goto(f"{base}/demo/cases/{case['file']}")
            s = wait_summary(page, after_ms=t, settle=0.5)
            for step in case["steps"]:
                if step.get("action"):
                    t = now_ms()
                    page.click(step["action"]["click"])
                    s = wait_summary(page, after_ms=t, href_contains=step["action"]["wait_for"], settle=3.5)
                tp, fp, fn = match(page, s["detections"], step["expected"])
                shot = None
                if shots:
                    shot = f"report/screenshots/{Path(case['file']).stem}_{step['name']}_{tag}.png"
                    page.screenshot(path=str(ROOT / shot), full_page=True)
                rec = {
                    "file": case["file"], "step": step["name"], "source": case["source"],
                    "reported_practice": case["reported_practice"],
                    "expected": step["expected"],
                    "detected": [{"key": d["key"], "path": d["path"], "confidence": d["confidence"], "text": d["text"], "evidence": d["evidence"]} for d in s["detections"]],
                    "tp": len(tp), "fp": len(fp), "fn": len(fn),
                    "missed": fn, "false_positives": [{"key": d["key"], "path": d["path"], "text": d["text"]} for d in fp],
                    "scan_ms": s["scanMs"], "screenshot": shot,
                }
                out.append(rec)
                status = "OK" if not fp and not fn else "DIFF"
                print(f"[{status}] {case['file']} {step['name']}: expected {[e['category'] for e in step['expected']]}, "
                      f"detected {[d['key'] for d in s['detections']]} (tp={len(tp)} fp={len(fp)} fn={len(fn)})")
            page.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()
    res = run(tag=args.tag)
    path = ROOT / "report" / f"case_results_{args.tag}.json"
    path.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
