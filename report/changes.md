# Rule changes and their reasons

Each change to detection behaviour is recorded here with the reason. Detection was never changed only to make a test pass.

## Initial build (Phase 0)

The extension was written from scratch in this session because no PatternGuard source code existed on the machine (see report/issues.md).

1. **Drip pricing rule (extension/rules.js, `dripFee`).** The first version flagged a fee if it was missing from *any* earlier step that showed prices. On spa-booking.html this flagged "Taxes and fees", which had been shown on the review step but not repeated on the add-ons step. That is not drip pricing: the charge had been disclosed. The rule now flags a fee only if *no* earlier step of the same flow showed it. Found during the first smoke run, before the regression test was written.
