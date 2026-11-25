"""Phase 7 (stretch): binary DistilBERT baseline on the Yada et al. dataset, CPU only.

Same stratified 80/20 split (seed 42) as eval/text_eval.py. Compares with the regex
stand-in on the same test split. The model is saved to models/distilbert_dp/
(gitignored) and is NOT used by the extension. Binary labels, English, non-Indian sites.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SEED = 42
HP = {"model": "distilbert-base-uncased", "max_length": 64, "epochs": 3, "batch_size": 16, "learning_rate": 5e-5}


def metrics(y, p):
    pr, rc, f1, _ = precision_recall_fscore_support(y, p, average="binary", zero_division=0)
    return {"accuracy": round(float(accuracy_score(y, p)), 4), "precision": round(float(pr), 4),
            "recall": round(float(rc), 4), "f1": round(float(f1), 4)}


def regex_preds(texts):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump([str(t) for t in texts], f)
    out = subprocess.run(["node", str(ROOT / "tests" / "text_cli.js"), f.name], capture_output=True, text=True, encoding="utf-8", check=True)
    return [1 if r["top_key"] else 0 for r in json.loads(out.stdout)]


def main():
    torch.manual_seed(SEED); np.random.seed(SEED)
    torch.set_num_threads(max(1, torch.get_num_threads()))
    df = pd.read_csv(ROOT / "data_public" / "yada_dataset.tsv", sep="\t")
    train, test = train_test_split(df, test_size=0.2, random_state=SEED, stratify=df["label"])
    tok = AutoTokenizer.from_pretrained(HP["model"])
    model = AutoModelForSequenceClassification.from_pretrained(HP["model"], num_labels=2)
    enc = lambda s: tok(list(map(str, s)), truncation=True, padding="max_length", max_length=HP["max_length"], return_tensors="pt")
    Xtr, ytr = enc(train["text"]), torch.tensor(train["label"].values)
    Xte = enc(test["text"])
    opt = torch.optim.AdamW(model.parameters(), lr=HP["learning_rate"])
    n = len(ytr)
    steps = HP["epochs"] * ((n + HP["batch_size"] - 1) // HP["batch_size"])
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: max(0.0, 1 - s / steps))
    t0 = time.time()
    model.train()
    g = torch.Generator().manual_seed(SEED)
    for ep in range(HP["epochs"]):
        perm = torch.randperm(n, generator=g)
        total = 0.0
        for i in range(0, n, HP["batch_size"]):
            idx = perm[i:i + HP["batch_size"]]
            out = model(input_ids=Xtr["input_ids"][idx], attention_mask=Xtr["attention_mask"][idx], labels=ytr[idx])
            out.loss.backward(); opt.step(); sched.step(); opt.zero_grad()
            total += out.loss.item() * len(idx)
        print(f"epoch {ep + 1}: mean loss {total / n:.4f}, elapsed {time.time() - t0:.0f}s", flush=True)
    train_s = time.time() - t0
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(test), 64):
            logits = model(input_ids=Xte["input_ids"][i:i + 64], attention_mask=Xte["attention_mask"][i:i + 64]).logits
            preds += logits.argmax(-1).tolist()
    y = test["label"].values
    res = {
        "note": "Binary classifier (dark pattern vs not) trained on English text from non-Indian shopping sites. Not used by the extension.",
        "seed": SEED, "hyperparameters": HP, "train_n": int(len(train)), "test_n": int(len(test)),
        "train_seconds": round(train_s, 1), "device": "cpu", "torch_threads": torch.get_num_threads(),
        "distilbert": metrics(y, preds), "regex_same_split": metrics(y, regex_preds(test["text"])),
    }
    out_dir = ROOT / "models" / "distilbert_dp"
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir); tok.save_pretrained(out_dir)
    (ROOT / "eval" / "distilbert_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
