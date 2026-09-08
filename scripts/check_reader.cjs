// node scripts/check_reader.cjs [optional draft JSON]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const Reader = require('../plasma/reader.js');
const katex = require('../vendor/katex/katex.min.js');
const root = path.resolve(__dirname, '..');
const paper = (topics, methods = ['数值模拟'], brief = {}) => ({topics, methods, brief, title: ''});
const fusion = paper(['聚变中的重联']);
const experiment = paper(['聚变中的重联'], ['实验 / 观测']);
const solar = paper(['磁场重联']);
assert(Reader.compare(fusion, experiment) < 0);
assert(Reader.compare(experiment, solar) < 0);
assert.deepEqual([solar, experiment, fusion].sort(Reader.compare), [fusion, experiment, solar]);
assert.equal(Reader.priority({...solar, title: 'MRX electron layer'}), 1);
assert.equal(Reader.priority({...paper(['聚变等离子体']), title: 'Error field penetration in DIII-D'}), 0);
assert.deepEqual(Reader.paragraphs('one\n\n two\n\n'), ['one', 'two']);
const highlight = {key: '2026-09-08T114713Z:2609.02803v1:methods:0', text: 'A paragraph', saved_at: new Date().toISOString()};
assert.equal(Reader.validateHighlights([highlight]).length, 1);
assert.equal(Reader.validateHighlights([{...highlight, key: highlight.key.replace('2026-09-08T114713Z','2026-09-08')}]).length, 1);
for (const invalid of [[highlight, highlight], [{...highlight, key: 'bad'}], [{...highlight, text: 5}], [{...highlight, saved_at: 'bad'}]]) assert.throws(() => Reader.validateHighlights(invalid));

let formulaCount = 0;
function checkMath(text) {
  assert.equal((text.match(/\\\(/g) || []).length, (text.match(/\\\)/g) || []).length, 'Unbalanced inline math');
  assert.equal((text.match(/\\\[/g) || []).length, (text.match(/\\\]/g) || []).length, 'Unbalanced display math');
  for (const m of text.matchAll(/\\\((.*?)\\\)|\\\[(.*?)\\\]/gs)) {
    const tex = (m[1] ?? m[2]).replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
    try {
      katex.renderToString(tex, {throwOnError: true, strict: 'error', trust: false, maxExpand: 100, displayMode: m[2] !== undefined});
    } catch (error) { throw new Error('Invalid TeX: ' + tex + '\n' + error.message); }
    formulaCount++;
  }
}
const html = fs.readFileSync(path.join(root, 'cuda/index.html'), 'utf8');
checkMath(html);
checkMath(fs.readFileSync(path.join(root, 'investing/index.html'), 'utf8'));
const dcfValue = require('../investing/calculator.js');
const dcfInput = {cashflow:10, growth:0, discount:10, terminal:0, extra:20, shares:10};
assert(Math.abs(dcfValue(dcfInput).perShare - 12) < 1e-10);
assert(dcfValue({...dcfInput, discount:12}).perShare < 12);
assert.equal(dcfValue({...dcfInput, cashflow:0}).perShare, 2);
for (const change of [{shares:0}, {discount:0}, {terminal:10}, {growth:-100},
                      {extra:Infinity}, {cashflow:NaN}, {shares:Number.MIN_VALUE}])
  assert.throws(() => dcfValue({...dcfInput, ...change}));
assert.equal((html.match(/class="equation"/g) || []).length, 14);
assert(!/<div class="equation"[^>]*>[^\\]/.test(html), 'Every equation panel must use TeX');
assert.equal((html.match(/<pre\b/g) || []).length, (html.match(/<pre[^>]*data-language="[^"]+"[^>]*><code>/g) || []).length);
assert(!/<pre[^>]*>[^]*?\\\(/.test(html.split('</pre>')[0]), 'Math and code must stay separate');
for (const name of ['math.js','plasma/reader.js','plasma/app.js','cuda/book.js']) new vm.Script(fs.readFileSync(path.join(root,name),'utf8'), {filename:name});
const files = fs.readdirSync(path.join(root, 'plasma/data/issues')).map(f => path.join(root, 'plasma/data/issues', f));
if (process.argv[2]) files.push(path.resolve(process.argv[2]));
for (const file of files) {
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  checkMath(data.overview || '');
  const briefs = data.briefs ? Object.values(data.briefs) : data.papers.filter(p => p.brief).map(p => p.brief);
  for (const brief of briefs) for (const value of Object.values(brief)) if (typeof value === 'string') checkMath(value);
}
const css = fs.readFileSync(path.join(root, 'vendor/katex/katex.min.css'), 'utf8');
for (const [,url] of css.matchAll(/url\(([^)]+)\)/g)) assert(fs.existsSync(path.join(root, 'vendor/katex',url)), `Missing font ${url}`);
// Hand-worked index examples: no missing/duplicate array updates, including tail threads.
for (const [n, threads, blocks] of [[10,4,3],[10,4,2],[17,8,3],[17,8,2]]) {
  const seen = Array(n).fill(0);
  for (let b=0;b<blocks;b++) for (let t=0;t<threads;t++) for (let i=b*threads+t;i<n;i+=blocks*threads) seen[i]++;
  assert(seen.every(count => count===1));
}
console.log(`PASS: relevance, annotation validation, ${formulaCount} TeX expressions, code blocks, local math fonts and index examples.`);
