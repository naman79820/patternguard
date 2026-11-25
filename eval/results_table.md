# PatternGuard evaluation results

All numbers below were produced by scripts in eval/ in this session. Raw data: eval/results.json, eval/text_results.json, eval/controlled_results.json.

## 1. Controlled test set (demo pages and reconstructed case pages)

8 pages, 15 page states, 20 labelled dark-pattern elements. Element-level matching with category. These pages were written by the team; this is not a held-out-site evaluation.

| Configuration | Precision | Recall | F1 | TP | FP | FN | Latency from load, median / max (ms) | Scan time, median / max (ms) |
|---|---|---|---|---|---|---|---|---|
| Text-only (all αk = 0) | 0.54 | 0.35 | 0.42 | 7 | 6 | 13 | 21.8 / 65.4 | 14.3 / 22.3 |
| Rules-only (all αk = 1) | 1.00 | 0.65 | 0.79 | 13 | 0 | 7 | 18.8 / 58.2 | 12.6 / 24.9 |
| Combined (config.json) | 1.00 | 1.00 | 1.00 | 20 | 0 | 0 | 21.5 / 86.3 | 13.1 / 36.4 |

Per-category results (combined configuration):

| Category | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| false_urgency | 1 | 0 | 0 | 1.00 | 1.00 |
| basket_sneaking | 7 | 0 | 0 | 1.00 | 1.00 |
| confirm_shaming | 5 | 0 | 0 | 1.00 | 1.00 |
| interface_interference | 2 | 0 | 0 | 1.00 | 1.00 |
| drip_pricing | 3 | 0 | 0 | 1.00 | 1.00 |
| trick_question | 2 | 0 | 0 | 1.00 | 1.00 |

## 2. Text check on the Yada et al. dataset (binary, English, non-Indian sites)

Positive prediction = any category fired in extension/text.js.

| Split | n | TP | FP | FN | TN | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|---|
| Full file | 2356 | 394 | 0 | 784 | 1178 | 0.6672 | 1.0000 | 0.3345 | 0.5013 |
| Test split (20%, seed 42) | 472 | 78 | 0 | 158 | 236 | 0.6653 | 1.0000 | 0.3305 | 0.4968 |

| Yada category | n | Flagged | Share flagged |
|---|---|---|---|
| Not Dark Pattern | 1178 | 0 | 0.0000 |
| Scarcity | 418 | 250 | 0.5981 |
| Social Proof | 312 | 23 | 0.0737 |
| Urgency | 210 | 48 | 0.2286 |
| Misdirection | 195 | 73 | 0.3744 |
| Obstruction | 27 | 0 | 0.0000 |
| Sneaking | 12 | 0 | 0.0000 |
| Forced Action | 4 | 0 | 0.0000 |

## 3. Text check on the Mathur et al. dataset (all rows are dark patterns; recall only)

1818 rows in the file, 1512 with a non-empty pattern string. Only types with a clean CCPA mapping are listed.

| Mathur type | CCPA category | n | Flagged in mapped category | Recall (mapped) | Recall (any category) |
|---|---|---|---|---|---|
| Countdown Timer | false_urgency | 149 | 40 | 0.2685 | 0.2685 |
| Limited-time Message | false_urgency | 88 | 9 | 0.1023 | 0.1023 |
| Low-stock Message | false_urgency | 631 | 449 | 0.7116 | 0.7116 |
| High-demand Message | false_urgency | 47 | 6 | 0.1277 | 0.1277 |
| Confirmshaming | confirm_shaming | 169 | 81 | 0.4793 | 0.4793 |
| Visual Interference | interface_interference | 14 | 0 | 0.0000 | 0.0714 |
| Trick Questions | trick_question | 9 | 0 | 0.0000 | 0.0000 |
| Hard to Cancel | subscription_trap | 30 | 0 | 0.0000 | 0.0000 |
| Sneak into Basket | basket_sneaking | 3 | 0 | 0.0000 | 0.0000 |
| Hidden Costs | drip_pricing | 3 | 0 | 0.0000 | 0.0000 |
| Forced Enrollment | forced_action | 4 | 0 | 0.0000 | 0.0000 |

## 4. Live sites

Live-site evaluation not done: no hand-saved pages exist in dataset/raw/.

## Figures

- eval/figures/fig_controlled_prf.png
- eval/figures/fig_mathur_recall.png
- eval/figures/fig_scan_latency.png
- eval/figures/fig_yada_share_flagged.png
