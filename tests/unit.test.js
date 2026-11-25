// Node unit tests for the pure parts of PatternGuard (no browser).
// Run: node tests/unit.test.js
const assert = require('assert');
const path = require('path');
const ext = path.join(__dirname, '..', 'extension');
require(path.join(ext, 'categories.js'));
const rules = require(path.join(ext, 'rules.js'));
const text = require(path.join(ext, 'text.js'));
const S = require(path.join(ext, 'score.js'));

const results = [];
function test(name, fn) {
  try { fn(); results.push({ name, pass: true }); console.log('[PASS] ' + name); }
  catch (e) { results.push({ name, pass: false, error: e.message }); console.log('[FAIL] ' + name + ': ' + e.message); }
}

test('contrast black on white is 21:1', () => {
  const cr = rules.contrastRatio([0, 0, 0], [255, 255, 255]);
  assert.strictEqual(+cr.toFixed(2), 21);
});
test('contrast is symmetric and 1:1 for equal colours', () => {
  assert.strictEqual(rules.contrastRatio([255, 255, 255], [0, 0, 0]).toFixed(4), rules.contrastRatio([0, 0, 0], [255, 255, 255]).toFixed(4));
  assert.strictEqual(rules.contrastRatio([120, 30, 200], [120, 30, 200]), 1);
});
test('contrast #777 on white is about 4.48:1 (WCAG reference)', () => {
  assert.strictEqual(rules.contrastRatio(rules.parseColor('#777777'), [255, 255, 255]).toFixed(2), '4.48');
});
test('parseColor handles rgb, rgba and hex', () => {
  assert.deepStrictEqual(rules.parseColor('rgb(1, 2, 3)'), [1, 2, 3, 1]);
  assert.deepStrictEqual(rules.parseColor('rgba(1, 2, 3, 0.5)'), [1, 2, 3, 0.5]);
  assert.deepStrictEqual(rules.parseColor('#fff'), [255, 255, 255, 1]);
});
test('timerSeconds reads mm:ss and ignores clock times', () => {
  assert.strictEqual(rules.timerSeconds('Offer ends in 09:59'), 599);
  assert.strictEqual(rules.timerSeconds('01:00:05'), 3605);
  assert.strictEqual(rules.timerSeconds('Show at 10:30'), null);
  assert.strictEqual(rules.timerSeconds('10:30 PM'), null);
});
test('parseAmount reads rupee amounts', () => {
  assert.strictEqual(rules.parseAmount('Convenience fee ₹1,349'), 1349);
  assert.strictEqual(rules.parseAmount('Rs. 99 only'), 99);
  assert.strictEqual(rules.parseAmount('no price'), null);
});
test('text scorer: confirm shaming wording', () => {
  const r = text.score('No, I will take risk');
  assert.ok(r.vector[2] >= 0.9);
});
test('text scorer: neutral dismissal gives all zeros', () => {
  assert.ok(text.score('No, thanks').vector.every((v) => v === 0));
});
test('text scorer: empty and whitespace give all zeros', () => {
  assert.ok(text.score('   ').vector.every((v) => v === 0));
  assert.ok(text.score('').vector.every((v) => v === 0));
});
test('manipulation score follows eq. 3.7', () => {
  // 2 pages, 1 affected with 2 detections of weight 1 -> (1/2) * (2/2) = 0.5
  assert.strictEqual(S({ a: { detections: ['x', 'y'] }, b: { detections: [] } }, {}), 0.5);
});

const failed = results.filter((r) => !r.pass).length;
console.log(`\nUnit tests: ${results.length - failed}/${results.length} passed`);
require('fs').writeFileSync(path.join(__dirname, '..', 'report', 'unit_result.json'), JSON.stringify(results, null, 2));
process.exit(failed ? 1 : 0);
