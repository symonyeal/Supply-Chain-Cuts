"""Build observational context without changing the frozen network or its results."""

from __future__ import annotations

import csv
import argparse
import hashlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path
import urllib.request

# R: repository root; U/I: frozen USGS/IEA input paths; C: selected commodities.
R = Path(__file__).resolve().parents[1]
U = "data/raw/usgs/MCS2026_Commodities_Data.csv"
I = "data/raw/iea/market-size-refining-2025-chart-options.json"
B = "data/raw/baci/country_codes_V202601.csv"
C = {"Lithium", "Cobalt", "Nickel", "Graphite (Natural)", "Copper", "Manganese", "Aluminum"}


def verified(root: Path, path: str, sources: list[dict]) -> bytes:
    """Read only bytes matching the frozen source manifest."""
    source = next(s for s in sources if s["path"] == path)
    data = (root / path).read_bytes()
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError(f"Source hash mismatch: {path}")
    return data


def fetch_iea(root: Path = R) -> None:
    """Recover the frozen chart options, rejecting changed numerical source bytes."""
    source = next(s for s in json.loads((root / 'SOURCES.lock').read_text(
        encoding='utf8'))['sources'] if s['path'] == I)

    class Chart(HTMLParser):
        options = None

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if values.get('data-chart-identifier') == (
                'market-size-and-top-refining-country-share-for-select-minerals-2025'
            ):
                self.options = values.get('data-chart-chartoptions')

    request = urllib.request.Request(source['url'], headers={'User-Agent': 'Supply-Chain-Cuts'})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode('utf8')
    chart = Chart()
    chart.feed(html)
    if chart.options is None:
        raise ValueError('IEA chart options not found')
    # The original frozen extraction has CRLF bytes, including on a later Linux rebuild.
    text = json.dumps(json.loads(chart.options.replace('\\"', '"')), indent=2, ensure_ascii=False)
    data = (text + '\n').replace('\n', '\r\n').encode('utf8')
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('IEA chart changed; frozen source was not overwritten')
    (root / I).parent.mkdir(parents=True, exist_ok=True)
    (root / I).write_bytes(data)


def build(root: Path = R) -> dict:
    """Extract country output and a separate refining cross-section."""
    sources = json.loads((root / "SOURCES.lock").read_text(encoding="utf8"))["sources"]
    raw = verified(root, U, sources).decode("cp1252")
    # The XML metadata defines em dash as zero, W as withheld, and NA as unavailable.
    verified(root, "data/raw/usgs/MCS2026_Commodities_Data.xml", sources)
    production = []
    for row in csv.DictReader(io.StringIO(raw)):
        if (
            row["Commodity"] not in C
            or "World" not in row["Section"]
            or row["Statistics"] != "Production"
            or row["Year"] not in {"2024", "2025"}
        ):
            continue
        value = row["Value"].strip()
        missing = None
        if value == "—":
            tonnes = 0
        elif value in {"W", "NA", "XX", "s", "E", ""}:
            tonnes = None
            missing = {"W": "withheld", "NA": "unavailable", "s": "small"}.get(
                value, "unquantified"
            )
        else:
            tonnes = float(value.replace(",", ""))
            if row["Unit"] == "thousand metric tons":
                tonnes *= 1000
            elif row["Unit"] != "metric tons":
                raise ValueError(f"Unexpected unit: {row['Unit']}")
            tonnes = int(tonnes) if tonnes.is_integer() else tonnes
        stage = row["Statistics_detail"].split()[0].lower()
        production.append(
            {
                "commodity": row["Commodity"],
                "stage": stage,
                "year": int(row["Year"]),
                "country": row["Country"],
                "tonnes": tonnes,
                "raw": value,
                "notes": row["Notes"],
                "source_notes": row["Other notes"],
                "estimated": "Estimated" in row["Notes"],
                "aggregate": row["Country"] == "Other countries",
                "world": row["Country"] == "World total",
                "missing": missing,
            }
        )
    production.sort(key=lambda row: (row["commodity"], row["stage"], row["year"], row["country"]))
    summaries = []
    groups = sorted({(r["commodity"], r["stage"], r["year"]) for r in production})
    for commodity, stage, year in groups:
        rows = [
            r
            for r in production
            if (r["commodity"], r["stage"], r["year"]) == (commodity, stage, year)
        ]
        world = next(r["tonnes"] for r in rows if r["world"])
        for row in rows:
            row["share"] = (
                row["tonnes"] / world if row["tonnes"] is not None and not row["world"] else None
            )
        named = sorted(
            (r for r in rows if not r["world"] and not r["aggregate"] and r["tonnes"] is not None),
            key=lambda r: r["tonnes"],
            reverse=True,
        )
        summaries.append(
            {
                "commodity": commodity,
                "stage": stage,
                "year": year,
                "world_tonnes": world,
                "named_top_country": named[0]["country"],
                "named_top_share": named[0]["share"],
                "named_top3_share": sum(r["tonnes"] for r in named[:3]) / world,
                "has_aggregate": any(r["aggregate"] for r in rows),
                "has_missing": any(r["missing"] for r in rows),
                "coverage_note": "Excludes withheld U.S. production."
                if commodity == "Lithium"
                else "Published world total; includes other countries where reported.",
                "concentration_label": (
                    "Named-country shares; top-three sum is a lower bound when aggregate "
                    "or withheld output is present, subject to rounded totals."
                ),
            }
        )
    chart = json.loads(verified(root, I, sources))
    countries = {
        row['country_iso3']: row['country_name']
        for row in csv.DictReader(io.StringIO(verified(root, B, sources).decode('utf8')))
    }
    refining = [
        {
            "name": point["name"],
            "group": series["name"],
            "top_share": point["x"] / 100,
            "market_usd_bn": point["y"],
            "year": 2025,
        }
        for series in chart["series"]
        for point in series["data"]
    ]
    return {
        "meta": {
            "years": [2024, 2025],
            "generated_from": "analysis/build_context.py",
            "countries": countries,
            "sources": [
                {k: s[k] for k in ("path", "url", "retrieved", "licence", "sha256")}
                for s in sources
                if s["path"] in {U, I, B, "data/raw/usgs/MCS2026_Commodities_Data.xml"}
            ],
            "production_note": (
                "Output, not installed capacity. Shares divide by published rounded world totals "
                "and are not renormalized; rounded country values may not add to totals. "
                "2025 figures include estimates."
            ),
            "refining_note": (
                "IEA 2025 cross-section, published 2026. Top refining country identity is not "
                "supplied by this chart. Market size is billion USD; shares are fractions. "
                "Source label Geranium is preserved verbatim."
            ),
            "model_note": (
                "Observational context only; does not update the frozen 2024 reference network, "
                "cut sets or probabilities."
            ),
        },
        "production": production,
        "refining": refining,
        "summaries": summaries,
    }


def outputs(context: dict) -> tuple[str, str]:
    """Return deterministic browser data and a complete long-form CSV."""
    js = "window.CONTEXT=" + json.dumps(context, ensure_ascii=False, separators=(",", ":")) + ";\n"
    fields = [
        "dataset",
        "commodity",
        "stage",
        "year",
        "country",
        "tonnes",
        "raw",
        "notes",
        "source_notes",
        "estimated",
        "aggregate",
        "world",
        "missing",
        "share",
        "group",
        "top_share",
        "market_usd_bn",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in context["production"]:
        writer.writerow({"dataset": "USGS production", **row})
    for row in context["refining"]:
        writer.writerow(
            {
                "dataset": "IEA refining",
                "commodity": row["name"],
                "year": row["year"],
                "stage": "refining",
                "group": row["group"],
                "top_share": row["top_share"],
                "market_usd_bn": row["market_usd_bn"],
            }
        )
    return js, buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-iea', action='store_true',
                        help='Re-fetch chart options only if they match the frozen digest')
    if parser.parse_args().fetch_iea:
        fetch_iea()
    context = build()
    js, csv_text = outputs(context)
    (R / "site/context.js").write_bytes(js.encode("utf8"))
    (R / "site/context.csv").write_bytes(csv_text.encode("utf8"))
    print(
        f"Production rows: {len(context['production'])}; "
        f"refining points: {len(context['refining'])}; "
        f"commodity-stage-year summaries: {len(context['summaries'])}"
    )


if __name__ == "__main__":
    main()
