/* PatternGuard service worker: serves configuration, stores per-tab results and
 * per-site detections, computes the site-level Manipulation Score S (report eq. 3.7)
 * and sets the toolbar badge. Everything stays in chrome.storage on this machine. */
importScripts('categories.js', 'score.js');

let configPromise = null;
// config.json holds alpha_k, severity w_k, tau and rule thresholds (requirement R4).
function getConfig() {
  if (!configPromise) {
    configPromise = fetch(chrome.runtime.getURL('config.json'))
      .then((r) => r.json())
      .catch((e) => { configPromise = null; throw e; });
  }
  return configPromise;
}

async function storeResults(msg, sender) {
  const tabId = sender.tab ? sender.tab.id : -1;
  const origin = new URL(msg.href).origin;
  const siteKey = 'pg:site:' + origin;
  const site = (await chrome.storage.local.get(siteKey))[siteKey] || { pages: {} };
  site.pages[msg.page] = { detections: msg.detections.map((d) => d.key), at: Date.now() };
  await chrome.storage.local.set({ [siteKey]: site });
  const S = PG.manipulationScore(site.pages, msg.severity);
  const tabRecord = { href: msg.href, page: msg.page, origin, detections: msg.detections, S,
    pagesAnalysed: Object.keys(site.pages).length, at: Date.now() };
  await chrome.storage.local.set({ ['pg:tab:' + tabId]: tabRecord });
  if (tabId >= 0) {
    const n = msg.detections.length;
    chrome.action.setBadgeText({ tabId, text: n ? String(n) : '' });
    chrome.action.setBadgeBackgroundColor({ tabId, color: '#c0392b' });
  }
  return { S };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'pg:getConfig') { getConfig().then(sendResponse, () => sendResponse(null)); return true; }
  if (msg && msg.type === 'pg:results') { storeResults(msg, sender).then(sendResponse); return true; }
  return false;
});

chrome.tabs.onRemoved.addListener((tabId) => chrome.storage.local.remove('pg:tab:' + tabId));
