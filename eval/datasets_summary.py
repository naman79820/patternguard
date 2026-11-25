"""Phase 2: describe the two public datasets from the files themselves."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data_public"


def main():
    y = pd.read_csv(D / "yada_dataset.tsv", sep="\t")
    m = pd.read_csv(D / "mathur_dark-patterns.csv")
    out = {
        "yada": {
            "file": "data_public/yada_dataset.tsv",
            "columns": list(y.columns),
            "rows": int(len(y)),
            "label_counts": {str(k): int(v) for k, v in y["label"].value_counts().sort_index().items()},
            "pattern_category_counts": {str(k): int(v) for k, v in y["Pattern Category"].value_counts().items()},
            "missing_text": int(y["text"].isna().sum()),
            "unique_page_ids": int(y["page_id"].nunique()),
        },
        "mathur": {
            "file": "data_public/mathur_dark-patterns.csv",
            "columns": list(m.columns),
            "rows": int(len(m)),
            "pattern_category_counts": {str(k): int(v) for k, v in m["Pattern Category"].value_counts().items()},
            "pattern_type_counts": {str(k): int(v) for k, v in m["Pattern Type"].value_counts().items()},
            "deceptive_counts": {str(k): int(v) for k, v in m["Deceptive?"].value_counts(dropna=False).items()},
            "missing_pattern_string": int(m["Pattern String"].isna().sum()),
        },
    }
    (ROOT / "report" / "datasets_summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
