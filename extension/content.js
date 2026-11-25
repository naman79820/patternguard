/* PatternGuard content script: candidate extraction, fusion, highlights, rescans.
 *
 * Fusion (report eq. 3.5 and 3.6):  c_k = alpha_k * r_k + (1 - alpha_k) * t_k,
 * report category k* = argmax_k c_k if c_k* >= tau.
 *
 * For testing and transparency, a JSON summary of the latest scan is written to the
 * data-patternguard attribute of <html>. It does not affect detection.
 */
(function () {
  'use strict';
  const PG = globalThis.PG;
  if (!PG || window.top !== window || globalThis.__patternguardLoaded) return;
  globalThis.__patternguardLoaded = true;

  const R = PG.rules;
  let CFG = null;            // { categories, tau, rules, rescanMinIntervalMs }
  const touched = new WeakSet();   // controls the user has interacted with
  const loadId = Math.random().toString(36).slice(2);
  const flowKey = 'pg:flow:' + location.origin + location.pathname; // fixed for this document
  const timerKey = 'pg:timers:' + location.origin + location.pathname;
  let scanCount = 0, redrawCount = 0, lastScanAt = 0, pendingTimer = null, lastSignature = '';
  let overlayRoot = null, overlayHost = null;

  // ---------- configuration ----------
  async function loadConfig() {
    // config.json is read by the service worker; retry briefly while it starts up.
    let cfg = null;
    for (let i = 0; i < 5 && !(cfg && cfg.categories); i++) {
      try { cfg = await chrome.runtime.sendMessage({ type: 'pg:getConfig' }); } catch (e) { cfg = null; }
      if (!(cfg && cfg.categories)) await new Promise((r) => setTimeout(r, 200 * (i + 1)));
    }
    if (!(cfg && cfg.categories)) throw new Error('PatternGuard: config.json could not be loaded');
    // merge numeric parameters from config.json with names and explanations from categories.js
    cfg.categories = PG.CATEGORIES.map((c) => {
      const o = cfg.categories.find((x) => x.key === c.key);
      if (!o) throw new Error('PatternGuard: config.json has no entry for ' + c.key);
      return { ...c, alpha: o.alpha, severity: o.severity };
    });
    return cfg;
  }

  // ---------- storage helpers (chrome.storage.local, never the page's storage) ----------
  async function getStore(key) {
    try { const o = await chrome.storage.local.get(key); return o[key]; } catch (e) { return undefined; }
  }
  async function setStore(key, val) {
    try { await chrome.storage.local.set({ [key]: val }); } catch (e) { /* ignore */ }
  }

  // ---------- DOM path ----------
  function pathOf(el) {
    if (el.id && document.querySelectorAll('#' + CSS.escape(el.id)).length === 1) return '#' + CSS.escape(el.id);
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && n !== document.documentElement; n = n.parentElement) {
      if (n.id && document.querySelectorAll('#' + CSS.escape(n.id)).length === 1) { parts.unshift('#' + CSS.escape(n.id)); break; }
      let i = 1;
      for (let s = n.previousElementSibling; s; s = s.previousElementSibling) if (s.tagName === n.tagName) i++;
      parts.unshift(n.tagName.toLowerCase() + ':nth-of-type(' + i + ')');
    }
    if (!parts[0] || !parts[0].startsWith('#')) parts.unshift('html');
    return parts.join(' > ');
  }

  // ---------- candidate extraction (FR1) ----------
  const INTERACTIVE_SEL = 'a[href], button, [role=button], input[type=button], input[type=submit], ' +
    'input[type=checkbox], input[type=radio], [role=checkbox], [role=switch], [role=radio], select, label';

  function extractCandidates() {
    const out = [];
    const hidden = [];
    const seen = new Set();
    const add = (el) => {
      if (seen.has(el) || (overlayHost && overlayHost.contains(el))) return;
      seen.add(el);
      if (R.isHidden(el)) { hidden.push(el); return; }
      out.push(el);
    };
    for (const el of document.body.querySelectorAll(INTERACTIVE_SEL)) add(el);
    // text-bearing elements outside interactive controls
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      if (!t.nodeValue.trim()) continue;
      const el = t.parentElement;
      if (!el || /^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(el.tagName)) continue;
      if (el.closest(INTERACTIVE_SEL) && !el.matches(INTERACTIVE_SEL)) continue;
      add(el);
    }
    return { candidates: out, hidden };
  }

  // ---------- user interaction tracking ----------
  function markTouched(e) {
    if (!e.isTrusted) return;
    const t = e.target instanceof Element ? e.target : null;
    if (!t) return;
    const ctrl = t.closest('input, [role=checkbox], [role=switch], [role=radio], label');
    if (!ctrl) return;
    touched.add(ctrl);
    if (ctrl.tagName === 'LABEL') {
      const c = ctrl.control || ctrl.querySelector('input, [role=checkbox], [role=switch], [role=radio]');
      if (c) touched.add(c);
    } else {
      const l = R.labelFor(ctrl);
      if (l) touched.add(l);
    }
    scheduleScan('user-input');
  }

  // ---------- scan ----------
  async function scan(reason) {
    const t0 = performance.now();
    lastScanAt = Date.now();
    scanCount++;
    const cats = CFG.categories;
    const K = cats.length;
    const { candidates, hidden } = extractCandidates();

    // structural evidence
    const findings = [];
    const prevTimers = (await getStore(timerKey)) || {};
    const memMs = CFG.rules.memoryMinutes * 60000;
    for (const p of Object.keys(prevTimers)) if (!prevTimers[p].cur || Date.now() - prevTimers[p].cur.at > memMs) delete prevTimers[p];
    const timers = R.findTimers(document);
    // stored per timer path: { prev: observation from an earlier load, cur: first observation in this load }
    const earlierLoad = {};
    for (const [p, e] of Object.entries(prevTimers)) {
      const o = e.cur && e.cur.loadId !== loadId ? e.cur : e.prev;
      if (o && o.loadId !== loadId) earlierLoad[p] = o;
    }
    findings.push(...R.timerReset(timers, earlierLoad, CFG, pathOf, loadId));
    findings.push(...R.preselected(document, touched));
    findings.push(...R.declineContrast(document, CFG));
    const feeLines = R.findFeeLines(document);
    let flow = (await getStore(flowKey)) || { views: [] };
    flow.views = flow.views.filter((v) => Date.now() - v.at < memMs);
    findings.push(...R.dripFee(feeLines, flow.views, location.href));
    findings.push(...R.overlayWall(document, CFG));

    // remember timers and this view for the next scan / reload
    const newTimers = { ...prevTimers };
    for (const { el, seconds } of timers) {
      const p = pathOf(el);
      // keep the first observation of this load, so a reload is compared with the earlier load
      const e = newTimers[p];
      if (!e) newTimers[p] = { prev: null, cur: { seconds, at: Date.now(), loadId } };
      else if (e.cur.loadId !== loadId) newTimers[p] = { prev: e.cur, cur: { seconds, at: Date.now(), loadId } };
    }
    await setStore(timerKey, newTimers);
    const view = flow.views.find((v) => v.href === location.href);
    const fees = feeLines.map((f) => f.label);
    if (view) { view.fees = [...new Set(view.fees.concat(fees))]; view.priceShown = view.priceShown || R.pricesShown(document); view.at = Date.now(); }
    else flow.views.push({ href: location.href, fees, priceShown: R.pricesShown(document), at: Date.now() });
    await setStore(flowKey, flow);

    // element -> rule vector
    const ruleVec = new Map();
    const evidence = new Map();
    for (const f of findings) {
      const k = cats.findIndex((c) => c.key === f.key);
      if (!ruleVec.has(f.el)) { ruleVec.set(f.el, new Array(K).fill(0)); evidence.set(f.el, {}); }
      const v = ruleVec.get(f.el);
      if (f.score > v[k]) { v[k] = f.score; evidence.get(f.el)[f.key] = f.evidence; }
    }

    // fuse every candidate and every element with rule evidence
    const elements = [...new Set(candidates.concat([...ruleVec.keys()]))];
    const detections = [];
    for (const el of elements) {
      const text = el.tagName === 'INPUT' ? (el.value || '') : R.visibleText(el);
      const t = PG.text.score(text, cats);
      const r = ruleVec.get(el) || new Array(K).fill(0);
      const isControl = el.matches(INTERACTIVE_SEL);
      const tv = t.vector.map((v, k) => (cats[k].textScope === 'control' && !isControl ? 0 : v));
      const c = cats.map((cat, k) => cat.alpha * r[k] + (1 - cat.alpha) * tv[k]);
      let kStar = 0;
      for (let k = 1; k < K; k++) if (c[k] > c[kStar]) kStar = k;
      if (c[kStar] >= CFG.tau) {
        const cat = cats[kStar];
        const why = (evidence.get(el) || {})[cat.key] ||
          (t.matches.find((m) => m.key === cat.key) ? `Text matched ${cat.name.toLowerCase()} wording: "${text.slice(0, 80)}"` : '');
        detections.push({
          el, category: cat.id, key: cat.key, name: cat.name, confidence: +c[kStar].toFixed(3),
          r: +r[kStar].toFixed(3), t: +tv[kStar].toFixed(3), alpha: cat.alpha,
          text: (el.tagName === 'INPUT' || el.matches('[role=checkbox],[role=switch],[role=radio]') ? R.optionText(el) : text).slice(0, 120),
          evidence: why, explanation: cat.explain
        });
      }
    }
    // if an element and one of its descendants report the same category, keep the descendant
    const kept = detections.filter((d) => !detections.some((o) => o !== d && o.key === d.key && d.el.contains(o.el)));

    const signature = JSON.stringify(kept.map((d) => {
      const b = d.el.getBoundingClientRect();
      return [pathOf(d.el), d.key, Math.round(b.left + scrollX), Math.round(b.top + scrollY), Math.round(b.width), Math.round(b.height)];
    }));
    if (signature !== lastSignature) {
      draw(kept);
      lastSignature = signature;
    }
    const scanMs = performance.now() - t0;
    const nav = performance.getEntriesByType('navigation')[0];
    const sinceLoad = nav && nav.loadEventEnd > 0 && scanCount === 1 ? performance.now() - nav.loadEventEnd : null;

    const records = kept.map((d) => ({
      category: d.category, key: d.key, name: d.name, confidence: d.confidence, r: d.r, t: d.t, alpha: d.alpha,
      path: pathOf(d.el), text: d.text, evidence: d.evidence
    }));
    let score = null;
    try {
      score = await chrome.runtime.sendMessage({
        type: 'pg:results', page: location.origin + location.pathname + location.hash, href: location.href,
        detections: records.map(({ category, key, name, confidence, path, evidence, text }) => ({ category, key, name, confidence, path, evidence, text })),
        severity: Object.fromEntries(cats.map((c) => [c.key, c.severity]))
      });
    } catch (e) { /* background unavailable */ }

    document.documentElement.setAttribute('data-patternguard', JSON.stringify({
      href: location.href, reason, scanCount, redrawCount, scanAt: Date.now(),
      scanMs: +scanMs.toFixed(2), sinceLoadMs: sinceLoad === null ? null : +sinceLoad.toFixed(2),
      tau: CFG.tau, detections: records,
      candidateCount: candidates.length, candidates: candidates.map(pathOf),
      hidden: hidden.map(pathOf),
      manipulationScore: score && typeof score.S === 'number' ? score.S : null
    }));
  }

  // ---------- highlights (FR6) ----------
  function ensureOverlay() {
    if (overlayHost && overlayHost.isConnected) return;
    overlayHost = document.createElement('patternguard-overlay');
    overlayHost.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;z-index:2147483647;pointer-events:none;';
    overlayRoot = overlayHost.attachShadow({ mode: 'open' });
    document.documentElement.appendChild(overlayHost);
  }

  function draw(dets) {
    ensureOverlay();
    redrawCount++;
    const frag = document.createDocumentFragment();
    const style = document.createElement('style');
    style.textContent =
      '.box{position:absolute;border:2px solid #c0392b;border-radius:3px;pointer-events:none;box-sizing:border-box}' +
      '.tag{position:absolute;background:#c0392b;color:#fff;font:11px/1.35 Arial,sans-serif;padding:2px 6px;' +
      'border-radius:3px;width:max-content;max-width:440px;white-space:normal;pointer-events:none}';
    frag.appendChild(style);
    const placed = []; // tag rectangles already used, in document coordinates
    const overlaps = (a) => placed.some((b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b);
    for (const d of dets) {
      const b = d.el.getBoundingClientRect();
      const left = b.left + scrollX - 3, top = b.top + scrollY - 3, w = b.width + 6, h = b.height + 6;
      const box = document.createElement('div');
      box.className = 'box';
      Object.assign(box.style, { left: left + 'px', top: top + 'px', width: w + 'px', height: h + 'px' });
      const tag = document.createElement('div');
      tag.className = 'tag';
      tag.textContent = `${d.name} (CCPA): ${d.explanation}`;
      box.appendChild(tag);
      frag.appendChild(box);
      // estimate the tag size, then place it above the box, or below if that spot is taken
      const tw = Math.min(440, 7 + tag.textContent.length * 5.6), th = tw >= 440 ? 32 : 18;
      const above = { l: left, r: left + tw, t: top - th - 2, b: top - 2 };
      const below = { l: left, r: left + tw, t: top + h + 2, b: top + h + th + 2 };
      const spot = overlaps(above) && !overlaps(below) ? below : above;
      tag.style.left = '-2px';
      tag.style.top = (spot === above ? -(th + 2) : h + 2) + 'px';
      placed.push(spot);
    }
    overlayRoot.replaceChildren(frag);
  }

  // ---------- rescans on page changes, at most once per interval ----------
  function scheduleScan(reason) {
    if (pendingTimer) return;
    const wait = Math.max(0, lastScanAt + CFG.rescanMinIntervalMs - Date.now());
    pendingTimer = setTimeout(() => { pendingTimer = null; scan(reason); }, wait);
  }

  function relevant(m) {
    if (overlayHost && (m.target === overlayHost || overlayHost.contains(m.target))) return false;
    if (m.type === 'attributes') {
      if (m.target === document.documentElement && m.attributeName === 'data-patternguard') return false;
      return true;
    }
    if (m.type === 'childList') {
      const nodes = [...m.addedNodes, ...m.removedNodes];
      // text-only swaps (e.g. a ticking timer) do not trigger a rescan
      return nodes.some((n) => n.nodeType === 1 && n !== overlayHost);
    }
    return false;
  }

  async function main() {
    CFG = await loadConfig();
    for (const ev of ['click', 'change', 'keydown']) document.addEventListener(ev, markTouched, true);
    await scan('initial');
    new MutationObserver((ms) => { if (ms.some(relevant)) scheduleScan('mutation'); })
      .observe(document.documentElement, {
        childList: true, subtree: true, attributes: true,
        attributeFilter: ['class', 'style', 'hidden', 'checked', 'aria-checked', 'open']
      });
    window.addEventListener('hashchange', () => scheduleScan('hashchange'));
    window.addEventListener('popstate', () => scheduleScan('popstate'));
  }

  if (document.readyState === 'complete') main();
  else window.addEventListener('load', main, { once: true });
})();
