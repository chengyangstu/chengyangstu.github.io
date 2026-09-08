const chapters = [...document.querySelectorAll('.chapter')];
const toc = document.getElementById('toc');
const search = document.getElementById('chapter-search');
const status = document.getElementById('search-status');
const content = chapters.map(chapter => ({chapter, text: chapter.textContent.toLowerCase()}));
function renderContents() {
  const query = search.value.trim().toLowerCase();
  toc.replaceChildren();
  let part = '', count = 0;
  for (const {chapter, text} of content) {
    if (query && !text.includes(query)) continue;
    if (part !== chapter.dataset.part) {
      part = chapter.dataset.part;
      const label = document.createElement('strong'); label.textContent = part; toc.append(label);
    }
    const a = document.createElement('a'); a.href = '#' + chapter.id;
    a.textContent = chapter.querySelector('h2').textContent;
    toc.append(a); ++count;
  }
  const resources = document.createElement('a'); resources.href = '#resources';
  resources.textContent = document.getElementById('resources').dataset.tocLabel || '资料、论文与视频索引'; toc.append(resources);
  status.textContent = query ? `找到 ${count} 章；点击目录跳至正文。` : '';
  updateCurrent();
}
function updateCurrent() {
  for (const a of toc.querySelectorAll('a')) {
    if (a.hash === location.hash) a.setAttribute('aria-current', 'location');
    else a.removeAttribute('aria-current');
  }
}
search.addEventListener('input', renderContents);
window.addEventListener('hashchange', updateCurrent);
const printButton = document.getElementById('print-book');
printButton.hidden = false; printButton.addEventListener('click', () => window.print());
// Print the complete teaching text, including exercise hints, then restore reading state.
let printDetails = [];
window.addEventListener('beforeprint', () => {
  printDetails = [...document.querySelectorAll('.chapter details:not([open])')];
  printDetails.forEach(d => d.open = true);
});
window.addEventListener('afterprint', () => printDetails.forEach(d => d.open = false));
renderContents();
const contentsPanel = document.querySelector('.book-sidebar details');
if (matchMedia('(max-width:700px)').matches) contentsPanel.open = false;
toc.addEventListener('click', event => {
  if (event.target.closest('a') && matchMedia('(max-width:700px)').matches) contentsPanel.open = false;
});

typesetMath(document.querySelector(".book-main"));
