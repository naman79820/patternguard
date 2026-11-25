# Mapping of Mathur et al. (2019) categories and types to the 13 CCPA dark patterns

Source of the left-hand columns: `data_public/mathur_dark-patterns.csv` (columns "Pattern Category" and "Pattern Type"; counts read from the file by `eval/datasets_summary.py`, see `report/datasets_summary.json`). Mathur et al. build on the strategy-level vocabulary of Gray et al. (nagging, obstruction, sneaking, interface interference, forced action).

The right-hand column uses the 13 categories of the CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023. "No clean mapping" means that no CCPA category covers the type without stretching its definition. The mapping was made by reading the definitions; it was not validated by independent annotators.

| Mathur category | Mathur type | Rows in file | CCPA category | Note |
|---|---|---|---|---|
| Urgency | Countdown Timer | 393 | False urgency | Clean mapping. |
| Urgency | Limited-time Message | 88 | False urgency | Clean mapping. |
| Scarcity | Low-stock Message | 632 | False urgency | CCPA false urgency covers false scarcity of stock. |
| Scarcity | High-demand Message | 47 | False urgency | CCPA false urgency covers claims of high demand. |
| Social Proof | Activity Notification | 313 | No clean mapping | Closest is false urgency ("others are buying"), but the CCPA list has no social-proof category. |
| Social Proof | Testimonials of Uncertain Origin | 12 | No clean mapping | Closest is disguised advertisement; not equivalent. |
| Misdirection | Confirmshaming | 169 | Confirm shaming | Clean mapping. |
| Misdirection | Visual Interference | 25 | Interface interference | Clean mapping. |
| Misdirection | Trick Questions | 9 | Trick question | Clean mapping. |
| Misdirection | Pressured Selling | 67 | No clean mapping | Partly interface interference (pre-selected upgrade) and partly basket sneaking; depends on the instance. |
| Obstruction | Hard to Cancel | 31 | Subscription trap | Clean mapping. |
| Sneaking | Sneak into Basket | 7 | Basket sneaking | Clean mapping. |
| Sneaking | Hidden Costs | 5 | Drip pricing | Clean mapping. |
| Sneaking | Hidden Subscription | 14 | Subscription trap (or SaaS billing) | Mostly subscription trap; SaaS billing where the hidden charge is a recurring software fee. |
| Forced Action | Forced Enrollment | 6 | Forced action | Clean mapping. |

## CCPA categories with no Mathur counterpart

Bait and switch, disguised advertisement (except the weak link above), nagging, SaaS billing (except the weak link above) and rogue malware have no direct counterpart in the Mathur data.

## Categories used for the recall-only text check (Phase 5)

Only types with a clean mapping are used: Countdown Timer, Limited-time Message, Low-stock Message, High-demand Message (false urgency); Confirmshaming (confirm shaming); Visual Interference (interface interference); Trick Questions (trick question); Hard to Cancel (subscription trap); Sneak into Basket (basket sneaking); Hidden Costs (drip pricing); Forced Enrollment (forced action).
