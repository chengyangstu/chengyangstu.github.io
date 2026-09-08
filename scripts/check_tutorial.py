"""Static publication check: chapter targets, local downloads, references and source syntax."""
import ast
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parents[1]
page = root / 'cuda/index.html'


class Book(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.chapters = set(), [], []
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids, 'Duplicate ID: ' + a['id']
            self.ids.add(a['id'])
        if 'href' in a:
            self.links.append(a['href'])
        if tag == 'article' and 'chapter' in a.get('class', '').split():
            self.chapters.append(a['id'])

    def handle_data(self, data):
        self.text.append(data)


book = Book()
html = page.read_text(encoding='utf-8')
book.feed(html)
assert book.chapters == [f'ch{i:02d}' for i in range(1, 25)], 'Missing/reordered chapters'
assert 'CONTINUE -->' not in html, 'Unfinished authoring placeholder'
for href in book.links:
    url = urlsplit(href)
    if url.scheme:
        assert url.scheme in ('http', 'https'), 'Unexpected link protocol'
    elif not url.path:
        assert unquote(url.fragment) in book.ids, 'Missing chapter/reference: ' + href
    else:
        target = (page.parent / unquote(url.path)).resolve()
        assert target.is_relative_to(root) and target.exists(), 'Missing local asset: ' + href
for source in (root / 'cuda/labs').glob('*.py'):
    ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
han = len(re.findall(r'[\u4e00-\u9fff]', ''.join(book.text)))
print(f'PASS: {len(book.chapters)} chapters, {len(book.links)} links, {han} Chinese characters; local references and Python syntax valid.')
