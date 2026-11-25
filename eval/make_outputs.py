"""Phase 5: combine results into eval/results.json, eval/results_table.md and eval/figures/*.png.
Plain academic styling: white background, black text, greyscale, no titles inside figures."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "eval" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10, "axes.edgecolor": "black",
                     "axes.labelcolor": "black", "xtick.color": "black", "ytick.color": "black",
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 200})

text = json.loads((ROOT / "eval" / "text_results.json").read_text(encoding="utf-8"))
ctrl = json.loads((ROOT / "eval" / "controlled_results.json").read_text(encoding="utf-8"))
dataset_raw = ROOT / "dataset" / "raw"
live = "Live-site evaluation not done" if not (dataset_raw.exists() and any(dataset_raw.glob("*/*.html"))) else "see dataset/"

NAMES = {"text_only": "Text-only (all αk = 0)", "rules_only": "Rules-only (all αk = 1)", "combined": "Combined (config.json)"}

# ---- figure 1: controlled test set P/R/F1 ----
fig, ax = plt.subplots(figsize=(6, 3.2))
cfgs = ["text_only", "rules_only", "combined"]
x = np.arange(3)
w = 0.25
for i, (m, hatch, shade) in enumerate([("precision", "", "0.85"), ("recall", "///", "0.55"), ("f1", "...", "0.25")]):
    vals = [ctrl["configs"][c]["overall"][m] or 0 for c in cfgs]
    b = ax.bar(x + (i - 1) * w, vals, w, color=shade, edgecolor="black", hatch=hatch, label=m.capitalize() if m != "f1" else "F1")
    for xi, v in zip(x + (i - 1) * w, vals):
        ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(x, ["Text-only", "Rules-only", "Combined"])
ax.set_ylim(0, 1.15)
ax.set_ylabel("Score")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=8)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig_controlled_prf.png")
plt.close(fig)

# ---- figure 2: Yada share flagged per category ----
pc = text["yada"]["per_yada_category"]
order = sorted(pc, key=lambda k: -pc[k]["n"])
fig, ax = plt.subplots(figsize=(6, 3.2))
vals = [pc[k]["share_flagged"] for k in order]
ax.bar(range(len(order)), vals, color="0.6", edgecolor="black")
for i, k in enumerate(order):
    ax.text(i, vals[i] + 0.02, f"{vals[i]:.2f}\n(n={pc[k]['n']})", ha="center", va="bottom", fontsize=7)
ax.set_xticks(range(len(order)), order, rotation=30, ha="right")
ax.set_ylim(0, 1.0)
ax.set_ylabel("Share flagged by text scorer")
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig_yada_share_flagged.png")
plt.close(fig)

# ---- figure 3: Mathur recall per type ----
rows = text["mathur"]["per_type"]
fig, ax = plt.subplots(figsize=(6, 3.4))
vals = [r["recall_mapped"] for r in rows]
ax.barh(range(len(rows)), vals, color="0.6", edgecolor="black")
ax.set_yticks(range(len(rows)), [f"{r['mathur_type']} (n={r['n_with_text']})" for r in rows], fontsize=8)
for i, v in enumerate(vals):
    ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)
ax.invert_yaxis()
ax.set_xlim(0, 1.0)
ax.set_xlabel("Recall in the mapped CCPA category")
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig_mathur_recall.png")
plt.close(fig)

# ---- figure 4: scan latency per configuration ----
fig, ax = plt.subplots(figsize=(6, 3.0))
data = [[r["scanMs"] for r in ctrl["rows"] if r["config"] == c] for c in cfgs]
ax.boxplot(data, widths=0.5, medianprops={"color": "black"}, boxprops={"color": "black"},
           whiskerprops={"color": "black"}, capprops={"color": "black"}, flierprops={"markeredgecolor": "black"})
ax.set_xticks([1, 2, 3], ["Text-only", "Rules-only", "Combined"])
ax.set_ylabel("Scan time per page state (ms)")
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig_scan_latency.png")
plt.close(fig)

# ---- results.json ----
results = {
    "controlled_test_set": {"description": ctrl["description"], "size": ctrl["set_size"], "configs": ctrl["configs"]},
    "yada_text_check": {k: text["yada"][k] for k in ["full", "test_split_seed42", "per_yada_category", "categories_fired"]},
    "mathur_text_check": {k: text["mathur"][k] for k in ["rows_in_file", "rows_with_text", "per_type", "per_ccpa"]},
    "live_sites": live,
    "figures": sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in FIG.glob("*.png")),
}
(ROOT / "eval" / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- results_table.md ----
def f(v):
    return "Not measured" if v is None else f"{v:.2f}"


L = ["# PatternGuard evaluation results", "",
     "All numbers below were produced by scripts in eval/ in this session. Raw data: eval/results.json, eval/text_results.json, eval/controlled_results.json.", "",
     "## 1. Controlled test set (demo pages and reconstructed case pages)", "",
     f"{ctrl['set_size']['pages']} pages, {ctrl['set_size']['page_states']} page states, {ctrl['set_size']['labelled_dark_pattern_elements']} labelled dark-pattern elements. Element-level matching with category. These pages were written by the team; this is not a held-out-site evaluation.", "",
     "| Configuration | Precision | Recall | F1 | TP | FP | FN | Latency from load, median / max (ms) | Scan time, median / max (ms) |",
     "|---|---|---|---|---|---|---|---|---|"]
for c in cfgs:
    o = ctrl["configs"][c]["overall"]; la = ctrl["configs"][c]["latency"]
    L.append(f"| {NAMES[c]} | {f(o['precision'])} | {f(o['recall'])} | {f(o['f1'])} | {o['tp']} | {o['fp']} | {o['fn']} | "
             f"{la['since_load_ms']['median']:.1f} / {la['since_load_ms']['max']:.1f} | {la['scan_ms']['median']:.1f} / {la['scan_ms']['max']:.1f} |")
L += ["", "Per-category results (combined configuration):", "", "| Category | TP | FP | FN | Precision | Recall |", "|---|---|---|---|---|---|"]
for k, v in ctrl["configs"]["combined"]["per_category"].items():
    L.append(f"| {k} | {v['tp']} | {v['fp']} | {v['fn']} | {f(v['precision'])} | {f(v['recall'])} |")
y = text["yada"]
L += ["", "## 2. Text check on the Yada et al. dataset (binary, English, non-Indian sites)", "",
      "Positive prediction = any category fired in extension/text.js.", "",
      "| Split | n | TP | FP | FN | TN | Accuracy | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|---|---|---|"]
for name, m in [("Full file", y["full"]), ("Test split (20%, seed 42)", y["test_split_seed42"])]:
    L.append(f"| {name} | {m['n']} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} | {m['accuracy']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} |")
L += ["", "| Yada category | n | Flagged | Share flagged |", "|---|---|---|---|"]
for k in order:
    L.append(f"| {k} | {pc[k]['n']} | {pc[k]['flagged']} | {pc[k]['share_flagged']:.4f} |")
L += ["", "## 3. Text check on the Mathur et al. dataset (all rows are dark patterns; recall only)", "",
      f"{text['mathur']['rows_in_file']} rows in the file, {text['mathur']['rows_with_text']} with a non-empty pattern string. Only types with a clean CCPA mapping are listed.", "",
      "| Mathur type | CCPA category | n | Flagged in mapped category | Recall (mapped) | Recall (any category) |", "|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| {r['mathur_type']} | {r['ccpa_category']} | {r['n_with_text']} | {r['flagged_mapped_category']} | {r['recall_mapped']:.4f} | {r['recall_any']:.4f} |")
L += ["", "## 4. Live sites", "", live + ": no hand-saved pages exist in dataset/raw/.", "",
      "## Figures", ""] + [f"- {p}" for p in results["figures"]]
(ROOT / "eval" / "results_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
