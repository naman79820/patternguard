/* PatternGuard: the 13 dark patterns of the CCPA Guidelines for Prevention and
 * Regulation of Dark Patterns, 2023: identifiers, names and explanation texts.
 *
 * The numeric parameters (alpha_k, severity w_k, tau and rule thresholds) are NOT
 * set here: they are loaded from config.json at startup (requirement R4), so they
 * can be changed without code changes.
 *
 * Works both as a content script (sets globalThis.PG) and in Node (module.exports).
 */
(function (root) {
  const PG = (root.PG = root.PG || {});

  // Order and numbering follow Table A.1 of the report (labels 1..13).
  const CATEGORIES = [
    { id: 1, key: 'false_urgency', name: 'False urgency',
      explain: 'This countdown appears to restart when the page is reloaded, so the deadline may not be real.' },
    { id: 2, key: 'basket_sneaking', name: 'Basket sneaking',
      explain: 'This paid option was already selected before you touched it. Check whether you want it.' },
    // textScope 'control': text evidence counts only on an option the user can choose
    // (button, link, label, checkbox ...), because the pattern is the wording of a dismissal option.
    { id: 3, key: 'confirm_shaming', name: 'Confirm shaming', textScope: 'control',
      explain: 'The wording of this option may be designed to make you feel bad about declining.' },
    { id: 4, key: 'forced_action', name: 'Forced action',
      explain: 'This screen blocks the page and asks you to sign up or install an app before you can continue.' },
    { id: 5, key: 'subscription_trap', name: 'Subscription trap',
      explain: 'Cancelling this subscription may take more steps than signing up for it.' },
    { id: 6, key: 'interface_interference', name: 'Interface interference',
      explain: 'This option is much less visible than the alternative next to it.' },
    { id: 7, key: 'bait_and_switch', name: 'Bait and switch',
      explain: 'The offer shown may differ from what is actually provided.' },
    { id: 8, key: 'drip_pricing', name: 'Drip pricing',
      explain: 'This charge was not shown on an earlier step, so the total is higher than the price first shown.' },
    { id: 9, key: 'disguised_advertisement', name: 'Disguised advertisement',
      explain: 'This may be an advertisement presented as ordinary content.' },
    { id: 10, key: 'nagging', name: 'Nagging',
      explain: 'This prompt appears to repeat after it was dismissed.' },
    { id: 11, key: 'trick_question', name: 'Trick question',
      explain: 'This wording is confusing (for example a double negative) and may mislead you about your choice.' },
    { id: 12, key: 'saas_billing', name: 'SaaS billing',
      explain: 'This text suggests a recurring charge that may be applied without a clear reminder.' },
    { id: 13, key: 'rogue_malware', name: 'Rogue malware',
      explain: 'This message may be trying to get you to install or run harmful software.' }
  ];


  PG.CATEGORIES = CATEGORIES;
  PG.categoryByKey = (key) => CATEGORIES.find((c) => c.key === key);
  PG.categoryIndex = (key) => CATEGORIES.findIndex((c) => c.key === key);

  if (typeof module !== 'undefined' && module.exports) module.exports = PG;
})(typeof globalThis !== 'undefined' ? globalThis : this);
