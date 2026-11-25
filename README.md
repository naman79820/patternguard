# PatternGuard

PatternGuard is a Chrome extension (Manifest V3, plain JavaScript, no build step) that detects dark patterns on shopping and travel pages, explains each finding in plain language and maps it to the 13 dark patterns of India's CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023.

Minor Project (ES-451), B.Tech CSE, JIMS Engineering Management Technical Campus (GGSIPU).

## How it works

For every candidate element on a page the extension computes two confidence vectors over the 13 CCPA categories:

- **Rules** (`extension/rules.js`): countdown that restarts across reloads; paid option pre-selected before the user touched it (HTML, script or `role=checkbox/radio/switch`); low-contrast or small decline next to a strong accept (WCAG contrast); fee not shown on an earlier step of the same flow (drip pricing); screen-covering sign-up or app wall (forced action); hidden-element check.
- **Text** (`extension/text.js`): a hand-written regex scorer, a stand-in for the DistilBERT classifier described in the report. Same output shape; not trained.

They are fused as `c = alpha * r + (1 - alpha) * t` per category, and an element is reported when `c >= tau` (`extension/content.js`). Detections are highlighted on the page. The service worker stores them with `chrome.storage` and computes the site's Manipulation Score S, which the toolbar popup shows. All weights and thresholds are in `extension/config.json`.

There is no backend, inference service, dashboard or crawler. Nothing leaves the browser.

## Install and load the extension

1. Open `chrome://extensions` in Chrome or another Chromium browser.
2. Turn on **Developer mode**.
3. Click **Load unpacked** and choose the `extension/` folder (or unzip `dist/PatternGuard_extension.zip` and choose that folder).

## Run the demo and case pages

Serve the repository root (the extension needs http pages):

```powershell
python -m http.server 8000
```

Then open, with the extension loaded:

- http://localhost:8000/demo/dark-checkout.html (4 detections; 5 after one reload, once the timer has run a few seconds)
- http://localhost:8000/demo/fair-checkout.html (0)
- http://localhost:8000/demo/spa-booking.html (0 on review, 3 on #addons, 1 on #payment)
- http://localhost:8000/demo/cases/ (five reconstructions of practices from CCPA actions; made-up shop names)

## Set up the test environment (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv            # any Python 3.10 to 3.12
.venv\Scripts\python -m pip install playwright pandas scikit-learn matplotlib numpy python-docx
.venv\Scripts\python -m playwright install chromium
# Phase 7 only:
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install transformers datasets
```

Node.js is needed for the unit tests and the text checks.

## Run the tests

```powershell
powershell -ExecutionPolicy Bypass -File tests\run_all.ps1
```

This runs `tests/unit.test.js` (Node), `tests/regression.py` (demo and case pages in Chromium with the extension), `tests/config_test.py` (TC-H05) and `tests/report_cases.py` (every test ID in report Tables 6.1 to 6.5, written to `report/test_results.json`).

## Run the evaluation

```powershell
.venv\Scripts\python eval\datasets_summary.py      # describe the public datasets
.venv\Scripts\python eval\text_eval.py             # text scorer on Yada et al. and Mathur et al.
.venv\Scripts\python eval\controlled_eval.py       # controlled test set, three configurations
.venv\Scripts\python eval\make_outputs.py          # eval/results.json, results_table.md, figures
.venv\Scripts\python eval\distilbert_baseline.py   # optional: binary DistilBERT baseline (CPU)
.venv\Scripts\python tests\run_cases.py --tag after
.venv\Scripts\python tools\screenshots.py
.venv\Scripts\python tools\update_report.py        # rebuild the report copy from docs/
```

## Folder map

| Path | Contents |
|---|---|
| `extension/` | The Chrome extension: manifest, config.json, categories, rules, text scorer, content script, service worker, popup |
| `demo/` | Demo pages; `demo/cases/` holds the reconstructed CCPA case pages |
| `tests/` | Regression, unit, config and report test cases; controlled pages in `tests/pages/`; expected outcomes |
| `eval/` | Evaluation scripts, results (`results.json`, `results_table.md`) and figures |
| `data_public/` | Yada et al. (Apache-2.0) and Mathur et al. dataset files, as downloaded |
| `docs/` | Original report (not modified) |
| `report/` | Updated report copy, edit log, test results, case studies, error analysis, screenshots, TODO for the team |
| `tools/` | Helper scripts (environment record, report update, screenshots) |
| `models/` | DistilBERT baseline weights (not in git) |

## Data sources

- Y. Yada et al., "Dark patterns in e-commerce: a dataset and its baseline evaluations," IEEE BigData 2022. Dataset: https://github.com/yamanalab/ec-darkpattern (Apache-2.0).
- A. Mathur et al., "Dark Patterns at Scale: Findings from a Crawl of 11K Shopping Websites," CSCW 2019. Data: https://github.com/aruneshmathur/dark-patterns.

## Limitations

The results on the controlled test set come from pages written alongside the rules. No live or held-out websites were evaluated. Hinglish is not validated. The content script runs on all URLs. Subscription trap and nagging have no rules. See `report/TODO_for_team.md` and Chapter 7 of the report.
