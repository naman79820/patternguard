"""Build report/case_studies.md from report/case_results_before.json and _after.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
before = json.loads((ROOT / "report/case_results_before.json").read_text(encoding="utf-8"))
after = json.loads((ROOT / "report/case_results_after.json").read_text(encoding="utf-8"))

def outcome(r):
    if r["fn"] == 0 and r["fp"] == 0:
        return "Caught as expected" if r["expected"] else "Correctly silent"
    parts = []
    if r["fn"]: parts.append(f"missed {r['fn']}")
    if r["fp"]: parts.append(f"{r['fp']} false positive(s)")
    return ", ".join(parts)

lines = ["# Reconstructed CCPA case studies", "",
         "Pages: `demo/cases/`. Expected outcomes: `tests/cases_expected.json` (committed before the first run, commit a574624).",
         "Runner: `python tests/run_cases.py --tag before|after`. Raw results: `report/case_results_before.json`, `report/case_results_after.json`.",
         "Matching is element level: a detection counts only if its element is the expected element and its category is the expected category.",
         "",
         "Sources: the pages reconstruct practices named in the team's brief, citing the linked news reports of CCPA penalties (Aug 2026). The articles themselves were not opened in this session (network use was restricted to package installs and the two dataset files), so the page details follow the brief, not a re-reading of the articles. Shop names are made up and styling is plain.",
         ""]
for tag, res in [("Before rule changes", before), ("After rule changes", after)]:
    tp = sum(r["tp"] for r in res); fp = sum(r["fp"] for r in res); fn = sum(r["fn"] for r in res)
    lines += [f"## {tag}", "", f"Totals over all steps: TP = {tp}, FP = {fp}, FN = {fn}.", "",
              "| Case page | Step | Reported practice | Expected | Detected | Outcome | Screenshot |", "|---|---|---|---|---|---|---|"]
    for r in res:
        exp = ", ".join(e["category"] for e in r["expected"]) or "none"
        det = ", ".join(d["key"] for d in r["detected"]) or "none"
        lines.append(f"| {r['file']} | {r['step']} | {r['reported_practice']} | {exp} | {det} | {outcome(r)} | {r['screenshot']} |")
    lines.append("")
    for r in res:
        for d in r["false_positives"]:
            lines.append(f"- False positive on {r['file']} ({r['step']}): `{d['key']}` on element `{d['path']}` with text \"{d['text']}\".")
        for m in r["missed"]:
            lines.append(f"- Missed on {r['file']} ({r['step']}): `{m['category']}` on `{m['selector']}`.")
    lines.append("")
lines += ["## What changed between the two runs", "",
          "One rule change, recorded in `report/changes.md`: text evidence for confirm shaming now counts only on controls the user can choose (buttons, links, labels, checkboxes). In the first run, the reconstruction banner on case 2 quoted the phrase \"No I will take risk\" inside an ordinary paragraph and was reported as confirm shaming on both steps. A quotation in prose is not a dismissal option, so this was a rule error, not a page error. No misses occurred in either run, so no rule was changed for recall.",
          "",
          "Case 4 check requested in the brief: confirm shaming also fired, on the button \"Remove donation and let a student miss free classes\", in both runs.",
          ""]
(ROOT / "report/case_studies.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines[:40]))
