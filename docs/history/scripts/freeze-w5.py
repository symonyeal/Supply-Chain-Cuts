"""Freeze the acquired W5 primary bytes without changing any existing lock entry."""
import hashlib
import json
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
R = P.parent / 'Chokepoint-Lab'
S = P / 'w5-sources'
manifest = R / 'data/research/manifest.json'
M = json.loads(manifest.read_text())
old = json.loads((R/'SOURCES.lock').read_text())
by = {x['path']: x for x in M['sources']}


def add(source, target, url, licence, transform=None):
    path = R / target
    path.parent.mkdir(parents=True, exist_ok=True)
    if source:
        if path.exists():
            assert path.read_bytes() == source.read_bytes()
        else:
            shutil.copyfile(source, path)
    row = {'path': target, 'url': url, 'license': licence, 'retrieved': '2026-10-16',
           'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    if transform:
        row['transform'] = transform
    if target in by:
        assert by[target]['sha256'] == row['sha256']
    else:
        M['sources'].append(row)
        by[target] = row


add(S/'000040293825.xlsx', 'data/raw/meti/h2daa2024k.xlsx',
    'https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040293825&fileKind=0',
    'CC-BY-4.0 via e-Stat terms section 6(c); third-party exclusions do not apply to METI numerical tables')
for name, url in [('estat-terms.html', 'https://www.e-stat.go.jp/terms-of-use'),
                   ('eurostat-terms.html', 'https://ec.europa.eu/eurostat/web/main/help/copyright-notice'),
                   ('prodcom-methods.html', 'https://ec.europa.eu/eurostat/cache/metadata/en/prom_esms.htm'),
                   ('k-bia.html', 'https://www.k-bia.or.kr/')]:
    add(S/name, f'data/raw/supplement/local/{name}', url, 'Terms/source audit snapshot; raw retained locally')
for name, url in [('cobalt-enduse-2024.pdf', 'https://www.cobaltinstitute.org/wp-content/uploads/2025/06/Cobalt-Market-Report-2024_Factsheet.pdf'),
                  ('nickel-factbook-2024.pdf', 'https://insg.org/wp-content/uploads/2024/09/publist_The-World-Nickel-Factbook-2024.pdf')]:
    add(S/name, f'data/raw/enduse/raw/{name}', url, 'Reuse licence unverified; local only')
api = 'https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-059358/A..{code}./?startPeriod=2024&endPeriod=2024&format=SDMX-CSV'
for code in ['20121955', '20134351', '20134352', '201343Z1', '20134281']:
    add(S/f'prodcom-{code}.csv', f'data/raw/eurostat/unfiltered/prodcom-{code}.csv',
        api.format(code=code), 'Eurostat reuse policy; full country scope retained locally; selected EU rows redistributable')
for name in ['structure', 'flow']:
    url = ('https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/' +
           ('datastructure/ESTAT/DS-059358/latest?references=children' if name=='structure'
            else 'dataflow/ESTAT/DS-059358/latest?references=all'))
    add(S/f'prodcom-{name}.xml', f'data/raw/eurostat/prodcom-{name}.xml', url,
        'Eurostat metadata reuse policy, attribution; Decision 2011/833/EU')
base = 'https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS?reporterCode=156&period=2024&cmdCode={code}&flowCode=X&maxRecords=500'
for code in ['28429040', '28539030', '28539050', '2504101000', '2504109100', '3801100030', '3824999940']:
    name = 'comtrade-lfp.json' if code=='28429040' else f'comtrade-{code}.json'
    add(S/name, f'data/raw/comtrade/{code}.json', base.format(code=code), 'Comtrade reuse licence unverified; local only')
chunks = json.loads((S/'comtrade-chunks.json').read_text())
for block in chunks:
    for c in block['chunks']:
        assert c['status']=='ok' and c['filter_respected']
        add(S/c['file'], 'data/raw/comtrade/'+c['file'], c['url'], 'Comtrade reuse licence unverified; local only')
add(S/'comtrade-chunks.json', 'data/raw/comtrade/chunks.json', base.format(code='28429040'),
    'Acquisition diagnostics, no raw records', 'Disjoint observed-partner batches, Chokepoint-Lab-brief/chunk-comtrade.py')
manifest.write_text(json.dumps(M,indent=2)+'\n',encoding='utf-8')
for x in old['sources']:
    assert hashlib.sha256((R/x['path']).read_bytes()).hexdigest() == x['sha256']
print(len(M['sources']), 'manifest sources; all', len(old['sources']), 'old frozen hashes unchanged')
