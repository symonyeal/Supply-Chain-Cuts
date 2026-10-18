"""Cache remaining public primary sources; preserve errors and retry metadata."""
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

P = Path(__file__).resolve().parent / 'w5-sources'
U = {
    'cobalt-enduse-2024.pdf': 'https://www.cobaltinstitute.org/wp-content/uploads/2025/06/Cobalt-Market-Report-2024_Factsheet.pdf',
    'nickel-factbook-2024.pdf': 'https://insg.org/wp-content/uploads/2024/09/publist_The-World-Nickel-Factbook-2024.pdf',
    'eurostat-terms.html': 'https://ec.europa.eu/eurostat/web/main/help/copyright-notice',
    'prodcom-methods.html': 'https://ec.europa.eu/eurostat/cache/metadata/en/prom_esms.htm',
}
api = 'https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-059358/A..{code}./?startPeriod=2024&endPeriod=2024&format=SDMX-CSV'
for code in ['201343Z1', '20134350']:
    U[f'prodcom-{code}.csv'] = api.format(code=code)
for code in ['2504101000', '2504109100', '3801100030', '3824999940']:
    U[f'comtrade-{code}.json'] = ('https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS?'
                                f'reporterCode=156&period=2024&cmdCode={code}&flowCode=X&maxRecords=500')
out = []
for name, url in U.items():
    path = P / name
    try:
        if not path.exists():
            with urlopen(Request(url, headers={'User-Agent': 'Chokepoint-Lab public-source audit'}), timeout=90) as r:
                path.write_bytes(r.read())
        out.append({'file': name, 'url': url, 'status': 'ok', 'bytes': path.stat().st_size})
    except HTTPError as e:
        out.append({'file': name, 'url': url, 'status': e.code, 'retry_after': e.headers.get('Retry-After')})
    print(out[-1], flush=True)
    time.sleep(6)
(P / 'fetch-extra.json').write_text(json.dumps(out, indent=1)+'\n')
