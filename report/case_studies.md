# Reconstructed CCPA case studies

Pages: `demo/cases/`. Expected outcomes: `tests/cases_expected.json` (committed before the first run, commit a574624).
Runner: `python tests/run_cases.py --tag before|after`. Raw results: `report/case_results_before.json`, `report/case_results_after.json`.
Matching is element level: a detection counts only if its element is the expected element and its category is the expected category.

Sources: the pages reconstruct practices named in the team's brief, citing the linked news reports of CCPA penalties (Aug 2026). The articles themselves were not opened in this session (network use was restricted to package installs and the two dataset files), so the page details follow the brief, not a re-reading of the articles. Shop names are made up and styling is plain.

## Before rule changes

Totals over all steps: TP = 7, FP = 2, FN = 0.

| Case page | Step | Reported practice | Expected | Detected | Outcome | Screenshot |
|---|---|---|---|---|---|---|
| case1_ticket_donation.html | checkout | Basket sneaking (CCPA action against BookMyShow) | basket_sneaking | basket_sneaking | Caught as expected | report/screenshots/case1_ticket_donation_checkout_before.png |
| case2_airline_risk.html | flight | Confirm shaming (CCPA action against IndiGo) | none | confirm_shaming | 1 false positive(s) | report/screenshots/case2_airline_risk_flight_before.png |
| case2_airline_risk.html | addons | Confirm shaming (CCPA action against IndiGo) | confirm_shaming | confirm_shaming, confirm_shaming | 1 false positive(s) | report/screenshots/case2_airline_risk_addons_before.png |
| case3_quick_commerce.html | cart | Drip pricing and basket sneaking (CCPA action against Zepto) | none | none | Correctly silent | report/screenshots/case3_quick_commerce_cart_before.png |
| case3_quick_commerce.html | checkout | Drip pricing and basket sneaking (CCPA action against Zepto) | drip_pricing, drip_pricing, basket_sneaking | basket_sneaking, drip_pricing, drip_pricing | Caught as expected | report/screenshots/case3_quick_commerce_checkout_before.png |
| case4_edtech_donation.html | checkout | Basket sneaking (CCPA action against Physics Wallah); confirm shaming checked as a second label | basket_sneaking, confirm_shaming | basket_sneaking, confirm_shaming | Caught as expected | report/screenshots/case4_edtech_donation_checkout_before.png |
| case5_fair_control.html | cart | Control (expected 0) | none | none | Correctly silent | report/screenshots/case5_fair_control_cart_before.png |
| case5_fair_control.html | checkout | Control (expected 0) | none | none | Correctly silent | report/screenshots/case5_fair_control_checkout_before.png |

- False positive on case2_airline_risk.html (flight): `confirm_shaming` on element `html > body:nth-of-type(1) > p:nth-of-type(1)` with text "Reconstruction of a practice reported in Business Standard, Aug 2026 (CCPA action against an airline whose add-on opt-ou".
- False positive on case2_airline_risk.html (addons): `confirm_shaming` on element `html > body:nth-of-type(1) > p:nth-of-type(1)` with text "Reconstruction of a practice reported in Business Standard, Aug 2026 (CCPA action against an airline whose add-on opt-ou".

## After rule changes

Totals over all steps: TP = 7, FP = 0, FN = 0.

| Case page | Step | Reported practice | Expected | Detected | Outcome | Screenshot |
|---|---|---|---|---|---|---|
| case1_ticket_donation.html | checkout | Basket sneaking (CCPA action against BookMyShow) | basket_sneaking | basket_sneaking | Caught as expected | report/screenshots/case1_ticket_donation_checkout_after.png |
| case2_airline_risk.html | flight | Confirm shaming (CCPA action against IndiGo) | none | none | Correctly silent | report/screenshots/case2_airline_risk_flight_after.png |
| case2_airline_risk.html | addons | Confirm shaming (CCPA action against IndiGo) | confirm_shaming | confirm_shaming | Caught as expected | report/screenshots/case2_airline_risk_addons_after.png |
| case3_quick_commerce.html | cart | Drip pricing and basket sneaking (CCPA action against Zepto) | none | none | Correctly silent | report/screenshots/case3_quick_commerce_cart_after.png |
| case3_quick_commerce.html | checkout | Drip pricing and basket sneaking (CCPA action against Zepto) | drip_pricing, drip_pricing, basket_sneaking | basket_sneaking, drip_pricing, drip_pricing | Caught as expected | report/screenshots/case3_quick_commerce_checkout_after.png |
| case4_edtech_donation.html | checkout | Basket sneaking (CCPA action against Physics Wallah); confirm shaming checked as a second label | basket_sneaking, confirm_shaming | basket_sneaking, confirm_shaming | Caught as expected | report/screenshots/case4_edtech_donation_checkout_after.png |
| case5_fair_control.html | cart | Control (expected 0) | none | none | Correctly silent | report/screenshots/case5_fair_control_cart_after.png |
| case5_fair_control.html | checkout | Control (expected 0) | none | none | Correctly silent | report/screenshots/case5_fair_control_checkout_after.png |


## What changed between the two runs

One rule change, recorded in `report/changes.md`: text evidence for confirm shaming now counts only on controls the user can choose (buttons, links, labels, checkboxes). In the first run, the reconstruction banner on case 2 quoted the phrase "No I will take risk" inside an ordinary paragraph and was reported as confirm shaming on both steps. A quotation in prose is not a dismissal option, so this was a rule error, not a page error. No misses occurred in either run, so no rule was changed for recall.

Case 4 check requested in the brief: confirm shaming also fired, on the button "Remove donation and let a student miss free classes", in both runs.
