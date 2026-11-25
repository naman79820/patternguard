// Playwright-side candidate extraction (crawler capture procedure), written separately
// from extension/content.js but following the same candidate definition (report Table 4.3):
// interactive controls plus visible elements that carry their own text.
// Evaluated with page.evaluate(); returns an array of DOM paths.
() => {
  const INTERACTIVE = ['a[href]', 'button', '[role=button]', 'input[type=button]', 'input[type=submit]',
    'input[type=checkbox]', 'input[type=radio]', '[role=checkbox]', '[role=switch]', '[role=radio]', 'select', 'label'].join(',');
  const hidden = (el) => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse' || parseFloat(cs.opacity) === 0) return true;
    }
    const r = el.getBoundingClientRect();
    return r.width * r.height < 4;
  };
  const unique = (id) => document.querySelectorAll('#' + CSS.escape(id)).length === 1;
  const path = (el) => {
    if (el.id && unique(el.id)) return '#' + CSS.escape(el.id);
    const parts = [];
    let n = el;
    while (n && n.nodeType === 1 && n !== document.documentElement) {
      if (n.id && unique(n.id)) { parts.unshift('#' + CSS.escape(n.id)); break; }
      const same = [...n.parentElement.children].filter((c) => c.tagName === n.tagName);
      parts.unshift(n.tagName.toLowerCase() + ':nth-of-type(' + (same.indexOf(n) + 1) + ')');
      n = n.parentElement;
    }
    if (!parts[0].startsWith('#')) parts.unshift('html');
    return parts.join(' > ');
  };
  const found = new Set();
  document.body.querySelectorAll(INTERACTIVE).forEach((el) => found.add(el));
  document.body.querySelectorAll('*').forEach((el) => {
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(el.tagName) || el.tagName.includes('-')) return;
    const ownText = [...el.childNodes].some((c) => c.nodeType === 3 && c.nodeValue.trim());
    if (!ownText) return;
    const ctl = el.closest(INTERACTIVE);
    if (ctl && ctl !== el) return;
    found.add(el);
  });
  return [...found].filter((el) => !hidden(el)).map(path);
}
