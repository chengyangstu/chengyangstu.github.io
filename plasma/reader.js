/* Explicit editorial relevance takes precedence; archived issues retain a topic fallback. */
const Reader = {
  priority(p) {
    if (Number.isInteger(p.brief?.relevance_tier)) return p.brief.relevance_tier;
    if (p.topics.includes('聚变中的重联')) return 0;
    if (p.topics.includes('聚变等离子体') && /\b(reconnect\w*|\w*tearing|magnetic islands?|sawtooth|sawteeth|internal kink|error.field penetration)\b/i.test(p.title + ' ' + (p.abstract || ''))) return 0;
    if (p.topics.includes('磁场重联') && /\b(MRX|TREX|FLARE|laboratory)\b/i.test(p.title)) return 1;
    if (p.topics.includes('磁场重联')) return 2;
    return 3;
  },
  compare(a, b) {
    return Reader.priority(a) - Reader.priority(b) ||
      Number(b.methods.some(m => m === '理论' || m === '数值模拟') && !b.methods.includes('实验 / 观测')) -
      Number(a.methods.some(m => m === '理论' || m === '数值模拟') && !a.methods.includes('实验 / 观测')) ||
      Number(Boolean(b.brief)) - Number(Boolean(a.brief));
  },
  paragraphs(text) { return text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean); },
  validateHighlights(items) {
    if (!Array.isArray(items) || items.length > 10000) throw Error('高亮备份格式或数量无效');
    const keys = new Set();
    for (const item of items) {
      if (!item || !/^\d{4}-\d{2}-\d{2}(?:-r(?:[2-9]|[1-9]\d+)|T\d{6}Z)?:\d{4}\.\d{4,5}v\d+:(takeaway|question|methods|findings|limitations|reading|evidence):\d+$/.test(item.key) ||
          keys.has(item.key) || typeof item.text !== 'string' || item.text.length > 20000 || !Number.isFinite(Date.parse(item.saved_at))) throw Error('高亮条目无效或重复');
      keys.add(item.key);
    }
    return items;
  }
};
if (typeof module !== 'undefined') module.exports = Reader;
