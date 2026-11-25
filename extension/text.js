/* PatternGuard text scorer.
 *
 * A transparent, regex-based stand-in for the DistilBERT classifier described in
 * the report (Section 3.7). It has the same output shape: a confidence vector over
 * the 13 CCPA categories (index 0 = category 1). It has NOT been trained; the
 * patterns were written by hand and are listed below so they can be audited.
 *
 * Works as a content script (globalThis.PG.text) and in Node (module.exports).
 */
(function (root) {
  const PG = (root.PG = root.PG || {});
  const MAX_CHARS = 512; // mirrors the classifier's maximum input length

  // [categoryKey, regex, confidence]. The highest matching confidence per category wins.
  const PATTERNS = [
    // False urgency (alpha = 1, so text alone never reports it; kept for the text-only ablation)
    ['false_urgency', /\bonly \d+ (left|remaining)\b/, 0.8],
    ['false_urgency', /\bhurry\b/, 0.7],
    ['false_urgency', /\b(offer|sale|deal|price) (ends|expires) (in|soon)\b/, 0.8],
    ['false_urgency', /\b\d+ (people|others|users) (are )?(viewing|looking at|watching)\b/, 0.7],
    ['false_urgency', /\b(selling|going) fast\b/, 0.7],
    ['false_urgency', /\blast chance\b/, 0.7],
    ['false_urgency', /\b(jaldi karo|jaldi|sirf \d+ (bache|baki)|abhi (kharido|khareedo|book karo))\b/, 0.7],

    // Confirm shaming
    ['confirm_shaming', /\bno,? i('| wi)ll take (the )?risks?\b/, 0.95],
    ['confirm_shaming', /\bi('ll| will) take my chances\b/, 0.9],
    ['confirm_shaming', /\bi don'?t (want|care|need) (to )?(save|saving|protect|protection|help|support|deals|discounts?|money|my (trip|family|order|device))\b/, 0.9],
    ['confirm_shaming', /\bi('d| would) rather (pay|miss|lose|not)\b/, 0.9],
    ['confirm_shaming', /\bno,? thanks,? i (don'?t|hate|prefer|like paying)\b/, 0.85],
    ['confirm_shaming', /\b(i'?m|i am) (fine|okay|ok) (with )?(being |staying )?(unprotected|paying more|missing out)\b/, 0.9],
    ['confirm_shaming', /\b(stay|remain) (unprotected|uninsured)\b/, 0.8],
    ['confirm_shaming', /\b(child|children|student|students|kid|kids)( will| would)? (miss|go without|lose|stay hungry)\b/, 0.85],
    ['confirm_shaming', /\b(mujhe|hume) (bachat|discount|offer) nahi chahiye\b/, 0.85],
    ['confirm_shaming', /\b(main|mai) risk (lunga|lungi|le lunga)\b/, 0.9],

    // Forced action (alpha = 0.5: needs the overlay rule as well)
    ['forced_action', /\b(sign ?up|log ?in|login|register|sign in|create an account) to (continue|proceed|view|see|access|unlock|shop|checkout|book)\b/, 0.9],
    ['forced_action', /\b(download|install|get) (our |the )?app to (continue|view|see|get|access|unlock|book)\b/, 0.9],
    ['forced_action', /\bcontinue (only )?(in|on) (the |our )?app\b/, 0.7],
    ['forced_action', /\byou must (sign|log|register|create|download|install)\b/, 0.8],

    // Bait and switch
    ['bait_and_switch', /\b(this|the) (deal|offer|item|price) is (no longer|not) available\b.*\b(similar|instead|alternative)\b/, 0.7],

    // Disguised advertisement (deliberately weak: text cannot tell disclosed from undisclosed ads)
    ['disguised_advertisement', /\b(sponsored|promoted) (content|result|listing)\b/, 0.4],

    // Trick question
    ['trick_question', /\buncheck (this|the) box (if|to) (you )?(do not|don'?t|not)\b/, 0.9],
    ['trick_question', /\b(do not|don'?t) (un)?(check|tick|select) .{0,40}\bif you (do not|don'?t)\b/, 0.85],
    ['trick_question', /\b(opt out of not|not to not)\b/, 0.9],

    // SaaS billing
    ['saas_billing', /\bfree trial\b.*\b(auto(matically)?[- ]?(renew|renews|charged|billed)|will be charged)\b/, 0.8],
    ['saas_billing', /\bauto[- ]?renews? (at|for) (₹|rs\.?|inr)/, 0.7],
    ['saas_billing', /\bwill be charged (automatically|monthly|annually|every month|every year) (after|unless)\b/, 0.8],

    // Rogue malware
    ['rogue_malware', /\byour (device|phone|computer|pc|mobile) (is|may be|has been) (infected|at risk)\b/, 0.9],
    ['rogue_malware', /\bvirus(es)? (detected|found)\b/, 0.9],
    ['rogue_malware', /\b(install|download) (now )?to (remove|clean|fix) (the )?(virus|malware)\b/, 0.9]
  ];

  function normalise(s) {
    if (s == null) return '';
    return String(s)
      .replace(/[‘’ʼ]/g, "'")
      .replace(/[“”]/g, '"')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase()
      .slice(0, MAX_CHARS);
  }

  // Returns { vector: number[13], matches: [{key, pattern, confidence}] }
  function score(text, categories) {
    const cats = categories || PG.CATEGORIES;
    const vector = new Array(cats.length).fill(0);
    const matches = [];
    const s = normalise(text);
    if (!s) return { vector, matches, text: s };
    for (const [key, re, conf] of PATTERNS) {
      if (re.test(s)) {
        const i = cats.findIndex((c) => c.key === key);
        if (i >= 0 && conf > vector[i]) vector[i] = conf;
        matches.push({ key, pattern: String(re), confidence: conf });
      }
    }
    return { vector, matches, text: s };
  }

  PG.text = { score, normalise, PATTERNS, MAX_CHARS };
  if (typeof module !== 'undefined' && module.exports) module.exports = PG.text;
})(typeof globalThis !== 'undefined' ? globalThis : this);
