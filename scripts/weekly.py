"""Collect arXiv papers, then publish reviewed briefs as immutable weekly issues."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'plasma' / 'data'
CACHE = ROOT / '.cache'
NS = {'a': 'http://www.w3.org/2005/Atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/'}
QUERY = '(cat:physics.plasm-ph OR ti:"magnetic reconnection" OR abs:"magnetic reconnection" OR ti:tokamak OR ti:stellarator OR abs:"fusion plasma" OR abs:"tearing mode" OR abs:microtearing OR abs:"magnetic island" OR abs:sawtooth OR abs:"internal kink")'
FIELDS = ('title_zh', 'takeaway', 'question', 'methods', 'findings', 'limitations', 'reading', 'evidence')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if exclusive:
        with path.open('x', encoding='utf-8') as f:
            f.write(content)
    else:
        # Only scratch data and the rebuildable index use replacement; reports use exclusive creation.
        path.write_text(content, encoding='utf-8')


def request(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'YanchengPlasmaWeekly/1.0 (https://chengyangstu.github.io/plasma/)'})
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def parse_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Time must include timezone')
    return dt.astimezone(timezone.utc)


def scheduled_end(now=None):
    now = now or datetime.now(timezone.utc)
    end = now.replace(hour=1, minute=0, second=0, microsecond=0)
    end -= timedelta(days=(end.weekday() - 2) % 7)
    return end if end <= now else end - timedelta(days=7)


def classify(title, abstract):
    text = (title + ' ' + abstract).lower()
    topics = []
    reconnect = re.search(r'\b(reconnect\w*|\w*tearing|magnetic islands?|sawtooth|sawteeth|internal kink|error.field penetration)\b', text)
    fusion = re.search(r'\b(tokamak|stellarator|gyrokinetic\w*|fusion|divertor|magnetically confined|magnetic confinement|inertial confinement|burning plasma)\b', text)
    if reconnect:
        topics.append('磁场重联')
    if fusion:
        topics.append('聚变等离子体')
    if reconnect and fusion:
        topics.insert(0, '聚变中的重联')
    methods = []
    if re.search(r'\b(theor\w*|analytic\w*|deriv\w*|scaling law\w*)\b', text):
        methods.append('理论')
    if re.search(r'\b(simulat\w*|numerical\w*|computational|particle-in-cell|gyrokinetic|mhd|pic)\b', text):
        methods.append('数值模拟')
    if re.search(r'\b(experiment\w*|measur\w*|observ\w*)\b', text):
        methods.append('实验 / 观测')
    # ponytail: keyword ranking; Codex reviews actual methods from the paper before publishing.
    score = 5 * ('理论' in methods) + 6 * ('数值模拟' in methods) + 2 * ('实验 / 观测' in methods)
    score += 3 * bool(re.search(r'reconnection|tokamak|stellarator|fusion|gyrokinetic', title.lower()))
    score += 40 * bool(reconnect and fusion)
    score += 10 * bool(reconnect and fusion and '数值模拟' in methods and '实验 / 观测' not in methods)
    score += 18 * bool(reconnect and re.search(r'\b(mrx|trex|flared|laboratory|experiment)\b', text))
    score -= 8 * bool(re.search(r'database|operator learning|challenge:', title.lower()))
    return topics, methods or ['待判定'], score


def parse_feed(xml, start, end):
    root = ET.fromstring(xml)
    if root.find('a:entry/a:id', NS) is not None and root.findtext('a:entry/a:id', '', NS).endswith('/errors'):
        raise ValueError('arXiv returned an API error')
    papers = []
    for entry in root.findall('a:entry', NS):
        def text(name):
            return ' '.join(entry.findtext('a:' + name, '', NS).split())
        published = text('published')
        if not start <= parse_time(published) < end:
            continue
        title, abstract = text('title'), text('summary')
        topics, methods, score = classify(title, abstract)
        if not topics:
            continue
        version = text('id').split('/abs/')[-1]
        if not re.fullmatch(r'\d{4}\.\d{4,5}v\d+', version):
            raise ValueError('Unexpected arXiv identifier')
        papers.append(dict(id=re.sub(r'v\d+$', '', version), version=version, title=title,
            authors=[a.findtext('a:name', '', NS) for a in entry.findall('a:author', NS)],
            abstract=abstract, published=published, updated=text('updated'),
            topics=topics, methods=methods, score=score,
            url='https://arxiv.org/abs/' + version, pdf_url='https://arxiv.org/pdf/' + version))
    return papers, int(root.findtext('o:totalResults', '0', NS))


def collect(end):
    start = end - timedelta(days=7)
    query = QUERY + f' AND submittedDate:[{start:%Y%m%d%H%M} TO {end:%Y%m%d%H%M}]'
    papers = {}
    offset = 0
    while True:
        params = urllib.parse.urlencode(dict(search_query=query, start=offset, max_results=200,
            sortBy='submittedDate', sortOrder='descending'))
        page, total = parse_feed(request('https://export.arxiv.org/api/query?' + params), start, end)
        papers.update({p['id']: p for p in page})
        offset += 200
        if offset >= total:
            break
        time.sleep(3)
    return sorted(papers.values(), key=lambda p: (p['score'], p['published']), reverse=True), query


def prepare(end, limit):
    from pypdf import PdfReader
    if end > datetime.now(timezone.utc):
        raise ValueError('Cannot prepare a future reporting window')
    papers, query = collect(end)
    selected = papers[:limit]  # Fusion reconnection receives the highest score; never pad with older papers.
    CACHE.mkdir(exist_ok=True)
    for paper in selected:
        print('Reading', paper['version'], paper['title'], flush=True)
        try:
            pdf_path = CACHE / (paper['version'] + '.pdf')
            if not pdf_path.exists():
                time.sleep(3)
            pdf = pdf_path.read_bytes() if pdf_path.exists() else request(paper['pdf_url'])
            reader = PdfReader(io.BytesIO(pdf))
            pages = [f'\n--- PDF page {n + 1} ---\n' + (p.extract_text() or '') for n, p in enumerate(reader.pages)]
            content = '\n'.join(pages)
            if len(content.strip()) < 1500:
                raise ValueError('Insufficient extractable text')
            path = CACHE / (paper['version'] + '.txt')
            path.write_text(content, encoding='utf-8')
            (CACHE / (paper['version'] + '.pdf')).write_bytes(pdf)
            paper.update(source_basis='PDF 全文文本', text_file=str(path), pages=len(pages),
                source_sha256=hashlib.sha256(pdf).hexdigest())
        except Exception as error:
            paper.update(source_basis='仅摘要', source_error=type(error).__name__)
            print('Full text unavailable:', paper['id'], type(error).__name__, flush=True)
    packet = dict(window_start=(end - timedelta(days=7)).isoformat(), window_end=end.isoformat(),
        query=query, collected_at=datetime.now(timezone.utc).isoformat(), papers=papers,
        selected_ids=[p['id'] for p in selected])
    save_json(CACHE / 'packet.json', packet)
    print(f'Prepared {len(papers)} relevant papers; {len(selected)} selected. Read .cache/packet.json and text files, then write .cache/briefs.json.', flush=True)


def validate_brief(brief):
    if not isinstance(brief, dict) or any(not isinstance(brief.get(k), str) or not brief[k].strip() for k in FIELDS):
        raise ValueError('Brief requires nonempty fields: ' + ', '.join(FIELDS))
    if not isinstance(brief.get('methods'), str):
        raise ValueError('methods must describe actual work')
    if not isinstance(brief.get('method_tags'), list) or not brief['method_tags'] or any(t not in ('理论', '数值模拟', '实验 / 观测') for t in brief['method_tags']):
        raise ValueError('Invalid method_tags')
    if brief.get('reading_scope') not in ('PDF 正文选读', 'PDF 全文阅读', '仅摘要'):
        raise ValueError('Actual reading_scope is required')
    if brief.get('editorial_version') == 2:
        if type(brief.get('relevance_tier')) is not int or not 0 <= brief['relevance_tier'] <= 5 or not brief.get('relevance_reason', '').strip():
            raise ValueError('Reviewed relevance tier 0..5 and explanation required')
        if brief['reading_scope'] != '仅摘要':
            if any(len(re.split(r'\n\s*\n', brief[k])) < 2 for k in ('methods', 'findings')):
                raise ValueError('Explain methods and findings in readable paragraphs')
            if not re.search(r'第\s*\d+.*?页', brief['evidence']):
                raise ValueError('PDF page locations required')
        for field in FIELDS:
            value = brief[field]
            if value.count(r'\(') != value.count(r'\)') or value.count('**') % 2:
                raise ValueError('Unclosed math or emphasis: ' + field)
            if re.search(r'<(?:script|iframe|img)\b', value, re.I):
                raise ValueError('Briefs use plain text and TeX, never embedded HTML')


def rebuild_index(data=DATA):
    issues = []
    for path in (data / 'issues').glob('*.json'):
        issue = read_json(path)
        issues.append({k: issue[k] for k in ('id', 'window_start', 'window_end', 'created_at', 'overview')}
            | dict(paper_count=len(issue['papers']), brief_count=sum(bool(p.get('brief')) for p in issue['papers']))
            | {k: issue[k] for k in ('revision_of', 'edition_note', 'aliases') if k in issue})
    issues.sort(key=lambda i: (i['window_end'], i['created_at']), reverse=True)
    save_json(data / 'index.json', dict(issues=issues))


def publish(packet_path, briefs_path, data=DATA, revision_of=None):
    packet, result = read_json(packet_path), read_json(briefs_path)
    briefs = result['briefs']
    if not isinstance(result.get('overview'), str) or not result['overview'].strip():
        raise ValueError('Overview is required')
    if set(briefs) != set(packet['selected_ids']):
        raise ValueError('Every selected paper must have a brief; no unknown IDs')
    for brief in briefs.values():
        validate_brief(brief)
    issue_id = parse_time(packet['window_end']).strftime('%Y-%m-%d')
    created_at = datetime.now(timezone.utc)
    if revision_of:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:-r(?:[2-9]|[1-9]\d+)|T\d{6}Z)?', revision_of):
            raise ValueError('Invalid revision source ID')
        original = read_json(data / 'issues' / (revision_of + '.json'))
        if any(parse_time(original[k]) != parse_time(packet[k]) for k in ('window_start', 'window_end')):
            raise ValueError('Editorial supplement must keep the original search window')
        if not result.get('edition_note', '').strip():
            raise ValueError('Editorial supplement must be explicitly labeled')
        revision = 2
        while (data / 'issues' / f'{issue_id}-r{revision}.json').exists():
            revision += 1
        issue_id += f'-r{revision}'
    start, end = parse_time(packet['window_start']), parse_time(packet['window_end'])
    if end - start != timedelta(days=7):
        raise ValueError('Window must be exactly seven days')
    papers = []
    for p in packet['papers']:
        if not start <= parse_time(p['published']) < end:
            raise ValueError('Paper outside publication window')
        paper = {k: v for k, v in p.items() if k not in ('text_file', 'score')}
        if p['id'] in briefs:
            paper['brief'] = briefs[p['id']]
            paper['methods'] = paper['brief']['method_tags']
            paper['source_basis'] = paper['brief']['reading_scope']
            if paper['source_basis'] != '仅摘要' and not p.get('source_sha256'):
                raise ValueError('PDF-based brief requires a fetched PDF')
        papers.append(paper)
    issue = dict(id=issue_id, window_start=packet['window_start'], window_end=packet['window_end'],
        created_at=created_at.isoformat(), overview=result['overview'],
        query=packet['query'], reading_note='Codex 辅助阅读；PDF 文本提取不等于逐图审阅；请以原文为准。', papers=papers,
        overall_report=[dict(id=p['id'], title=p['brief']['title_zh'], summary=p['brief']['takeaway']) for p in papers if p.get('brief')])
    if revision_of:
        issue.update(revision_of=revision_of, edition_note=result['edition_note'])
    path = data / 'issues' / (issue_id + '.json')
    save_json(path, issue, exclusive=True)  # Existing reports can never be replaced, even on retries.
    rebuild_index(data)
    print('Archived:', path)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'publish', 'index'])
    parser.add_argument('--end', help='Exclusive UTC cutoff, default most recent Wednesday 09:00 Beijing')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--briefs', type=Path, default=CACHE / 'briefs.json')
    parser.add_argument('--revision-of', help='Archive a labeled supplement without changing the original window or file')
    args = parser.parse_args()
    if args.command == 'prepare':
        if not 1 <= args.limit <= 30:
            parser.error('--limit must be 1..30')
        prepare(parse_time(args.end) if args.end else scheduled_end(), args.limit)
    elif args.command == 'publish':
        publish(CACHE / 'packet.json', args.briefs, revision_of=args.revision_of)
    else:
        rebuild_index()
