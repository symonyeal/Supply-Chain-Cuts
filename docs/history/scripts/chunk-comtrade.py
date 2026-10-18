"""Cross-check preview rows with disjoint batches of observed partner codes."""
import collections
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

P = Path(__file__).resolve().parent / 'w5-sources'
out = []
for code, name in [('28429040', 'comtrade-lfp.json'), ('28539030', 'comtrade-28539030.json'),
                   ('28539050', 'comtrade-28539050.json')]:
    rows = json.loads((P/name).read_text())['data']
    partners = sorted({x['partnerCode'] for x in rows})
    combined, chunks = [], []
    for i in range(0, len(partners), 10):
        group = partners[i:i+10]
        url = ('https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS?reporterCode=156'
               f'&period=2024&cmdCode={code}&flowCode=X&maxRecords=500&partnerCode='
               + ','.join(map(str, group)))
        path = P/f'comtrade-{code}-partners-{i//10}.json'
        try:
            if not path.exists():
                path.write_bytes(urlopen(url, timeout=90).read())
            x = json.loads(path.read_text())
            valid = all(r['partnerCode'] in group and r['cmdCode']==code for r in x['data'])
            chunks.append({'file': path.name, 'url': url, 'status': 'ok',
                           'partners': group, 'rows': x['count'], 'filter_respected': valid})
            if valid:
                combined += x['data']
        except HTTPError as e:
            chunks.append({'file': path.name, 'url': url, 'status': e.code,
                           'retry_after': e.headers.get('Retry-After')})
        print(chunks[-1], flush=True)
        time.sleep(6)
    canonical = lambda z: collections.Counter(json.dumps(x,sort_keys=True) for x in z)
    out.append({'code': code, 'chunks': chunks, 'unfiltered_rows': len(rows),
                'known_partner_chunks_match': canonical(rows)==canonical(combined),
                'completeness': 'unverified: only partners observed in the preview are checked'})
(P/'comtrade-chunks.json').write_text(json.dumps(out,indent=1)+'\n')
