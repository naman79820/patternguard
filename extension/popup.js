(async function () {
  const params = new URLSearchParams(location.search);
  let tabId = params.has('tab') ? parseInt(params.get('tab'), 10) : null;
  if (tabId === null) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    tabId = tab ? tab.id : -1;
  }
  const key = 'pg:tab:' + tabId;
  const rec = (await chrome.storage.local.get(key))[key];
  const list = document.getElementById('list');
  if (!rec) {
    document.getElementById('site').textContent = 'No scan for this tab yet.';
    return;
  }
  document.getElementById('site').textContent = rec.origin;
  document.getElementById('S').textContent = rec.S.toFixed(2);
  document.getElementById('pages').textContent = `${rec.pagesAnalysed} page(s) analysed on this site; ${rec.detections.length} detection(s) on this page.`;
  if (rec.detections.length === 0) {
    const d = document.createElement('div');
    d.className = 'empty';
    d.textContent = 'No dark patterns detected on this page.';
    list.replaceWith(d);
    return;
  }
  for (const det of rec.detections) {
    const li = document.createElement('li');
    const c = document.createElement('div'); c.className = 'cat'; c.textContent = `${det.name} (${(det.confidence * 100).toFixed(0)}%)`;
    const t = document.createElement('div'); t.textContent = det.text;
    const e = document.createElement('div'); e.className = 'ev'; e.textContent = det.evidence;
    li.append(c, t, e);
    list.appendChild(li);
  }
})();
