"""Phase 5: text check of the regex stand-in (extension/text.js) on the public datasets.

Runs the exact JavaScript scorer in Node (tests/text_cli.js) on every text.
- Yada et al.: binary labels; "any category fired" = predicted positive.
  Reported on the full file and on a fixed 80/20 split (seed 42) used again in Phase 7.
- Mathur et al.: all rows are dark patterns, so only recall (share flagged) is reported,
  for the types that map cleanly to a CCPA category (report/mapping_mathur_to_ccpa.md).
This measures only the wording stand-in, on English text from US/global shopping sites.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score
from sklearn.model_selection import train_test_split

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]

CLEAN_MAP = {
    "Countdown Timer": "false_urgency", "Limited-time Message": "false_urgency",
    "Low-stock Message": "false_urgency", "High-demand Message": "false_urgency",
    "Confirmshaming": "confirm_shaming", "Visual Interference": "interface_interference",
    "Trick Questions": "trick_question", "Hard to Cancel": "subscription_trap",
    "Sneak into Basket": "basket_sneaking", "Hidden Costs": "drip_pricing",
    "Forced Enrollment": "forced_action",
}


def score_texts(texts):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([str(t) for t in texts], f)
        name = f.name
    out = subprocess.run(["node", str(ROOT / "tests" / "text_cli.js"), name],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


def binary_metrics(y, p):
    tn, fp, fn, tp = confusion_matrix(y, p, labels=[0, 1]).ravel()
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, average="binary", zero_division=0)
    return {"n": int(len(y)), "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "accuracy": round(float(accuracy_score(y, p)), 4),
            "precision": round(float(pr), 4), "recall": round(float(rc), 4), "f1": round(float(f1), 4)}


def yada():
    df = pd.read_csv(ROOT / "data_public" / "yada_dataset.tsv", sep="\t")
    res = score_texts(df["text"].tolist())
    df["pred"] = [1 if r["top_key"] else 0 for r in res]
    df["pred_key"] = [r["top_key"] for r in res]
    full = binary_metrics(df["label"].values, df["pred"].values)
    _, test = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])
    split = binary_metrics(test["label"].values, test["pred"].values)
    per_cat = {}
    for cat, g in df.groupby("Pattern Category"):
        per_cat[cat] = {"n": int(len(g)), "flagged": int(g["pred"].sum()), "share_flagged": round(float(g["pred"].mean()), 4)}
    fired = df[df["pred"] == 1]["pred_key"].value_counts().to_dict()
    errors = {
        "false_positives": df[(df["pred"] == 1) & (df["label"] == 0)][["text", "pred_key"]].head(15).values.tolist(),
        "false_negatives_by_category": {c: g[(g["pred"] == 0)]["text"].head(5).tolist()
                                        for c, g in df[df["label"] == 1].groupby("Pattern Category")},
    }
    return {"full": full, "test_split_seed42": split, "per_yada_category": per_cat,
            "categories_fired": {str(k): int(v) for k, v in fired.items()}, "examples": errors,
            "test_index": test.index.tolist()}


def mathur():
    df = pd.read_csv(ROOT / "data_public" / "mathur_dark-patterns.csv")
    n_all = len(df)
    df = df[df["Pattern String"].notna()].copy()
    res = score_texts(df["Pattern String"].tolist())
    df["any"] = [1 if r["top_key"] else 0 for r in res]
    df["vec"] = [r["vector"] for r in res]
    keys = json.loads(subprocess.run(["node", "-e", "const P=require('./extension/categories.js');console.log(JSON.stringify(P.CATEGORIES.map(c=>c.key)))"],
                                     capture_output=True, text=True, cwd=str(ROOT), check=True).stdout)
    rows = []
    for t, ccpa in CLEAN_MAP.items():
        g = df[df["Pattern Type"] == t]
        if len(g) == 0:
            continue
        k = keys.index(ccpa)
        mapped = int(sum(1 for v in g["vec"] if v[k] > 0))
        rows.append({"mathur_type": t, "ccpa_category": ccpa, "n_with_text": int(len(g)),
                     "flagged_any_category": int(g["any"].sum()), "recall_any": round(float(g["any"].mean()), 4),
                     "flagged_mapped_category": mapped, "recall_mapped": round(mapped / len(g), 4)})
    by_ccpa = {}
    for r in rows:
        b = by_ccpa.setdefault(r["ccpa_category"], {"n": 0, "any": 0, "mapped": 0})
        b["n"] += r["n_with_text"]; b["any"] += r["flagged_any_category"]; b["mapped"] += r["flagged_mapped_category"]
    for b in by_ccpa.values():
        b["recall_any"] = round(b["any"] / b["n"], 4); b["recall_mapped"] = round(b["mapped"] / b["n"], 4)
    misses = {r["mathur_type"]: df[(df["Pattern Type"] == r["mathur_type"]) & (df["any"] == 0)]["Pattern String"].head(5).tolist() for r in rows}
    return {"rows_in_file": int(n_all), "rows_with_text": int(len(df)), "per_type": rows, "per_ccpa": by_ccpa, "examples_missed": misses}


def main():
    out = {"note": "Regex stand-in (extension/text.js) run in Node. English text from non-Indian sites; Yada labels are binary. Measures only the wording component.",
           "yada": yada(), "mathur": mathur()}
    (ROOT / "eval" / "text_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    y = out["yada"]
    print("Yada full:", y["full"])
    print("Yada test split (seed 42):", y["test_split_seed42"])
    print("Yada per category:", y["per_yada_category"])
    print("fired:", y["categories_fired"])
    for r in out["mathur"]["per_type"]:
        print("Mathur", r)


if __name__ == "__main__":
    main()
