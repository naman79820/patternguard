"""TC-H05: changing alpha_k in config.json changes the fused output without code changes.

Runs dark-checkout.html twice on temporary copies of the extension:
  A) config.json unchanged
  B) config.json with alpha for confirm_shaming changed from 0 to 1
Only config.json differs between A and B (checked by hashing every other file).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_harness import ROOT, serve_repo, launch, clear_storage, wait_summary, now_ms, copy_extension  # noqa: E402

CAT = "confirm_shaming"


def tree_hash(d, skip="config.json"):
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob("*")):
        if p.is_file() and p.name != skip:
            h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()


def run(ext, base):
    with launch(ext) as ctx:
        clear_storage(ctx)
        page = ctx.new_page()
        t = now_ms()
        page.goto(f"{base}/demo/dark-checkout.html")
        s = wait_summary(page, after_ms=t, settle=0.5)
        return [{"key": d["key"], "confidence": d["confidence"], "r": d["r"], "t": d["t"], "alpha": d["alpha"], "path": d["path"]}
                for d in s["detections"]]


def main():
    def patch(cfg):
        for c in cfg["categories"]:
            if c["key"] == CAT:
                c["alpha"] = 1
    ext_a = copy_extension(lambda cfg: None)
    ext_b = copy_extension(patch)
    same_code = tree_hash(ext_a) == tree_hash(ext_b)
    with serve_repo() as base:
        a = run(ext_a, base)
        b = run(ext_b, base)
    changed = a != b
    result = {
        "id": "TC-H05",
        "changed_parameter": f"categories[{CAT}].alpha: 0 -> 1 (temporary copy of config.json)",
        "only_config_differs": same_code,
        "default_detections": a,
        "modified_detections": b,
        "fused_output_changed": changed,
        "pass": bool(changed and same_code),
    }
    out = ROOT / "report" / "config_test_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"default: {[d['key'] for d in a]}")
    print(f"alpha({CAT})=1: {[d['key'] for d in b]}")
    print(f"only config.json differs: {same_code}; fused output changed: {changed}")
    print("[PASS] TC-H05" if result["pass"] else "[FAIL] TC-H05")
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
