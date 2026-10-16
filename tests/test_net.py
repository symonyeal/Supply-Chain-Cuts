"""Certificates on the frozen 2024 network and the derived policy node-years."""
import numpy as np
import pytest

from chokepoint.events import YEARS, node_years
from chokepoint.net import LCE_LIOH, build, model
from chokepoint.recourse import solve


@pytest.fixture(scope="module")
def N():
    return build()


def test_requirements_and_baseline(N):
    """R_p = Σ_q a[p,q] R_q; the undisrupted network meets demand exactly (φ(0) = 0)."""
    R = N["requirement"]
    for p in R:
        if p not in N["finals"]:
            assert R[p] == pytest.approx(sum(x*R[q] for r, q, x in N["a"] if r == p))
    assert N["supply_ratio"]["cell"] == pytest.approx(1)
    for s in ("liion", "pv", "joint"):
        M = build(sector=s)
        assert solve(model(M), np.zeros(len(M["nodes"])))["phi"] == pytest.approx(0, abs=1e-9)


def test_labels_and_conversions(N):
    assert {x["basis"] for x in N["nodes"]} <= {"production", "trade", "imputed"}
    assert LCE_LIOH == pytest.approx(73.891/83.928)       # Li2CO3 per 2 LiOH·H2O
    co = {x["country"]: x["annual"] for x in N["nodes"] if x["product"] == "refined_co"}
    assert co["CHN"] == pytest.approx(147.0)                # MYB 2023 Table 8, kt Co
    china = next(x for x in N["nodes"] if x["country"] == "CHN" and x["product"] == "li_carbonate")
    assert china["annual"] == pytest.approx(670 + 360*LCE_LIOH)


def test_node_years_exposure(N):
    """Unsurveyed is missing, not zero; an in-window act adds an onset in a surveyed year."""
    V = [(x["country"], x["product"]) for x in N["nodes"]]
    Y, ids, _ = node_years(V)
    t = list(YEARS).index(2022)
    assert Y[V.index(("ZWE", "mine_li")), t] == 1
    assert "ZWE-SI213-2022" in ids["ZWE:mine_li:2022"]
    assert np.isnan(Y[V.index(("CHN", "cell"))]).all()
    assert np.isin(Y[np.isfinite(Y)], [0, 1]).all()
