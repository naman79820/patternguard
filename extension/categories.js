/* PatternGuard: the 13 dark patterns of the CCPA Guidelines for Prevention and
 * Regulation of Dark Patterns, 2023, with fusion weights and severity weights.
 *
 * alpha  = weight of structural (rule) evidence in the fused confidence
 *          c = alpha * r + (1 - alpha) * t   (report eq. 3.5)
 * severity = w_k used in the Manipulation Score S (report eq. 3.7)
 *
 * Works both as a content script (sets globalThis.PG) and in Node (module.exports).
 */
(function (root) {
  const PG = (root.PG = root.PG || {});

  // Order and numbering follow Table A.1 of the report (labels 1..13).
  const CATEGORIES = [
    { id: 1, key: 'false_urgency', name: 'False urgency', alpha: 1, severity: 1,
      explain: 'This countdown appears to restart when the page is reloaded, so the deadline may not be real.' },
    { id: 2, key: 'basket_sneaking', name: 'Basket sneaking', alpha: 1, severity: 1,
      explain: 'This paid option was already selected before you touched it. Check whether you want it.' },
    { id: 3, key: 'confirm_shaming', name: 'Confirm shaming', alpha: 0, severity: 1,
      explain: 'The wording of this option may be designed to make you feel bad about declining.' },
    { id: 4, key: 'forced_action', name: 'Forced action', alpha: 0.5, severity: 1,
      explain: 'This screen blocks the page and asks you to sign up or install an app before you can continue.' },
    { id: 5, key: 'subscription_trap', name: 'Subscription trap', alpha: 1, severity: 1,
      explain: 'Cancelling this subscription may take more steps than signing up for it.' },
    { id: 6, key: 'interface_interference', name: 'Interface interference', alpha: 1, severity: 1,
      explain: 'This option is much less visible than the alternative next to it.' },
    { id: 7, key: 'bait_and_switch', name: 'Bait and switch', alpha: 0, severity: 1,
      explain: 'The offer shown may differ from what is actually provided.' },
    { id: 8, key: 'drip_pricing', name: 'Drip pricing', alpha: 1, severity: 1,
      explain: 'This charge was not shown on an earlier step, so the total is higher than the price first shown.' },
    { id: 9, key: 'disguised_advertisement', name: 'Disguised advertisement', alpha: 0, severity: 1,
      explain: 'This may be an advertisement presented as ordinary content.' },
    { id: 10, key: 'nagging', name: 'Nagging', alpha: 1, severity: 1,
      explain: 'This prompt appears to repeat after it was dismissed.' },
    { id: 11, key: 'trick_question', name: 'Trick question', alpha: 0, severity: 1,
      explain: 'This wording is confusing (for example a double negative) and may mislead you about your choice.' },
    { id: 12, key: 'saas_billing', name: 'SaaS billing', alpha: 0, severity: 1,
      explain: 'This text suggests a recurring charge that may be applied without a clear reminder.' },
    { id: 13, key: 'rogue_malware', name: 'Rogue malware', alpha: 0, severity: 1,
      explain: 'This message may be trying to get you to install or run harmful software.' }
  ];

  const DEFAULTS = {
    tau: 0.6,
    rules: {
      contrastLimit: 3.0,      // WCAG ratio below which a decline control counts as low contrast
      sizeRatio: 4.0,          // accept area / decline area at or above which the decline is "small"
      overlayCoverage: 0.6,    // share of the viewport an overlay must cover to count as a wall
      timerSlackSeconds: 5,    // tolerance when comparing a timer across reloads
      memoryMinutes: 30        // how long timer and fee memory is kept
    },
    rescanMinIntervalMs: 3000
  };

  PG.CATEGORIES = CATEGORIES;
  PG.DEFAULTS = DEFAULTS;
  PG.categoryByKey = (key) => CATEGORIES.find((c) => c.key === key);
  PG.categoryIndex = (key) => CATEGORIES.findIndex((c) => c.key === key);

  if (typeof module !== 'undefined' && module.exports) module.exports = PG;
})(typeof globalThis !== 'undefined' ? globalThis : this);
