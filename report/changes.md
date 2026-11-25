# Rule changes and their reasons

Each change to detection behaviour is recorded here with the reason. Detection was never changed only to make a test pass.

## Initial build (Phase 0)

The extension was written from scratch in this session because no PatternGuard source code existed on the machine (see report/issues.md).

1. **Drip pricing rule (extension/rules.js, `dripFee`).** The first version flagged a fee if it was missing from *any* earlier step that showed prices. On spa-booking.html this flagged "Taxes and fees", which had been shown on the review step but not repeated on the add-ons step. That is not drip pricing: the charge had been disclosed. The rule now flags a fee only if *no* earlier step of the same flow showed it. Found during the first smoke run, before the regression test was written.

## Phase 3

2. **Confirm shaming limited to controls (extension/categories.js `textScope: 'control'`, extension/content.js fusion).** In the first run on the case pages, the banner paragraph of case2_airline_risk.html quoted the opt-out wording "No I will take risk" and was reported as confirm shaming on both steps (2 false positives, see report/case_results_before.json). Under the CCPA definition, confirm shaming is the wording of an option offered to the user, so text in ordinary prose should not count. Text evidence for confirm shaming is now used only for interactive controls (buttons, links, labels, checkboxes, role=button and similar). All other categories are unchanged. After the change, case results were TP 7, FP 0, FN 0 and the demo regression still passed.
