"""Independent certificates on networks with hand-derived cut sets."""
import numpy as np
import pytest

from chokepoint.recourse import matrices, solve
from chokepoint.cuts import enumerate_cuts
from chokepoint.brute import enumerate_brute
from chokepoint.sweep import certified_lattice, sparse


def test_duration_lattice():
    """Two parallel suppliers: failure > 5 requires either 8 or both 4-unit losses."""
    V = [("A", "ore"), ("B", "ore"), ("C", "cell")]
    u, a, d = [4, 4, 8], {("ore", "cell"): 1}, [8, 8]
    M = matrices(V, u, a, d)
    C = enumerate_cuts(M, [1, 2], alpha=0.3, k=2)
    B = enumerate_brute(M, [1, 2], alpha=0.3, k=2)["cuts"]
    assert C["complete"]
    assert {tuple(x["D"]) for x in C["cuts"]} == {
        (2, 0, 0), (0, 2, 0), (0, 0, 1), (1, 1, 0)
    }
    assert {tuple(x["D"]) for x in C["cuts"]} == {tuple(x) for x in B}
    for S in C["cuts"]:
        assert S["phi"] > 4.8
        assert abs(S["phi"] - S["dual"]) < 1e-7
        assert all(x["phi"] <= 4.8 + 1e-7 for x in S["predecessors"])


def test_shared_sweep_returns_sparse_cuts_and_certificates():
    M = matrices([("A", "ore"), ("B", "ore"), ("C", "cell")],
                 [4, 4, 8], {("ore", "cell"): 1}, [8, 8])
    result = certified_lattice(M, alpha=0.3, durations=(1, 2), k=3)
    expected = sparse(enumerate_brute(M, [1, 2], alpha=0.3, k=3)["cuts"])
    assert expected
    assert result["cuts"] == expected
    assert result["lp_calls"] > 0 and result["seconds"] >= 0
    assert len(result["certificates"]) == len(expected)
    assert all(c["certified"] for c in result["certificates"])


def test_absent_input_is_not_free_material():
    M = matrices([("A", "cell")], [10], {("ore", "cell"): 2}, [10])
    R = solve(M, [0])
    assert R["status"] == "optimal"
    assert R["phi"] == pytest.approx(10)
    assert R["dual"] == pytest.approx(10)


def test_dual_bound_at_converging_paths():
    V = [("A", "raw"), ("B", "p"), ("C", "q"), ("D", "cell")]
    a = {("raw", "p"): 2, ("raw", "q"): 3,
         ("p", "cell"): 4, ("q", "cell"): 5}
    M = matrices(V, [100, 20, 20, 5], a, [5, 5], h=0.3)
    for D in ([0, 0, 0, 0], [2, 0, 0, 0], [0, 1, 2, 0], [0, 0, 0, 2]):
        R = solve(M, D)
        assert abs(R["phi"] - R["dual"]) < 1e-7
        assert R["residual"] < 1e-7


def test_invalid_product_cycle():
    with pytest.raises(ValueError, match="acyclic"):
        matrices([("A", "p"), ("B", "q")], [1, 1],
                 {("p", "q"): 1, ("q", "p"): 1}, [1], final="q")


def test_strict_boundary():
    M = matrices([("A", "cell")], [10], {}, np.full(24, 10))
    C = enumerate_cuts(M, [6, 12], alpha=0.25, k=1)
    assert C["complete"]
    assert [x["D"] for x in C["cuts"]] == [[12]]


def test_aggregation_preserves_recourse_without_inventory():
    V = [("A", "ore"), ("B", "ore"), ("C", "cell"), ("D", "cell")]
    args = V, [3, 5, 4, 4], {("ore", "cell"): 1}, [8, 8]
    M, N = matrices(*args), matrices(*args, aggregate=False)
    for D in ([0, 0, 0, 0], [2, 0, 0, 0], [0, 1, 2, 0], [0, 0, 0, 2]):
        assert solve(M, D)["phi"] == pytest.approx(solve(N, D)["phi"])


def test_near_boundary_cut_is_not_lost():
    M = matrices([("A", "cell"), ("B", "cell")], [0.5000004, 0.4999996], {}, [1])
    C = enumerate_cuts(M, [1], alpha=0.5, k=1)
    assert C["complete"]
    assert [x["D"] for x in C["cuts"]] == [[1, 0]]


def test_lattice_equals_brute():
    """Lemma B pruning loses no cut: lattice search = exhaustive search on random networks."""
    from chokepoint.brute import enumerate_lattice
    rng = np.random.default_rng(3)
    for trial in range(6):
        V = [(c, p) for p, m in (("ore", 4), ("cam", 3), ("cell", 3)) for c in "ABCD"[:m]]
        u = rng.uniform(0.2, 1.5, len(V))
        a = {("ore", "cam"): 1.0, ("cam", "cell"): 1.0}
        h, sigma = (0, 0) if trial < 3 else (0.4, 0.2)
        M = matrices(V, u, a, np.full(6, 1.2), h, sigma, 2)
        for alpha in (0.1, 0.3):
            B = sorted(map(tuple, enumerate_brute(M, [2, 4], alpha=alpha, k=3)["cuts"]))
            C = sorted(map(tuple, enumerate_lattice(M, [2, 4], alpha=alpha, k=3)["cuts"]))
            assert B == C


@pytest.mark.slow
def test_lattice_equals_brute_deep():
    """Four layers, three durations, singletons at intermediate durations."""
    from chokepoint.brute import enumerate_lattice
    rng = np.random.default_rng(11)
    layers = (("ore", 3), ("ref", 3), ("cam", 2), ("cell", 3))
    a = {("ore", "ref"): 1.0, ("ref", "cam"): 1.0, ("cam", "cell"): 1.0}
    seen = 0
    for trial in range(8):
        V = [(c, p) for p, m in layers for c in "ABC"[:m]]
        u = np.concatenate([rng.dirichlet(np.ones(m))*rng.uniform(1.0, 1.6) for _, m in layers])
        h, sigma = ((0, 0), (0.5, 0), (0, 0.3), (0.5, 0.3))[trial % 4]
        M = matrices(V, u/12, a, np.full(12, 1/12), h, sigma, 2, ends=[1, 2, 3, 6, 12])
        for alpha in (0.08, 0.2):
            B = sorted(map(tuple, enumerate_brute(M, [1, 3, 6], alpha=alpha, k=3)["cuts"]))
            C = sorted(map(tuple, enumerate_lattice(M, [1, 3, 6], alpha=alpha, k=3)["cuts"]))
            assert B == C
            seen += sum(sum(x > 0 for x in S) > 1 for S in B)
    assert seen > 10


def test_non_optimal_worst_state_is_incomplete(monkeypatch):
    from chokepoint import cuts

    M = matrices([("A", "ore"), ("B", "ore"), ("C", "cell")], [4, 4, 8],
                 {("ore", "cell"): 1}, [8, 8])
    monkeypatch.setattr(cuts, "solve", lambda *a, **k: {"status": "numerical"})
    C = enumerate_cuts(M, [1, 2], alpha=0.3, k=2)
    assert not C["complete"] and C["status"] == "worst_state_numerical"


def _stub(theta, **kw):
    """A solver whose primal sits at theta + 2e-7 and whose dual sits at theta - 8e-7."""
    def solve(M, D, dual=True, **_):
        R = {"status": "optimal", "phi": theta + 2e-7, "dual": theta - 8e-7, "gap": 1e-6,
             "residual": 0.0, **kw}
        return R if dual else {**R, "dual": None, "gap": None}
    return solve


def _net():
    M = matrices([("A", "ore"), ("B", "ore"), ("C", "cell")], [4, 4, 8],
                 {("ore", "cell"): 1}, [8, 8])
    return M, 0.3*M["total"]


def _blocked():
    """Primal-only classifiers would call the crafted state a failure; each path must refuse."""
    from chokepoint import brute, risk
    M, theta = _net()
    p, w = [0.3, 0.3, 0.3], [0.5, 0.5]
    return {
        "brute": lambda: brute.enumerate_brute(M, [1, 2], alpha=0.3, k=2),
        "lattice": lambda: brute.enumerate_lattice(M, [1, 2], alpha=0.3, k=2),
        "residual": lambda: risk.residual_sampling(M, p, 0.4, [1, 2], w, [], alpha=0.3, n=50),
        "importance": lambda: risk.importance_sampling(M, p, 0.4, [1, 2], w, [], alpha=0.3,
                                                       n=50, pilot=0),
        "partial": lambda: risk.partial_sampling(
            M, p, 0.4, [1, 2], w, [{"a": 1.0}]*3, {"c": {"a": 0.5}}, alpha=0.3, n=50),
    }, theta


@pytest.mark.parametrize("path", ["brute", "lattice", "residual", "importance", "partial"])
def test_crafted_boundary_state_is_refused(monkeypatch, path):
    from chokepoint import recourse
    calls, theta = _blocked()
    monkeypatch.setattr(recourse, "solve", _stub(theta))
    out = calls[path]()
    assert out["status"] == "boundary" and not out.get("cuts")


@pytest.mark.parametrize("path", ["brute", "lattice", "residual", "importance", "partial"])
@pytest.mark.parametrize("fault", [{"status": "numerical"}, {"status": "limit"},
                                   {"status": "infeasible"}, {"residual": 2e-6}])
def test_solver_outcomes_are_values(monkeypatch, path, fault):
    from chokepoint import recourse
    calls, theta = _blocked()
    monkeypatch.setattr(recourse, "solve", _stub(theta, **fault))
    out = calls[path]()
    assert out["status"] == fault.get("status", "residual") and not out.get("cuts")


@pytest.mark.parametrize("fault", [{"status": "numerical"}, {"status": "infeasible"},
                                   {"residual": 2e-6}, {"dual": 5.0 + 3e-7, "gap": 2e-6}])
def test_certificate_requires_dual_residual_and_status(monkeypatch, fault):
    from chokepoint import sweep
    good = {"status": "optimal", "phi": 5.0 + 3e-7, "dual": 5.0 + 3e-7, "gap": 0.0,
            "residual": 0.0}
    out = dict(good)
    monkeypatch.setattr(sweep, "solve", lambda *a, **k: out)
    assert sweep.certify(None, [0], 5.0)["certified"]
    out.update(fault)
    assert not sweep.certify(None, [0], 5.0)["certified"]
    out.update(good, dual=5.0 - 8e-7, phi=5.0 + 2e-7, gap=1e-6)
    assert not sweep.certify(None, [0], 5.0)["certified"]


def test_certificate_predecessor_status_is_a_value(monkeypatch):
    from chokepoint import sweep
    good = {"status": "optimal", "phi": 6.0, "dual": 6.0, "gap": 0.0, "residual": 0.0}
    monkeypatch.setattr(sweep, "solve", lambda M, D, dual=True: good if dual
                        else {"status": "numerical"})
    assert not sweep.certify(None, [3], 5.0)["certified"]


def test_runner_exits_on_blocked_sampler():
    from chokepoint.fetch import sampled
    ok = {"estimate": 0.1}
    assert sampled(ok) is ok and sampled({"status": "optimal"})
    with pytest.raises(SystemExit, match="boundary"):
        sampled({"status": "boundary", "samples_completed": 3})
