"""Exercise the overview and the explorer: scenarios, filters, downloads, links, themes."""
# R: repository root; o: evidence directory; u: local or deployed site URL; x: explorer URL.
# W: viewport widths; p: browser page; c: one saved configuration.
from __future__ import annotations

import argparse
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import Error, sync_playwright

R = Path(__file__).resolve().parents[1]

SWEEP = """() => {
  const D = window.DATA, reports = [], el = id => document.getElementById(id);
  const select = (id,value) => { if (el(id).value !== value) {
    el(id).value = value; el(id).dispatchEvent(new Event('change',{bubbles:true}));
  }};
  for (const [sector,chemistry,B] of [['liion','fixed',D],['liion','choice',D.choice],
       ['pv','choice',D.pv],['joint','fixed',D.joint],['joint','choice',D.joint_choice]]) {
    for (const [key,c] of Object.entries(B.configs)) {
      select('sector',sector); select('chemistry',chemistry);
      const x = Object.fromEntries(key.split('_').map(v => [v[0],v.slice(1)]));
      for (const [id,value] of [['alpha',x.a],['DJ',x.D],['h',x.h],['sigma',x.s],['L',x.L]])
        select(id,value);
      const m = [...document.querySelectorAll('.metric b')].map(x => x.textContent);
      const expected = [String(c.cuts.length),String(c.cuts.filter(s => s.length===1).length),
        (100*c.L).toFixed(1)+'%'];
      if (expected.some((v,i) => v!==m[i]))
        throw Error(JSON.stringify({sector,chemistry,key,m,expected}));
      if (document.querySelectorAll('.cut-row').length !== c.cuts.length)
        throw Error('Cut-list count differs for '+key);
      reports.push({sector,chemistry,key,cuts:c.cuts.length,L:c.L});
    }
  }
  return reports;
}"""

PROBE = """() => {
  const d = document.documentElement;
  const missing = [...document.querySelectorAll('input,select')].filter(e =>
    !e.labels.length && !e.getAttribute('aria-label')).map(e => e.id);
  const tiny = [...document.querySelectorAll('p,label,summary,button,th,td')].filter(e =>
    e.getClientRects().length && parseFloat(getComputedStyle(e).fontSize)<12).length;
  const cs = getComputedStyle(d), rgb = s => s.match(/\\d+(?:\\.\\d+)?/g).slice(0,3).map(Number);
  const resolve = token => {const e=document.createElement('span');
    e.style.color='var('+token+')';document.body.append(e);const c=rgb(getComputedStyle(e).color);
    e.remove();return c;};
  const lum = c => c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;})
    .reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  const contrast = (a,b) => {const x=lum(resolve(a)),y=lum(resolve(b));
    return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
  const chain=document.getElementById('chain'), bounds=chain?.getBoundingClientRect();
  const chainOverflow=!!chain&&[...chain.querySelectorAll('.stage-caption')].some(e=>
    e.getBoundingClientRect().bottom>bounds.bottom+1);
  return {overflow:d.scrollWidth>d.clientWidth+1,missing,tiny,
    chainOverflow,
    text:contrast('--text','--bg'),muted:contrast('--muted','--bg'),
    accent:contrast('--accent','--bg'),button:contrast('--accent-ink','--accent'),
    mark:contrast('--context','--soft'),bg:cs.getPropertyValue('--bg').trim()};
}"""


OVERVIEW = """() => {
  const R = 'a0.25_h0_s0_L6_D12', n = B => B.configs[R].cuts.filter(c => c.length === 1).length;
  const count = s => document.querySelectorAll(s).length;
  return {fact: document.querySelector('.fact b').textContent,
    expected: String(n(DATA.choice) + n(DATA.pv)),
    weak: count('#chain-liion .row.weak, #chain-pv .row.weak'),
    duration: count('#duration .dot.long'), policies: count('#policies .policy-row:not(.head)'),
    minerals: count('#mine-refine .dot.long')};
}"""


def probe(p, report: dict, o: Path, name: str, width: int):
    """Check layout, labels, type size and contrast in both themes; screenshot each theme."""
    for theme in ('light', 'dark'):
        p.evaluate('(theme)=>document.documentElement.dataset.theme=theme', theme)
        x = p.evaluate(PROBE)
        assert not any(x[k] for k in ('overflow', 'missing', 'tiny', 'chainOverflow')), (name, x)
        for key in ('text', 'muted', 'accent', 'button'):
            assert x[key] >= 4.5, (name, key, x)
        assert x['mark'] >= 3, (name, x)
        p.screenshot(path=str(o / f'{name}-{width}-{theme}.png'), full_page=name == 'overview')
        report['views'].append({'page': name, 'width': width, 'theme': theme, **x})
    before = p.evaluate('getComputedStyle(document.body).backgroundColor')
    p.locator('#theme').click()
    assert p.evaluate('getComputedStyle(document.body).backgroundColor') != before


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def themes(browser, u):
    """Exercise shared preference behavior across pages, reloads and denied storage."""
    rows = []
    for system in ('light', 'dark'):
        for blocked in (False, True):
            context = browser.new_context(color_scheme=system)
            if blocked:
                context.add_init_script("""Object.defineProperty(window, 'localStorage', {
                    get() { throw new DOMException('Storage disabled', 'SecurityError'); }
                });""")
            p = context.new_page()
            expected = system
            for name in ('', 'explore.html'):
                p.goto(u + name)
                button = p.locator('#theme')
                label = lambda theme: 'Light view' if theme == 'dark' else 'Dark view'
                assert button.inner_text() == label(expected)
                changed = 'light' if expected == 'dark' else 'dark'
                button.click()
                assert button.inner_text() == label(changed)
                assert p.evaluate('document.documentElement.dataset.theme') == changed
                expected = system if blocked else changed
                p.reload()
                assert button.inner_text() == label(expected)
                rows.append({'page': name or 'index.html', 'system': system,
                             'storage_blocked': blocked, 'after_reload': expected})
            context.close()
    return rows


def check(u: str, o: Path, preview: Path | None = None) -> dict:
    report = {'url': u, 'views': [], 'errors': []}
    with sync_playwright() as pw:
        browser = None
        launch_errors = []
        for channel in (None, 'chrome', 'msedge'):
            try:
                browser = pw.chromium.launch(channel=channel) if channel else pw.chromium.launch()
                break
            except Error as error:
                launch_errors.append(str(error).splitlines()[0])
        if browser is None:
            raise RuntimeError(f'No Chromium available: {launch_errors}')
        report['themes'] = themes(browser, u)
        p = browser.new_page(viewport={'width': 1440, 'height': 1000})
        p.on('pageerror', lambda error: report['errors'].append(str(error)))
        p.goto(u)
        p.wait_for_selector('#duration .row')
        report['overview'] = p.evaluate(OVERVIEW)
        x = report['overview']
        assert x == {'fact': x['expected'], 'expected': '9', 'weak': 9, 'duration': 9,
                     'policies': 5, 'minerals': 4}, x
        for width in (1440, 768, 390):
            p.set_viewport_size({'width': width, 'height': 1000 if width > 600 else 844})
            p.goto(u)
            probe(p, report, o, 'overview', width)
        p.set_viewport_size({'width': 1440, 'height': 1000})
        p.locator('nav a[href="explore.html"]').click()
        p.wait_for_selector('.cut-row')
        x = p.url.split('?')[0]
        assert x.endswith('explore.html'), x
        report['configurations'] = p.evaluate(SWEEP)
        assert len(report['configurations']) == 417
        p.locator('#reset').click()
        assert p.locator('.metric b').nth(0).inner_text() == '7'
        p.locator('#cut-query').fill('graphite')
        assert p.locator('.cut-row').count() == 1
        with p.expect_download() as download:
            p.locator('#download-cuts').click()
        target = o / 'filtered-cuts.csv'
        download.value.save_as(target)
        rows = list(csv.DictReader(target.open(encoding='utf-8-sig')))
        assert len(rows) == 1 and 'Graphite' in rows[0]['losses']
        assert float(rows[0]['shortfall_fraction']) > .25
        p.locator('#cut-query').fill('no such material')
        assert p.locator('.empty').first.is_visible()
        assert p.locator('#download-cuts').is_disabled()
        p.locator('#reset').click()
        assert p.locator('#cut-query').input_value() == ''
        p.locator('#pin').click()
        p.locator('#advanced').locator('summary').click()
        p.locator('#h').select_option('3')
        assert 'Pinned' in p.locator('#comparison-note').inner_text()
        linked = p.url
        p.reload()
        assert p.locator('#h').input_value() == '3'
        assert 'Pinned' in p.locator('#comparison-note').inner_text()
        report['link_roundtrip'] = linked
        p.locator('#sector').select_option('joint')
        assert p.locator('#h').is_disabled() and p.locator('#sigma').is_disabled()
        assert p.locator('#h').input_value() == '0'
        assert p.locator('#alpha option[value="0.5"]').is_disabled()
        p.locator('#reset').click()
        p.locator('.stage[data-product="graphite"]').click()
        assert p.locator('#node-product').input_value() == 'graphite'
        assert p.locator('#node-table tbody tr').count() > 0
        with p.expect_download() as download:
            p.locator('#download-nodes').click()
        target = o / 'filtered-nodes.csv'
        download.value.save_as(target)
        rows = list(csv.DictReader(target.open(encoding='utf-8-sig')))
        assert rows and all(row['product'] == 'graphite' for row in rows)
        assert '31.7%' in p.locator('#production-title').inner_text()
        assert '290,000' in p.locator('#production-scope').inner_text()
        assert 'withheld' in p.locator('#production-warning').inner_text()
        p.locator('#all-refining').check()
        assert p.locator('#refining-chart .bar-row').count() == 16
        p.locator('#year').select_option('2024')
        assert '2024' in p.locator('#production-scope').inner_text()
        for width in (1440, 768, 390):
            p.set_viewport_size({'width': width, 'height': 1000 if width > 600 else 844})
            p.goto(x)
            for selector in ('#result', '#chain', '#minerals', '#compare'):
                p.locator(selector).screenshot(path=str(o / f'{selector[1:]}-{width}.png'))
            probe(p, report, o, 'explorer', width)
        p.goto(x + '?sector=joint&alpha=0.5&h=3&sigma=0.5&chemistry=bad')
        assert p.locator('#alpha').input_value() == '0.25'
        assert p.locator('#h').input_value() == '0'
        assert p.locator('#chemistry').input_value() == 'choice'
        assert not report['errors'], report['errors']
        if preview:
            p.set_viewport_size({'width': 1200, 'height': 630})
            p.goto(u)
            p.evaluate("document.documentElement.dataset.theme='light'")
            preview.parent.mkdir(parents=True, exist_ok=True)
            p.screenshot(path=str(preview))
        browser.close()
    report['passed'] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--url', help='Deployed explorer URL; otherwise serve local site/')
    parser.add_argument('--preview', type=Path, help='Optional 1200 × 630 publication screenshot')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    server = None
    if args.url:
        u = args.url
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(R)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        u = f'http://127.0.0.1:{server.server_port}/site/'
    try:
        report = check(u, args.out, args.preview)
        (args.out / 'browser.json').write_text(json.dumps(report, indent=2), encoding='utf8')
        print(json.dumps({'passed': report['passed'], 'configurations': len(
            report['configurations']), 'views': len(report['views']), 'errors': report['errors']}))
    finally:
        if server:
            server.shutdown()


if __name__ == '__main__':
    main()
