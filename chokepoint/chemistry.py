"""Separate cathode commodities and shared-capacity recipes; approved W3 design."""
from pathlib import Path

from chokepoint.bom import bill
from chokepoint.net import blocks
from chokepoint.recourse import matrices


def model(N, shares=(0, 1), T=24, h=0.0, sigma=0.0, L=6.0, durations=(3, 6, 12),
          aggregate=True, root=Path('.')):
    """Build chemistry recourse with fixed reference capacities and 24-month share bounds.

    INPUT N: 50% reference physical network; shares: delivered NCM lower/upper share.
    OUTPUT the same primal/dual matrix contract used by every cut enumerator.
    """
    if N['ncm'] != 0.5 or 'cell' not in N['finals']:
        raise ValueError('Chemistry choice requires the 50% reference cell network')
    R = N['requirement'] | {'cam_lfp': N['requirement']['cam'],
                            'cam_ncm': N['requirement']['cam']}
    recipes = {'cam': {}, 'cell': {}}
    stock = {}
    B = [bill(s, root) for s in (0, 1)]
    blend_cam = sum(b['cam_kg_kwh'] for b in B)/2
    for name, b in zip(('lfp', 'ncm'), B, strict=True):
        q = 'cam_' + name
        cam = {'li_carbonate': b['lce_kg_kwh']/b['cam_kg_kwh']}
        if name == 'ncm':
            cam['pcam'] = b['pcam_kg_kwh']/b['cam_kg_kwh']
        cell = {q: b['cam_kg_kwh'], 'aam': b['kg_kwh']['Graphite'],
                'refined_cu': b['kg_kwh']['Cu'], 'aluminium': b['kg_kwh']['Al']}
        for layer, output, inputs in (('cam', q, cam), ('cell', 'cell', cell)):
            coeff = {p: x*R[output]/R[p] for p, x in inputs.items()}
            recipes[layer][name] = (output, coeff)
            weight = b['cam_kg_kwh']/(2*blend_cam) if layer == 'cam' else 0.5
            for p, x in coeff.items():
                stock[p, layer] = stock.get((p, layer), 0) + weight*x
    a = {(p, q): x*R[q]/R[p] for p, q, x in N['a']}
    stock.update({(p, q): x for (p, q), x in a.items() if q not in recipes})
    M = matrices([(x['country'], x['product']) for x in N['nodes']],
                 [x['capacity'] for x in N['nodes']], a,
                 {p: [1/12]*T for p in N['finals']}, h, sigma, L, aggregate=aggregate,
                 ends=blocks(T, sigma, L, durations), recipes=recipes, stock=stock,
                 shares={'cell': shares})
    M['chemistry'] = {'NCM_share': list(shares), 'share_horizon_months': T,
                      'capacity_reference_NCM': 0.5, 'basis': 'recipe_flexibility_scenario'}
    return M
