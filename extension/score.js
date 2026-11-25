/* Site-level Manipulation Score (report eq. 3.7):
 *   S = (Pa / P) * (sum_k w_k * n_k) / P
 * P  = analysed pages of the site, Pa = pages with at least one detection,
 * n_k = detections in category k, w_k = severity weight of category k. */
(function (root) {
  const PG = (root.PG = root.PG || {});
  // pages: { pageKey: { detections: [categoryKey, ...] } }, severity: { categoryKey: w_k }
  PG.manipulationScore = function (pages, severity) {
    const keys = Object.keys(pages);
    const P = keys.length;
    if (P === 0) return 0;
    const Pa = keys.filter((k) => pages[k].detections.length > 0).length;
    let weighted = 0;
    for (const k of keys) for (const cat of pages[k].detections) weighted += (severity && severity[cat] != null ? severity[cat] : 1);
    return +((Pa / P) * (weighted / P)).toFixed(4);
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = PG.manipulationScore;
})(typeof globalThis !== 'undefined' ? globalThis : this);
