"""Independent source-value checks for the observational context."""

import csv
import io
import json

import pytest

from analysis.build_context import R, U, build, outputs, verified

# c: generated context; r: one observational record.


@pytest.fixture(scope="module")
def c():
    return build()


def record(c, commodity, country, year=2025, stage="mine"):
    return next(
        r
        for r in c["production"]
        if (r["commodity"], r["country"], r["year"], r["stage"])
        == (commodity, country, year, stage)
    )


def test_source_values_and_units(c):
    assert record(c, "Lithium", "Australia")["tonnes"] == 92000
    assert record(c, "Lithium", "World total")["tonnes"] == 290000
    assert record(c, "Lithium", "Australia")["share"] == pytest.approx(92000 / 290000)
    assert record(c, "Cobalt", "World total")["tonnes"] == 310000
    assert record(c, "Copper", "World total")["tonnes"] == 23000000
    assert record(c, "Copper", "World total", stage="refinery")["tonnes"] == 29000000
    assert record(c, "Aluminum", "World total", stage="smelter")["tonnes"] == 74000000


def test_withheld_is_missing_and_dash_is_zero(c):
    r = record(c, "Lithium", "United States")
    assert r["tonnes"] is None and r["share"] is None
    assert r["raw"] == "W" and r["missing"] == "withheld"
    assert record(c, "Graphite (Natural)", "United States")["tonnes"] == 0
    assert record(c, "Graphite (Natural)", "United States")["raw"] == "—"
    assert record(c, "Lithium", "Other countries")["aggregate"]
    assert "Excludes U.S." in record(c, "Lithium", "World total")["notes"]
    assert (
        "withheld U.S."
        in next(r for r in c["summaries"] if r["commodity"] == "Lithium")["coverage_note"]
    )


def test_full_scope_and_flags(c):
    assert len(c["production"]) == 240
    assert sum(not r["world"] for r in c["production"]) == 224
    assert sum(r["world"] for r in c["production"]) == 16
    assert len(c["summaries"]) == 16
    assert record(c, "Lithium", "Australia")["estimated"]
    assert all(r["share"] is None for r in c["production"] if r["world"])
    for r in c["summaries"]:
        assert r["named_top_share"] <= r["named_top3_share"]
        assert "lower bound" in r["concentration_label"]


def test_named_concentration_does_not_rank_other_countries(c):
    r = next(r for r in c["summaries"] if r["commodity"] == "Cobalt" and r["year"] == 2025)
    assert r["named_top_country"] == "Congo (Kinshasa)"
    # Other countries (9,100 t) exceeds Russia (7,700 t) but is not a named producer.
    assert r["named_top3_share"] == pytest.approx((230000 + 44000 + 7700) / 310000)
    assert r["has_aggregate"]
    total = sum(
        r["tonnes"]
        for r in c["production"]
        if r["commodity"] == "Cobalt" and r["year"] == 2025 and not r["world"]
    )
    assert total != 310000  # Published rounded world total must remain the denominator.


def test_iea_coordinates_not_mine_shares(c):
    assert len(c["refining"]) == 16
    r = {r["name"]: r for r in c["refining"]}
    assert r["Lithium"]["top_share"] == 0.74
    assert r["Lithium"]["market_usd_bn"] == 28.85
    assert r["Nickel"]["top_share"] == 0.45
    assert r["Cobalt"]["market_usd_bn"] == 13.93
    assert "Geranium" in r
    assert all("country" not in r for r in c["refining"])


def test_offline_hash_verification():
    sources = json.loads((R / "SOURCES.lock").read_text(encoding="utf8"))["sources"]
    bad = [{**s, "sha256": "0" * 64} if s["path"] == U else s for s in sources]
    with pytest.raises(ValueError, match="Source hash mismatch"):
        verified(R, U, bad)


def test_deterministic_artifacts_and_complete_download(c):
    js, text = outputs(c)
    assert outputs(build()) == (js, text)
    assert (R / "site/context.js").read_bytes() == js.encode("utf8")
    assert (R / "site/context.csv").read_bytes() == text.encode("utf8")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 256
    assert sum(r["dataset"] == "IEA refining" for r in rows) == 16
