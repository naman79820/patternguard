/* PatternGuard rule engine: structural evidence from the DOM and computed CSS.
 *
 * Rules implemented (each returns findings {el, key, score, evidence}):
 *   1. timerReset      - countdown that restarts across reloads        -> false_urgency
 *   2. preselected     - paid option ticked before the user touched it -> basket_sneaking
 *   3. declineContrast - weak decline control next to a strong accept  -> interface_interference
 *   4. dripFee         - fee line not shown on an earlier step         -> drip_pricing
 *   5. overlayWall     - screen-covering sign-up / app wall            -> forced_action
 * Categories without a rule get r = 0 (subscription trap and nagging are not implemented).
 *
 * The pure helpers (colour parsing, luminance, contrast) also load in Node for unit tests.
 */
(function (root) {
  const PG = (root.PG = root.PG || {});

  // ---------- colour and contrast (WCAG 2.1, report eqs. 3.1 to 3.3) ----------
  function parseColor(str) {
    if (!str) return null;
    const m = String(str).match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?\s*\)/i);
    if (m) {
      let a = m[4] === undefined ? 1 : m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]);
      return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), a];
    }
    const h = String(str).trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (h) {
      let x = h[1];
      if (x.length === 3) x = x.split('').map((c) => c + c).join('');
      return [parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16), 1];
    }
    return null;
  }

  function luminance(rgb) {
    const lin = (c) => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
  }

  function contrastRatio(fg, bg) {
    const l1 = luminance(fg);
    const l2 = luminance(bg);
    const hi = Math.max(l1, l2);
    const lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }

  // Blend a semi-transparent colour over an opaque one.
  function blend(top, bottom) {
    const a = top[3] === undefined ? 1 : top[3];
    return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a)).concat(1);
  }

  // ---------- DOM helpers (browser only) ----------
  function effectiveBackground(el) {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parseColor(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) {
        layers.push(c);
        if (c[3] >= 1) break;
      }
    }
    let bg = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
    return bg;
  }

  function textContrast(el) {
    const cs = getComputedStyle(el);
    const bg = effectiveBackground(el);
    let fg = parseColor(cs.color) || [0, 0, 0, 1];
    fg = blend(fg, bg);
    return contrastRatio(fg, bg);
  }

  function isHidden(el) {
    if (!el || !el.isConnected) return true;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') return true;
      if (parseFloat(cs.opacity) === 0) return true;
    }
    const r = el.getBoundingClientRect();
    return r.width * r.height < 4;
  }

  function area(el) {
    const r = el.getBoundingClientRect();
    return r.width * r.height;
  }

  function visibleText(el) {
    return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  // Amount in rupees found in a string, or null. Accepts ₹, Rs, Rs., INR.
  function parseAmount(s) {
    const m = String(s).replace(/,/g, '').match(/(?:₹|\brs\.?|\binr)\s*(\d+(?:\.\d+)?)/i);
    return m ? parseFloat(m[1]) : null;
  }

  // ---------- rule 1: countdown reset across reloads ----------
  const TIMER_RE = /(?<![\d:])(\d{1,2}):(\d{2})(?::(\d{2}))?(?![\d:])(?!\s*(?:am|pm|a\.m|p\.m|hrs|hours))/i;

  function timerSeconds(text) {
    const m = text.match(TIMER_RE);
    if (!m) return null;
    if (/\b(at|on)\s*$/i.test(text.slice(0, m.index))) return null; // "at 10:30" is a clock time
    const a = parseInt(m[1], 10), b = parseInt(m[2], 10), c = m[3] !== undefined ? parseInt(m[3], 10) : null;
    if (b > 59 || (c !== null && c > 59)) return null;
    return c === null ? a * 60 + b : a * 3600 + b * 60 + c;
  }

  function findTimers(doc) {
    const out = [];
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      const el = t.parentElement;
      if (!el || seen.has(el)) continue;
      const own = visibleText(el);
      if (own.length > 60) continue;
      const secs = timerSeconds(own);
      if (secs !== null && !isHidden(el)) {
        seen.add(el);
        out.push({ el, seconds: secs });
      }
    }
    return out;
  }

  // prevTimers: {path: {seconds, at}} from the previous page load (or null)
  function timerReset(timers, prevTimers, cfg, pathOf, loadId) {
    const findings = [];
    const slack = cfg.rules.timerSlackSeconds;
    for (const { el, seconds } of timers) {
      const p = prevTimers && prevTimers[pathOf(el)];
      if (!p || p.loadId === loadId) continue; // only compare across reloads
      const elapsed = (Date.now() - p.at) / 1000;
      const expected = p.seconds - elapsed;
      if (seconds > expected + slack) {
        findings.push({
          el, key: 'false_urgency', score: 1,
          evidence: `Timer showed ${p.seconds}s ${Math.round(elapsed)}s ago; after reload it shows ${seconds}s (expected about ${Math.max(0, Math.round(expected))}s).`
        });
      }
    }
    return findings;
  }

  // ---------- rule 2: pre-selected paid options ----------
  const COST_WORDS = /\b(donat\w*|insur\w*|protect\w*|membership|member|tip|warranty|add-?on|cover|pass|plan|premium|priority|assurance|guarantee|charity|contribut\w*)\b/i;

  function labelFor(input) {
    const doc = input.ownerDocument;
    if (input.id) {
      const l = doc.querySelector(`label[for="${CSS.escape(input.id)}"]`);
      if (l) return l;
    }
    const wrap = input.closest('label');
    if (wrap) return wrap;
    const lb = input.getAttribute('aria-labelledby');
    if (lb) {
      const l = doc.getElementById(lb.split(/\s+/)[0]);
      if (l) return l;
    }
    return null;
  }

  function optionText(ctrl) {
    const l = labelFor(ctrl);
    let s = (l ? visibleText(l) : '') + ' ' + (ctrl.getAttribute('aria-label') || '');
    if (s.trim().length < 3 && ctrl.parentElement) s += ' ' + visibleText(ctrl.parentElement).slice(0, 200);
    return s.trim();
  }

  function isPaidOption(text) {
    const amt = parseAmount(text);
    return (amt !== null && amt > 0) || (COST_WORDS.test(text) && amt !== 0);
  }

  function isChecked(ctrl) {
    if (ctrl.tagName === 'INPUT') return !!ctrl.checked;
    return ctrl.getAttribute('aria-checked') === 'true';
  }

  function preselected(doc, touched) {
    const findings = [];
    const ctrls = doc.querySelectorAll(
      'input[type=checkbox], input[type=radio], [role=checkbox], [role=switch], [role=radio]'
    );
    for (const ctrl of ctrls) {
      if (!isChecked(ctrl) || touched.has(ctrl)) continue;
      const lab = labelFor(ctrl);
      if (lab && touched.has(lab)) continue;
      const text = optionText(ctrl);
      if (!isPaidOption(text)) continue;
      const isRadio = ctrl.type === 'radio' || ctrl.getAttribute('role') === 'radio';
      if (isRadio) {
        // A selected radio is only suspicious if the group has a cheaper or free alternative.
        const myAmt = parseAmount(text) || 0;
        const group = ctrl.name
          ? [...doc.querySelectorAll(`input[type=radio][name="${CSS.escape(ctrl.name)}"]`)]
          : [...(ctrl.closest('[role=radiogroup]') || ctrl.parentElement).querySelectorAll('[role=radio]')];
        const cheaper = group.some((o) => o !== ctrl && (parseAmount(optionText(o)) || 0) < myAmt);
        if (!cheaper) continue;
      }
      // Highlight the visible control, or its label when the input itself is visually hidden.
      let target = ctrl;
      if (isHidden(ctrl) && lab && !isHidden(lab)) target = lab;
      if (isHidden(target)) continue;
      const how = ctrl.tagName === 'INPUT'
        ? (ctrl.hasAttribute('checked') ? 'ticked in the HTML' : 'ticked by a script')
        : `marked aria-checked=true (role=${ctrl.getAttribute('role')})`;
      findings.push({
        el: target, key: 'basket_sneaking', score: 1,
        evidence: `Paid option "${text.slice(0, 80)}" was ${how} before any user interaction.`
      });
    }
    return findings;
  }

  // ---------- rule 3: weak decline next to strong accept ----------
  const DECLINE_RE = /^(no\b|nope\b|not now|skip|decline|maybe later|cancel|continue without|i don'?t|i('ll| will) (pass|skip|take)|close|dismiss|remove)/i;
  const INTERACTIVE = 'a[href], button, [role=button], input[type=button], input[type=submit]';

  function controlText(el) {
    return (el.tagName === 'INPUT' ? el.value : visibleText(el)).replace(/[‘’]/g, "'");
  }

  function declineContrast(doc, cfg) {
    const findings = [];
    const all = [...doc.querySelectorAll(INTERACTIVE)].filter((e) => !isHidden(e));
    for (const d of all) {
      const dText = controlText(d);
      if (!DECLINE_RE.test(dText) && !/\bno,? thanks\b/i.test(dText)) continue;
      // nearest accept control sharing an ancestor within 4 levels
      let accept = null;
      let anc = d.parentElement;
      for (let lvl = 0; lvl < 4 && anc && !accept; lvl++, anc = anc.parentElement) {
        accept = all.find((a) => a !== d && anc.contains(a) && !DECLINE_RE.test(controlText(a)) && !/\bno,? thanks\b/i.test(controlText(a)));
      }
      if (!accept) continue;
      const dCR = textContrast(d), aCR = textContrast(accept);
      const dArea = area(d), aArea = area(accept);
      const ratio = aArea / Math.max(dArea, 1);
      const lowContrast = dCR < cfg.rules.contrastLimit && aCR >= cfg.rules.contrastLimit;
      const small = ratio >= cfg.rules.sizeRatio;
      if (!lowContrast && !small) continue;
      const score = lowContrast && small ? 1 : 0.8;
      findings.push({
        el: d, key: 'interface_interference', score,
        evidence: `Decline "${dText.slice(0, 40)}" has contrast ${dCR.toFixed(2)}:1 and area ${Math.round(dArea)}px²; ` +
          `accept "${controlText(accept).slice(0, 40)}" has contrast ${aCR.toFixed(2)}:1 and area ${Math.round(aArea)}px² (ratio ${ratio.toFixed(1)}).`,
        accept
      });
    }
    return findings;
  }

  // ---------- rule 4: fee lines with cross-step memory (drip pricing) ----------
  const FEE_RE = /\b(handling|convenience|platform|service|packaging|packing|surge|small cart|booking|processing|delivery)\s*(fees?|charges?)\b|\b(fees?|surcharge)\b/i;

  function feeLabel(text) {
    return text.replace(/(?:₹|\brs\.?|\binr)\s*[\d,]+(?:\.\d+)?/gi, '').replace(/[^a-z ]/gi, ' ')
      .replace(/\s+/g, ' ').trim().toLowerCase();
  }

  function findFeeLines(doc) {
    const out = [];
    const els = doc.body.querySelectorAll('li, tr, div, p, span, dd, dt');
    for (const el of els) {
      const t = visibleText(el);
      if (t.length === 0 || t.length > 120) continue;
      if (!FEE_RE.test(t)) continue;
      const amt = parseAmount(t);
      if (amt === null) continue;
      // keep the smallest element that contains both label and amount
      const childHas = [...el.children].some((c) => {
        const ct = visibleText(c);
        return FEE_RE.test(ct) && parseAmount(ct) !== null;
      });
      if (childHas || isHidden(el)) continue;
      out.push({ el, label: feeLabel(t), amount: amt, text: t });
    }
    return out;
  }

  function pricesShown(doc) {
    return parseAmount(visibleText(doc.body)) !== null;
  }

  // views: [{href, fees:[label], priceShown}] from earlier steps of this flow
  function dripFee(feeLines, views, href) {
    const findings = [];
    const earlier = (views || []).filter((v) => v.href !== href && v.priceShown);
    if (earlier.length === 0) return findings;
    for (const f of feeLines) {
      if (f.amount <= 0) continue;
      // a charge is dripped only if no earlier step showed it
      if (earlier.some((v) => v.fees.includes(f.label))) continue;
      const missingFrom = earlier;
      findings.push({
        el: f.el, key: 'drip_pricing', score: 1,
        evidence: `Charge "${f.text.slice(0, 60)}" was not shown on an earlier step (${missingFrom[0].href.replace(/^https?:\/\/[^/]+/, '')}) where prices were displayed.`
      });
    }
    return findings;
  }

  // ---------- rule 5: screen-covering sign-up / app walls ----------
  const WALL_RE = /\b(sign ?up|sign in|log ?in|login|register|create an account|download|install)\b/i;

  function overlayWall(doc, cfg) {
    const findings = [];
    const vw = root.innerWidth, vh = root.innerHeight;
    const seen = new Set();
    for (const el of doc.body.querySelectorAll('*')) {
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
      if (isHidden(el)) continue;
      const r = el.getBoundingClientRect();
      const w = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
      const h = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
      const cover = (w * h) / (vw * vh);
      if (cover < cfg.rules.overlayCoverage) continue;
      if ([...seen].some((s) => s.contains(el))) continue;
      const text = visibleText(el);
      if (!WALL_RE.test(text)) continue;
      seen.add(el);
      findings.push({
        el, key: 'forced_action', score: 1,
        evidence: `Fixed overlay covers ${(cover * 100).toFixed(0)}% of the viewport and asks the user to sign up, log in or install an app.`
      });
    }
    return findings;
  }

  PG.rules = {
    parseColor, luminance, contrastRatio, blend,
    effectiveBackground, textContrast, isHidden, area, visibleText, parseAmount,
    timerSeconds, findTimers, timerReset,
    labelFor, optionText, isPaidOption, preselected,
    declineContrast, DECLINE_RE,
    feeLabel, findFeeLines, pricesShown, dripFee,
    overlayWall
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = PG.rules;
})(typeof globalThis !== 'undefined' ? globalThis : this);
