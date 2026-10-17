"""Independent enumeration of minimal failing states; deliberately imports no interdiction code.

Both enumerators call φ only. `enumerate_brute` visits every state of support ≤ k, skipping
supersets of found cuts and supports whose top state survives (Prop. 1). `enumerate_lattice`
also uses capacity dominance (docs/MODEL.md, Lemma B): moving a disruption to a no-smaller
node of the same layer, or lengthening it, does not lower φ.
"""
from itertools import combinations, combinations_with_replacement, product

import numpy as np

from chokepoint.recourse import solve


def _minimal(cuts):
    return [D for D in cuts if not any(
        S != D and all(x <= y for x, y in zip(S, D, strict=True)) for S in cuts)]


def enumerate_brute(M, durations, alpha=0.25, k=3, eps=1e-7, eligible=None):
    """Enumerate all duration-minimal failing states of support <= k by primal solves."""
    n, theta, top = len(M["V"]), alpha*M["total"], max(durations)
    eligible = list(range(n) if eligible is None else eligible)
    cuts = []

    def fails(D):
        R = solve(M, D, dual=False)
        if R["status"] != "optimal":
            raise RuntimeError(R)
        return R["phi"] > theta + eps

    for l in range(min(k, n) + 1):
        for I in combinations(eligible, l):
            D = [0]*n
            for v in I:
                D[v] = top
            if not any(all(x <= y for x, y in zip(S, D, strict=True)) for S in cuts) \
                    and not fails(D):
                continue                                  # every state on I is ≤ D (Prop. 1)
            for q in product(sorted(durations), repeat=l):
                D = [0]*n
                for v, j in zip(I, q, strict=True):
                    D[v] = int(j)
                if any(all(x <= y for x, y in zip(S, D, strict=True)) for S in cuts):
                    continue
                if fails(D):
                    cuts.append(D)
    return _minimal(cuts)


def enumerate_lattice(M, durations, alpha=0.25, k=3, eps=1e-7, eligible=None):
    """Enumerate the same set by branch and bound over layer patterns.

    For a pattern λ (layers with multiplicities) the nodes of each layer are taken in
    decreasing capacity. A partial state is completed optimistically: every open slot gets
    the largest admissible node at D_J. If that completion survives, so does every state in
    the subtree (Lemma B and Prop. 1). OUTPUT minimal failing states and the LP count.
    """
    n, theta = len(M["V"]), alpha*M["total"]
    durations = sorted(durations)
    eligible = list(range(n) if eligible is None else eligible)
    layers = {}
    for v in sorted(eligible, key=lambda v: (M["V"][v][1], -M["u"][v], v)):
        layers.setdefault(M["V"][v][1], []).append(v)
    cache, cuts, found = {}, [], []

    def dominates(D):
        return any(all(x <= y for x, y in zip(S, D, strict=True)) for S in cuts + found)

    def fails(D):
        key = tuple(D)
        if dominates(key):
            return True
        if key not in cache:
            R = solve(M, np.array(key, float), dual=False)
            if R["status"] != "optimal":
                raise RuntimeError(R)
            cache[key] = R["phi"] > theta + eps
        return cache[key]

    if fails([0]*n):
        return {"cuts": [[0]*n], "lp_calls": len(cache)}

    dmax = {v: durations[-1] for v in eligible}      # longest duration below v's singleton cut

    def completions(E, later, p, r):
        """Upper states of the subtree: open slots filled by maximal admissible (node, duration).

        A layer with one open slot (other than p) contributes the antichain of
        (largest node, dmax) pairs; otherwise the next distinct nodes at D_J (Lemma B)."""
        C, used, options = list(E), {p: r}, [[]]
        for q in later:
            if q != p and later.count(q) == 1:
                best, chain = 0, []
                for v in layers[q]:
                    if dmax[v] > best:
                        best = dmax[v]
                        chain.append((v, best))
                options = [o + [x] for o in options for x in chain]
            else:
                used[q] = used.get(q, -1) + 1
                C[layers[q][used[q]]] = durations[-1]
        for o in options:
            F = list(C)
            for v, d in o:
                F[v] = d
            yield F

    def search(pattern, D, i, prev):
        """Fill slot i of the pattern; prev is the rank used by slot i-1 if in the same layer."""
        p = pattern[i]
        later = pattern[i + 1:]
        bound = 0                       # durations ≤ bound survive at all remaining ranks
        for r in range(prev + 1, len(layers[p]) - later.count(p)):
            v = layers[p][r]
            for d in reversed([x for x in durations if bound < x <= dmax[v]]):
                E = list(D)
                E[v] = d
                if dominates(E):
                    continue                         # no minimal cut below (Prop. 1)
                if not any(fails(C) for C in completions(E, later, p, r)):
                    bound = d                        # (r' ≥ r, d' ≤ d) survive (Lemma B)
                    break
                if not later:
                    found.append(E)
                else:
                    search(pattern, E, i + 1, r if later[0] == p else -1)

    for l in range(1, min(k, len(eligible)) + 1):
        found.clear()
        for pattern in combinations_with_replacement(sorted(layers), l):
            if all(pattern.count(p) <= len(layers[p]) for p in pattern):
                search(pattern, [0]*n, 0, -1)
        cuts[:] = _minimal(cuts + found)
        if l == 1:
            for S in cuts:
                v = next(v for v, d in enumerate(S) if d)
                dmax[v] = max([0, *(d for d in durations if d < S[v])])
    return {"cuts": cuts, "lp_calls": len(cache)}
