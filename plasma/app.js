const $ = id => document.getElementById(id);
const storageKey = 'yancheng-plasma-bookmarks-v1';
const state = {view: 'papers', topic: 'all', method: 'all', query: '', index: [], issue: null, saved: [], request: 0, expanded: new Set()};
let storageBroken = false;
let toastTimer;
const validId = value => typeof value === 'string' && /^\d{4}\.\d{4,5}(v\d+)?$/.test(value);
const validIssue = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{6}Z$/.test(value);
const date = value => new Date(value).toLocaleDateString('zh-CN', {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'});
const issueLabel = value => date(value) + ' ' + new Date(value).toLocaleTimeString('zh-CN', {timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit'});
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function action(text, run, className = 'text-button') {
  const button = el('button', text, className);
  button.type = 'button';
  button.addEventListener('click', run);
  return button;
}
function link(text, url) {
  const node = el('a', text);
  node.href = url;
  node.target = '_blank';
  node.rel = 'noopener noreferrer';
  return node;
}
function toast(text) {
  $('toast').textContent = text;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').hidden = true, 4500);
}
function validateSaved(items) {
  if (!Array.isArray(items) || items.length > 5000) throw Error('收藏文件格式不正确');
  const keys = new Set();
  for (const item of items) {
    const p = item?.paper;
    if (!p || !validId(p.id) || !validId(p.version) || !validIssue(item.issue_id) || item.key !== `${item.issue_id}:${p.version}` || keys.has(item.key)) throw Error('收藏条目无效或重复');
    if (!['title', 'abstract', 'published', 'source_basis'].every(k => typeof p[k] === 'string') || !Number.isFinite(Date.parse(p.published))) throw Error('论文信息不完整');
    for (const k of ['authors', 'topics', 'methods']) if (!Array.isArray(p[k]) || !p[k].every(v => typeof v === 'string')) throw Error('论文字段无效');
    if (p.brief && !['title_zh', 'takeaway', 'question', 'methods', 'findings', 'limitations', 'reading', 'evidence'].every(k => typeof p.brief[k] === 'string')) throw Error('简报内容不完整');
    keys.add(item.key);
  }
  return items;
}
try { state.saved = validateSaved(JSON.parse(localStorage.getItem(storageKey) || '[]')); }
catch { storageBroken = true; }
function persist(items) {
  if (storageBroken) { toast('收藏存储读取失败，已停止写入以保护原始数据。请先导出备份。'); return false; }
  try { localStorage.setItem(storageKey, JSON.stringify(items)); state.saved = items; return true; }
  catch { toast('浏览器未能保存收藏，可能空间不足；已有收藏未被删除。请导出备份。'); return false; }
}
function key(p, issueId) { return `${issueId}:${p.version}`; }
function bookmark(p, issueId) {
  const k = key(p, issueId);
  const saved = state.saved.some(item => item.key === k);
  const button = action(saved ? '★ 已收藏' : '☆ 收藏', () => {
    const exists = state.saved.some(item => item.key === k);
    const next = exists ? state.saved.filter(item => item.key !== k) : [...state.saved, {key: k, issue_id: issueId, saved_at: new Date().toISOString(), paper: {...p, source_basis: p.source_basis || '仅摘要'}}];
    if (!persist(next)) return;
    toast(exists ? '已移出收藏' : '已收藏论文与当前简报');
    render();
    button.textContent = exists ? '☆ 收藏' : '★ 已收藏';
    button.setAttribute('aria-pressed', String(!exists));
  }, 'bookmark');
  button.setAttribute('aria-label', `${saved ? '取消收藏' : '收藏'}：${p.title}`);
  button.setAttribute('aria-pressed', String(saved));
  return button;
}
function download(name, data, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([data], {type}));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function markdown(p) {
  const b = p.brief;
  const lines = [`# ${p.title}`, '', p.authors.join(', '), '', `arXiv: https://arxiv.org/abs/${p.version}`, `首次提交：${p.published}`, `阅读依据：${p.source_basis || '仅摘要'}`, ''];
  if (b) for (const [field, title] of sections) lines.push(`## ${title}`, '', b[field], '');
  else lines.push('## 原始摘要', '', p.abstract);
  lines.push('', 'AI 辅助阅读，请以原文为准。');
  return lines.join('\n');
}
const sections = [['takeaway', '一句话速读'], ['question', '研究问题'], ['methods', '方法与模型'], ['findings', '主要发现'], ['limitations', '局限与待核实'], ['reading', '阅读建议'], ['evidence', '原文定位']];
function paperDetails(p, issueId) {
  const details = el('details', undefined, 'brief');
  const summary = el('summary', p.brief ? '阅读简报' : '查看摘要');
  const body = el('div', undefined, 'brief-body');
  const k = key(p, issueId);
  details.open = state.expanded.has(k);
  details.addEventListener('toggle', () => { if (details.open) state.expanded.add(k); else state.expanded.delete(k); });
  if (p.brief) {
    body.append(el('p', p.brief.title_zh, 'translated-title'));
    for (const [field, title] of sections) {
      const section = el('section'); section.append(el('h3', title), el('p', p.brief[field])); body.append(section);
    }
  } else {
    body.append(el('p', '此文保留在本期候选清单中，尚无中文阅读简报。'), el('h3', 'arXiv 原始摘要'), el('p', p.abstract));
  }
  body.append(el('p', '首次提交：' + p.published + '\n版本：' + p.version + '\n阅读依据：' + (p.source_basis || '仅摘要') + '。PDF 文本提取不等于逐图审阅，请核对原文。', 'muted'));
  const actions = el('div', undefined, 'actions');
  actions.append(link('PDF 原文 ↗', `https://arxiv.org/pdf/${p.version}`), action('下载简报', () => download(`${p.version}-brief.md`, markdown(p), 'text/markdown;charset=utf-8')));
  body.append(actions); details.append(summary, body);
  return details;
}
function overallReport(issue) {
  const article = el('article', undefined, 'paper overall');
  article.append(el('h2', '本周总体报告'), el('p', issue.overview, 'takeaway'));
  const details = el('details', undefined, 'brief');
  details.open = state.expanded.has(issue.id + ':overall');
  details.addEventListener('toggle', () => { if (details.open) state.expanded.add(issue.id + ':overall'); else state.expanded.delete(issue.id + ':overall'); });
  details.append(el('summary', '阅读总体报告'));
  const list = el('ol', undefined, 'brief-body overview-list');
  const reports = issue.overall_report || issue.papers.filter(p => p.brief).map(p => ({id: p.id, title: p.brief.title_zh, summary: p.brief.takeaway}));
  for (const report of reports) { const item = el('li'); item.append(el('strong', report.title), el('p', report.summary)); list.append(item); }
  details.append(list); article.append(details);
  return article;
}
function row(p, issueId) {
  const article = el('article', undefined, 'paper');
  article.id = 'paper-' + p.id;
  const meta = el('div', undefined, 'paper-meta');
  const labels = el('span', `${p.topics.join(' / ')} · ${p.methods.join(' / ')}`);
  const time = el('time', date(p.published)); time.dateTime = p.published; labels.append(time);
  meta.append(labels, bookmark(p, issueId));
  const authors = p.authors.length > 5 ? p.authors.slice(0, 5).join(', ') + ' et al.' : p.authors.join(', ');
  const actions = el('div', undefined, 'actions');
  actions.append(link('arXiv ↗', `https://arxiv.org/abs/${p.version}`), el('span', p.brief ? p.source_basis : '候选论文 · 尚未精读', 'source-note'));
  article.append(meta, el('h2', p.title), el('p', p.brief?.takeaway || '本期相关候选论文，展开查看原始摘要。', 'takeaway'), el('p', authors, 'authors'), actions, paperDetails(p, issueId));
  return article;
}
function render() {
  $('saved-count').textContent = state.saved.length;
  document.querySelectorAll('[data-view]').forEach(b => { b.classList.toggle('active', b.dataset.view === state.view); b.setAttribute('aria-pressed', String(b.dataset.view === state.view)); });
  $('toolbar').hidden = state.view === 'archive';
  $('save-tools').hidden = state.view !== 'saved';
  $('intro').replaceChildren(); $('list').replaceChildren();
  if (state.view === 'archive') {
    $('intro').append(el('p', `共 ${state.index.length} 期。所有简报独立存档，新一期不会覆盖旧一期。`));
    for (const issue of state.index) {
      const line = el('article', undefined, 'archive-row'); const info = el('div');
      info.append(el('h2', issueLabel(issue.window_end)), el('p', `${date(issue.window_start)} — ${date(issue.window_end)} · ${issue.paper_count} 篇论文 · ${issue.brief_count} 份简报`));
      line.append(info, action('打开周报 →', () => { state.view = 'papers'; $('week').value = issue.id; loadIssue(issue.id); })); $('list').append(line);
    }
    if (!state.index.length) $('list').append(el('div', '首期周报正在准备。', 'empty'));
    return;
  }
  let papers = state.view === 'saved' ? state.saved.map(s => ({p: s.paper, issueId: s.issue_id})) : (state.issue?.papers || []).map(p => ({p, issueId: state.issue.id}));
  if (state.view === 'papers' && state.issue) {
    const i = state.issue;
    $('intro').append(el('strong', `${date(i.window_start)} — ${date(i.window_end)} · ${i.papers.length} 篇论文 / ${i.papers.filter(p => p.brief).length} 份简报`));
    $('list').append(overallReport(i));
    papers.sort((a, b) => Number(Boolean(b.p.brief)) - Number(Boolean(a.p.brief)));
  } else $('intro').append(el('p', `我的收藏 · ${state.saved.length} 条`));
  const query = state.query.trim().toLowerCase();
  const filtered = papers.filter(({p}) => (state.topic === 'all' || p.topics.includes(state.topic)) && (state.method === 'all' || p.methods.includes(state.method)) && (!query || [p.title, p.abstract, ...p.authors, ...Object.values(p.brief || {})].join(' ').toLowerCase().includes(query)));
  for (const {p, issueId} of filtered) $('list').append(row(p, issueId));
  if (!filtered.length) $('list').append(el('div', state.view === 'saved' && !state.saved.length ? '还没有收藏。读到有意思的论文，点一下「☆ 收藏」。' : '没有匹配的论文，试试其他关键词或筛选条件。', 'empty'));
}
async function loadIssue(id) {
  const request = ++state.request;
  if (!validIssue(id)) return;
  $('list').replaceChildren(el('div', '正在读取周报…', 'empty'));
  try {
    const response = await fetch(`data/issues/${id}.json`);
    if (!response.ok) throw Error('HTTP ' + response.status);
    const issue = await response.json();
    if (request !== state.request) return;
    if (issue.id !== id || !Array.isArray(issue.papers)) throw Error('Invalid issue');
    state.issue = issue; $('week').value = id;
    const url = new URL(location.href); url.searchParams.set('issue', id); history.replaceState(null, '', url);
    render();
  } catch { if (request === state.request) $('list').replaceChildren(el('div', '周报读取失败，请刷新重试。历史文件仍保留在 GitHub 仓库中。', 'empty')); }
}
$('week').onchange = () => { state.view = 'papers'; loadIssue($('week').value); };
$('search').oninput = event => { state.query = event.target.value; render(); };
for (const kind of ['view', 'topic', 'method']) document.querySelectorAll(`[data-${kind}]`).forEach(button => button.addEventListener('click', () => {
  state[kind] = button.dataset[kind];
  document.querySelectorAll(`[data-${kind}]`).forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
  render();
}));
$('export').onclick = () => {
  if (storageBroken) {
    try { download('plasma-bookmarks-recovery.json', localStorage.getItem(storageKey) || '[]'); }
    catch { toast('浏览器禁止访问本地存储，无法导出。'); }
  } else download('plasma-bookmarks.json', JSON.stringify({version: 1, exported_at: new Date().toISOString(), items: state.saved}, null, 2));
};
$('import').onclick = () => $('import-file').click();
$('import-file').onchange = async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 10 * 1024 * 1024) throw Error('文件超过 10 MB');
    const data = JSON.parse(await file.text());
    if (data.version !== 1) throw Error('不支持的收藏备份版本');
    const items = validateSaved(data.items);
    const merged = new Map(state.saved.map(item => [item.key, item]));
    for (const item of items) if (!merged.has(item.key)) merged.set(item.key, item);
    const next = validateSaved([...merged.values()]);
    if (persist(next)) { render(); toast(`已合并收藏，共 ${next.length} 条；已有条目保持原样。`); }
  } catch (error) { toast('导入失败：' + error.message + '。已有收藏未被修改。'); }
  event.target.value = '';
};
window.addEventListener('storage', event => {
  if (event.key !== storageKey) return;
  try { state.saved = validateSaved(JSON.parse(event.newValue || '[]')); render(); }
  catch { toast('其他标签页的收藏格式无效，请刷新后检查。'); }
});
async function init() {
  try {
    const response = await fetch('data/index.json', {cache: 'no-store'});
    if (!response.ok) throw Error('Index unavailable');
    const data = await response.json(); state.index = data.issues;
    $('week').replaceChildren(...state.index.map(issue => { const option = el('option', `${issueLabel(issue.window_end)} · ${issue.brief_count} 份简报`); option.value = issue.id; return option; }));
    const params = new URLSearchParams(location.search);
    const requested = params.get('issue'); const paperId = params.get('paper');
    if (state.index.length) {
      await loadIssue(state.index.some(i => i.id === requested) ? requested : state.index[0].id);
      const p = state.issue?.papers.find(p => p.id === paperId);
      if (p) { state.expanded.add(key(p, state.issue.id)); render(); $('paper-' + p.id)?.scrollIntoView({block: 'start'}); }
      if (Date.now() - Date.parse(state.index[0].window_end) > 8 * 86400000) { $('notice').textContent = '最新一期已超过 8 天。更新依赖电脑与 Codex 可用；历史简报可以继续阅读。'; $('notice').hidden = false; }
    } else { $('week').append(el('option', '暂无周报')); render(); }
  } catch { $('list').replaceChildren(el('div', '无法连接周报归档，请刷新重试。仍可从「我的收藏」读取本地简报。', 'empty')); }
  if (storageBroken) { $('notice').textContent = '浏览器收藏读取失败，已停止写入保护原始数据。请到「我的收藏」导出备份。'; $('notice').hidden = false; }
}
$('saved-count').textContent = state.saved.length;
init();
