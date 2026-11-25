"""Phase 5: element-level evaluation on the CONTROLLED TEST SET
(demo pages + reconstructed case pages, written by the team; not held-out sites).

Three configurations via config.json overrides on temporary copies of the extension:
  text_only  : all alpha_k = 0
  rules_only : all alpha_k = 1
  combined   : config.json as shipped
Latency: sinceLoadMs = time from the load event to the end of the first scan, including
drawing highlights (report eq. 6.4); scanMs = duration of each scan (used for SPA steps).
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from pg_harness import serve_repo, launch, clear_storage, wait_summary, now_ms, copy_extension  # noqa: E402
from run_cases import match  # noqa: E402

CONFIGS = {
    "text_only": lambda c: [x.__setitem__("alpha", 0) for x in c["categories"]],
    "rules_only": lambda c: [x.__setitem__("alpha", 1) for x in c["categories"]],
    "combined": lambda c: None,
}
KEYS = ["false_urgency", "basket_sneaking", "confirm_shaming", "forced_action", "subscription_trap",
        "interface_interference", "bait_and_switch", "drip_pricing", "disguised_advertisement", "nagging",
        "trick_question", "saas_billing", "rogue_malware"]


def page_list():
    demo = json.loads((ROOT / "tests" / "demo_expected.json").read_text(encoding="utf-8"))["pages"]
    cases = json.loads((ROOT / "tests" / "cases_expected.json").read_text(encoding="utf-8"))["cases"]
    return demo + [{"file": "demo/cases/" + c["file"], "steps": c["steps"]} for c in cases]


def run_config(name, ext, base):
    rows = []
    with launch(ext) as ctx:
        for p in page_list():
            clear_storage(ctx)
            page = ctx.new_page()
            t = now_ms()
            page.goto(f"{base}/{p['file']}")
            s = wait_summary(page, after_ms=t, settle=0.5)
            for step in p["steps"]:
                if step.get("reload_after_s"):
                    time.sleep(step["reload_after_s"])
                    t = now_ms()
                    page.reload()
                    s = wait_summary(page, after_ms=t, settle=0.5)
                if step.get("action"):
                    t = now_ms()
                    page.click(step["action"]["click"])
                    s = wait_summary(page, after_ms=t, href_contains=step["action"]["wait_for"], settle=3.5)
                tp, fp, fn = match(page, s["detections"], step["expected"])
                rows.append({"config": name, "page": p["file"], "step": step["name"],
                             "tp": [x["category"] for x in tp], "fp": [{"key": d["key"], "path": d["path"], "text": d["text"]} for d in fp],
                             "fn": [{"category": x["category"], "selector": x["selector"]} for x in fn],
                             "scanMs": s["scanMs"], "sinceLoadMs": s["sinceLoadMs"], "reason": s["reason"]})
            page.close()
    return rows


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": None if p is None else round(p, 4), "recall": None if r is None else round(r, 4),
            "f1": None if f is None else round(f, 4)}


def summarise(rows):
    tp = sum(len(r["tp"]) for r in rows); fp = sum(len(r["fp"]) for r in rows); fn = sum(len(r["fn"]) for r in rows)
    overall = prf(tp, fp, fn)
    per = {}
    for k in KEYS:
        a = sum(r["tp"].count(k) for r in rows)
        b = sum(1 for r in rows for d in r["fp"] if d["key"] == k)
        c = sum(1 for r in rows for d in r["fn"] if d["category"] == k)
        if a + b + c:
            per[k] = prf(a, b, c)
    load = [r["sinceLoadMs"] for r in rows if r["sinceLoadMs"] is not None]
    scans = [r["scanMs"] for r in rows]
    lat = {"since_load_ms": {"n": len(load), "median": round(statistics.median(load), 2), "max": round(max(load), 2)},
           "scan_ms": {"n": len(scans), "median": round(statistics.median(scans), 2), "max": round(max(scans), 2)}}
    return {"overall": overall, "per_category": per, "latency": lat}


def main():
    out = {"description": "Controlled test set: demo pages and reconstructed case pages written by the team, element-level ground truth from tests/demo_expected.json and tests/cases_expected.json. Not held-out sites.",
           "configs": {}, "rows": []}
    with serve_repo() as base:
        for name, patch in CONFIGS.items():
            ext = copy_extension(patch)
            rows = run_config(name, ext, base)
            out["rows"] += rows
            out["configs"][name] = summarise(rows)
            print(name, json.dumps(out["configs"][name]["overall"]), json.dumps(out["configs"][name]["latency"]))
    n_steps = len({(r["page"], r["step"]) for r in out["rows"]})
    n_pos = sum(len(s["expected"]) for p in page_list() for s in p["steps"])
    out["set_size"] = {"pages": len(page_list()), "page_states": n_steps, "labelled_dark_pattern_elements": n_pos}
    (ROOT / "eval" / "controlled_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(out["set_size"])


if __name__ == "__main__":
    main()
