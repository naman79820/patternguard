// Run extension/text.js on a JSON array of strings read from a file (argv[2]);
// writes a JSON array of {input_length, processed_length, vector, top_key, top_conf, matches} to stdout.
const fs = require('fs');
const path = require('path');
const ext = path.join(__dirname, '..', 'extension');
const PG = require(path.join(ext, 'categories.js'));
const text = require(path.join(ext, 'text.js'));
const inputs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = inputs.map((s) => {
  const r = text.score(s);
  let k = 0;
  for (let i = 1; i < r.vector.length; i++) if (r.vector[i] > r.vector[k]) k = i;
  return {
    input_length: (s || '').length, processed_length: r.text.length, vector: r.vector,
    top_key: r.vector[k] > 0 ? PG.CATEGORIES[k].key : null, top_conf: r.vector[k],
    matches: r.matches.map((m) => m.key)
  };
});
process.stdout.write(JSON.stringify(out));
