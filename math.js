/* Self-hosted KaTeX; source text remains readable if the renderer is unavailable. */
function typesetMath(root) {
  if (typeof renderMathInElement !== 'function') return;
  renderMathInElement(root, {
    delimiters: [{left: '\\(', right: '\\)', display: false}, {left: '\\[', right: '\\]', display: true}],
    throwOnError: false, trust: false, strict: 'warn', maxExpand: 100,
    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option']
  });
}
