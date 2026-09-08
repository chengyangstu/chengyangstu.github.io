"""Run with python scripts/check.py; no test dependencies required."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from weekly import DATA, FIELDS, classify, parse_feed, publish, rebuild_index, save_json, scheduled_end, validate_brief

end = datetime(2026, 9, 9, 1, tzinfo=timezone.utc)
assert scheduled_end(end) == end
assert scheduled_end(end - timedelta(seconds=1)) == end - timedelta(days=7)
assert classify('Dye removal by plasma reactor', '')[0] == []
assert classify('Magnetic reconnection', 'kinetic simulations')[0] == ['磁场重联']
assert '数值模拟' in classify('Tokamak turbulence', 'gyrokinetic simulations')[1]
assert '聚变中的重联' in classify('Microtearing modes in a tokamak', 'kinetic simulations')[0]
assert classify('Microtearing modes in a tokamak', 'kinetic simulations')[2] > classify('Solar magnetic reconnection', 'kinetic simulations')[2]
xml = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>3</o:totalResults>'''
for published in (end - timedelta(days=7), end, end - timedelta(days=8)):
    xml += f'<entry><id>http://arxiv.org/abs/2609.00001v1</id><title>Magnetic reconnection</title><summary>Numerical simulations</summary><published>{published.isoformat()}</published><updated>{end.isoformat()}</updated></entry>'
papers, total = parse_feed((xml + '</feed>').encode(), end - timedelta(days=7), end)
assert total == 3 and len(papers) == 1  # Exact first-submission date, not last revision date.
brief = {k: 'A real check value' for k in FIELDS} | {'method_tags': ['理论'], 'reading_scope': '仅摘要'}
with tempfile.TemporaryDirectory(prefix='plasma-archive-check-') as tmp:
    root = Path(tmp).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith('plasma-archive-check-')
    packet = dict(window_start=(end - timedelta(days=7)).isoformat(), window_end=end.isoformat(),
        query='test', papers=papers, selected_ids=[papers[0]['id']])
    save_json(root / 'packet.json', packet)
    save_json(root / 'briefs.json', dict(overview='Test', briefs={papers[0]['id']: brief}))
    first = publish(root / 'packet.json', root / 'briefs.json', root / 'data')
    assert first.stem == '2026-09-09'
    original = first.read_bytes()
    try:
        publish(root / 'packet.json', root / 'briefs.json', root / 'data')
        raise AssertionError('Existing report was overwritten')
    except FileExistsError:
        pass
    save_json(root / 'briefs.json', dict(overview='Test', edition_note='Expanded supplement', briefs={papers[0]['id']: brief}))
    supplement = publish(root / 'packet.json', root / 'briefs.json', root / 'data', revision_of=first.stem)
    revised = json.loads(supplement.read_text(encoding='utf-8'))
    assert supplement.stem == '2026-09-09-r2'
    assert revised['revision_of'] == first.stem and revised['window_end'] == packet['window_end']
    assert first.read_bytes() == original
    packet['window_start'] = end.isoformat()
    packet['window_end'] = (end + timedelta(days=7)).isoformat()
    packet['papers'][0]['published'] = (end + timedelta(days=1)).isoformat()
    save_json(root / 'packet.json', packet)
    publish(root / 'packet.json', root / 'briefs.json', root / 'data')
    rebuild_index(root / 'data')
    assert first.read_bytes() == original
    assert len(json.loads((root / 'data/index.json').read_text(encoding='utf-8'))['issues']) == 3
if DATA.exists():
    index = json.loads((DATA / 'index.json').read_text(encoding='utf-8'))['issues']
    assert {i['id'] for i in index} == {p.stem for p in (DATA / 'issues').glob('*.json')}
    for item in index:
        issue = json.loads((DATA / 'issues' / (item['id'] + '.json')).read_text(encoding='utf-8'))
        assert len({p['id'] for p in issue['papers']}) == len(issue['papers'])
        assert item['brief_count'] == sum(bool(p.get('brief')) for p in issue['papers'])
        for p in issue['papers']:
            if p.get('brief'):
                validate_brief(p['brief'])
        if 'overall_report' in issue:
            assert {r['id'] for r in issue['overall_report']} == {p['id'] for p in issue['papers'] if p.get('brief')}
print('PASS: date boundaries, relevance, immutable reports, complete history index.')
