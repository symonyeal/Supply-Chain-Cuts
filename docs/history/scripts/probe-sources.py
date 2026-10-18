"""Cache primary W5 endpoint responses outside the frozen model inputs."""
import hashlib
import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

root=Path(__file__).resolve().parent/'w5-sources'
root.mkdir(exist_ok=True)
urls={
 'meti-index.html':'https://www.meti.go.jp/statistics/tyo/seidou/index.html',
 'estat-files.html':'https://www.e-stat.go.jp/stat-search/files?layout=datalist&toukei=00550200&tstat=000001022932&cycle=7&year=20240',
 'eurostat-structure.xml':'https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/dataflow/ESTAT/DS-059358/1.0?references=all',
 'comtrade-lfp.json':'https://comtradeapi.un.org/public/v1/previewTariffline/C/A/HS?reporterCode=156&period=2024&cmdCode=28429040&flowCode=X&maxRecords=500',
 'k-bia.html':'https://www.k-bia.or.kr/'
}
def get(item):
 name,url=item
 p=root/name
 try:
  if not p.exists():
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Chokepoint-Lab/0.3'}),timeout=45) as r:p.write_bytes(r.read())
  b=p.read_bytes()
  result={'name':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  if name.endswith('.json'):
   x=json.loads(b);result['keys']=list(x);result['count']=x.get('count');result['first']=x.get('data',[])[:1]
  elif name.endswith('.html'):
   s=b.decode('utf-8',errors='replace');result['links']=[m[:300] for m in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',s,re.S) if any(v in str(m) for v in ('2024','年報','電池','통계','통계','battery'))][:20]
  return result
 except urllib.error.URLError as e:return {'name':name,'url':url,'error':str(e)}
with ThreadPoolExecutor(3) as pool:
 results=list(pool.map(get,urls.items()))
(root/'probe.json').write_text(json.dumps(results,indent=1,ensure_ascii=False)+'\n',encoding='utf-8')
for x in results:print(json.dumps(x,ensure_ascii=True),flush=True)
