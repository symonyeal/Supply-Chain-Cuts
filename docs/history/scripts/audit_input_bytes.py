"""Compare committed raw-input bytes with frozen hashes, before fixing Git attributes."""
import hashlib
import json
import subprocess
from pathlib import Path

r = Path('C:/Users/Yeal/Documents/My Projects/Chokepoint-Lab')
out = {'mismatches': [], 'not_yet_committed': [], 'verified': []}
for x in json.loads((r/'SOURCES.lock').read_text())['sources']:
    if not x['committed']:
        continue
    p = subprocess.run(['git', '-C', str(r), 'show', 'HEAD:'+x['path']], capture_output=True)
    if p.returncode:
        out['not_yet_committed'].append(x['path'])
    elif hashlib.sha256(p.stdout).hexdigest() != x['sha256']:
        raw = (r/x['path']).read_bytes()
        out['mismatches'].append({'path': x['path'], 'newline_only':
                                 raw.replace(b'\r\n', b'\n') == p.stdout.replace(b'\r\n', b'\n')})
    else:
        out['verified'].append(x['path'])
dest = r/'results/input-bytes-1e7ce2f'
dest.mkdir(exist_ok=True)
(dest/'checks.json').write_text(json.dumps(out, indent=1)+'\n')
print(json.dumps(out, indent=1))
assert not out['mismatches'], 'Committed raw bytes do not match frozen hashes'
