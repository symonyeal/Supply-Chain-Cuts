//! Frozen primary-source processing. No subprocess or Python runtime is used.
// R/root: repository; U/I/B: frozen paths; r: source row; c: context; n: number.
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, path::Path};
mod network;
pub use network::{bill, network};

/// SHA-256 for result provenance; raw-input verification uses the same digest.
pub fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

const U: &str = "data/raw/usgs/MCS2026_Commodities_Data.csv";
const I: &str = "data/raw/iea/market-size-refining-2025-chart-options.json";
const B: &str = "data/raw/baci/country_codes_V202601.csv";
const X: &str = "data/raw/usgs/MCS2026_Commodities_Data.xml";
pub(crate) type Row = BTreeMap<String, String>;

pub(crate) fn manifest(root: &Path) -> Result<Value, String> {
    serde_json::from_slice(&fs::read(root.join("SOURCES.lock")).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())
}

pub(crate) fn read(root: &Path, path: &str) -> Result<Vec<u8>, String> {
    let lock = manifest(root)?;
    let source = lock["sources"]
        .as_array()
        .ok_or("Missing source list")?
        .iter()
        .find(|s| s["path"] == path)
        .ok_or_else(|| format!("Unmanifested source: {path}"))?;
    let bytes = fs::read(root.join(path)).map_err(|e| format!("{path}: {e}"))?;
    let hash = digest(&bytes);
    if source["sha256"] != hash {
        return Err(format!("Source hash mismatch: {path}"));
    }
    Ok(bytes)
}

pub(crate) fn rows(root: &Path, path: &str, cp1252: bool) -> Result<Vec<Row>, String> {
    let bytes = read(root, path)?;
    let text = if cp1252 {
        decode_cp1252(&bytes)?
    } else {
        String::from_utf8(bytes).map_err(|e| e.to_string())?
    };
    let mut reader = csv::Reader::from_reader(text.as_bytes());
    let header = reader.headers().map_err(|e| e.to_string())?.clone();
    reader
        .records()
        .map(|row| {
            let row = row.map_err(|e| e.to_string())?;
            Ok(header
                .iter()
                .zip(row.iter())
                .map(|(k, v)| (k.to_string(), v.to_string()))
                .collect())
        })
        .collect()
}

fn decode_cp1252(bytes: &[u8]) -> Result<String, String> {
    // Windows-1252's C1 block; undefined bytes are rejected, as Python's strict decoder does.
    const C1: [u32; 32] = [
        0x20ac, 0, 0x201a, 0x192, 0x201e, 0x2026, 0x2020, 0x2021, 0x2c6, 0x2030, 0x160, 0x2039,
        0x152, 0, 0x17d, 0, 0, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014, 0x2dc,
        0x2122, 0x161, 0x203a, 0x153, 0, 0x17e, 0x178,
    ];
    bytes
        .iter()
        .map(|b| {
            let code = if (0x80..=0x9f).contains(b) {
                C1[(*b - 0x80) as usize]
            } else {
                *b as u32
            };
            if code == 0 && *b != 0 {
                Err(format!("Undefined Windows-1252 byte: {b:x}"))
            } else {
                char::from_u32(code).ok_or("Invalid Windows-1252 codepoint".into())
            }
        })
        .collect()
}

pub(crate) fn num(s: &str) -> Result<f64, String> {
    s.parse::<f64>()
        .map_err(|e| format!("Invalid number {s:?}: {e}"))
}

/// Verify every committed raw source, returning paths, lengths and digests.
pub fn verify(root: &Path) -> Result<Value, String> {
    let lock = manifest(root)?;
    let mut verified = vec![];
    for source in lock["sources"].as_array().ok_or("Missing source list")? {
        if source["committed"] != true {
            continue;
        }
        let path = source["path"].as_str().ok_or("Missing source path")?;
        let bytes = read(root, path)?;
        verified.push(json!({"path":path,"bytes":bytes.len(),"sha256":source["sha256"]}));
    }
    Ok(json!({"count":verified.len(),"verified":verified}))
}

/// Observational context, independent of the historical network and cut results.
pub fn context(root: &Path) -> Result<Value, String> {
    let sources = manifest(root)?;
    read(root, X)?;
    let mut production = vec![];
    for r in rows(root, U, true)? {
        if ![
            "Lithium",
            "Cobalt",
            "Nickel",
            "Graphite (Natural)",
            "Copper",
            "Manganese",
            "Aluminum",
        ]
        .contains(&r["Commodity"].as_str())
            || !r["Section"].contains("World")
            || r["Statistics"] != "Production"
            || !["2024", "2025"].contains(&r["Year"].as_str())
        {
            continue;
        }
        let value = r["Value"].trim();
        let (tonnes, missing) = if value == "—" {
            (json!(0), Value::Null)
        } else if ["W", "NA", "XX", "s", "E", ""].contains(&value) {
            (
                Value::Null,
                json!(match value {
                    "W" => "withheld",
                    "NA" => "unavailable",
                    "s" => "small",
                    _ => "unquantified",
                }),
            )
        } else {
            let mut n = num(&value.replace(',', ""))?;
            if r["Unit"] == "thousand metric tons" {
                n *= 1000.0;
            } else if r["Unit"] != "metric tons" {
                return Err(format!("Unexpected unit: {}", r["Unit"]));
            }
            (
                if n.fract() == 0.0 {
                    json!(n as i64)
                } else {
                    json!(n)
                },
                Value::Null,
            )
        };
        let stage = r["Statistics_detail"]
            .split_whitespace()
            .next()
            .ok_or("Missing stage")?
            .to_lowercase();
        production.push(json!({"commodity":r["Commodity"],"stage":stage,
            "year":r["Year"].parse::<u32>().map_err(|e|e.to_string())?,"country":r["Country"],
            "tonnes":tonnes,"raw":value,"notes":r["Notes"],"source_notes":r["Other notes"],
            "estimated":r["Notes"].contains("Estimated"),"aggregate":r["Country"]=="Other countries",
            "world":r["Country"]=="World total","missing":missing}));
    }
    let key = |r: &Value| {
        (
            r["commodity"].as_str().unwrap().to_string(),
            r["stage"].as_str().unwrap().to_string(),
            r["year"].as_u64().unwrap(),
            r["country"].as_str().unwrap().to_string(),
        )
    };
    production.sort_by_key(&key);
    let mut summaries = vec![];
    let mut start = 0;
    while start < production.len() {
        let (commodity, stage, year, _) = key(&production[start]);
        let mut end = start + 1;
        while end < production.len() {
            let k = key(&production[end]);
            if (k.0, k.1, k.2) != (commodity.clone(), stage.clone(), year) {
                break;
            }
            end += 1;
        }
        let group = &mut production[start..end];
        let world = group
            .iter()
            .find(|r| r["world"] == true)
            .ok_or("Missing world total")?["tonnes"]
            .as_f64()
            .ok_or("Missing world value")?;
        for r in group.iter_mut() {
            r["share"] = if r["world"] != true {
                r["tonnes"]
                    .as_f64()
                    .map(|n| json!(n / world))
                    .unwrap_or(Value::Null)
            } else {
                Value::Null
            };
        }
        let mut named: Vec<&Value> = group
            .iter()
            .filter(|r| r["world"] != true && r["aggregate"] != true && !r["tonnes"].is_null())
            .collect();
        named.sort_by(|a, b| {
            b["tonnes"]
                .as_f64()
                .partial_cmp(&a["tonnes"].as_f64())
                .unwrap()
        });
        let top3: f64 = named
            .iter()
            .take(3)
            .map(|r| r["tonnes"].as_f64().unwrap())
            .sum();
        summaries.push(json!({"commodity":commodity,"stage":stage,"year":year,"world_tonnes":world as i64,
            "named_top_country":named[0]["country"],"named_top_share":named[0]["share"],"named_top3_share":top3/world,
            "has_aggregate":group.iter().any(|r|r["aggregate"]==true),"has_missing":group.iter().any(|r|!r["missing"].is_null()),
            "coverage_note":if commodity=="Lithium" {"Excludes withheld U.S. production."} else {"Published world total; includes other countries where reported."},
            "concentration_label":"Named-country shares; top-three sum is a lower bound when aggregate or withheld output is present, subject to rounded totals."}));
        start = end;
    }
    let chart: Value = serde_json::from_slice(&read(root, I)?).map_err(|e| e.to_string())?;
    let mut refining = vec![];
    for series in chart["series"].as_array().ok_or("Missing IEA series")? {
        for point in series["data"].as_array().ok_or("Missing IEA points")? {
            refining.push(json!({"name":point["name"],"group":series["name"],"top_share":point["x"].as_f64().ok_or("Missing x")?/100.0,"market_usd_bn":point["y"],"year":2025}));
        }
    }
    let mut countries = serde_json::Map::new();
    for r in rows(root, B, false)? {
        countries.insert(r["country_iso3"].clone(), json!(r["country_name"]));
    }
    let sources: Vec<Value> = sources["sources"]
        .as_array()
        .ok_or("Missing sources")?
        .iter()
        .filter(|s| [U, I, B, X].contains(&s["path"].as_str().unwrap_or("")))
        .map(|s| {
            let mut source = serde_json::Map::new();
            for k in ["path", "url", "retrieved", "licence", "sha256"] {
                source.insert(k.into(), s[k].clone());
            }
            Value::Object(source)
        })
        .collect();
    Ok(
        json!({"meta":{"years":[2024,2025],"generated_from":"analysis/build_context.py","countries":countries,"sources":sources,
        "production_note":"Output, not installed capacity. Shares divide by published rounded world totals and are not renormalized; rounded country values may not add to totals. 2025 figures include estimates.",
        "refining_note":"IEA 2025 cross-section, published 2026. Top refining country identity is not supplied by this chart. Market size is billion USD; shares are fractions. Source label Geranium is preserved verbatim.",
        "model_note":"Observational context only; does not update the frozen 2024 reference network, cut sets or probabilities."},"production":production,"refining":refining,"summaries":summaries}),
    )
}

fn py_text(v: &Value) -> String {
    match v {
        Value::Null => String::new(),
        Value::Bool(b) => if *b { "True" } else { "False" }.into(),
        Value::String(s) => s.clone(),
        Value::Number(n) if n.is_f64() => {
            let x = n.as_f64().unwrap();
            if x != 0.0 && (x.abs() < 1e-4 || x.abs() >= 1e16) {
                let text = format!("{x:e}");
                let (mantissa, exponent) = text.split_once('e').unwrap();
                let exponent = exponent.parse::<i32>().unwrap();
                format!("{mantissa}e{exponent:+03}")
            } else {
                v.to_string()
            }
        }
        _ => v.to_string(),
    }
}

/// Complete long-form CSV. Booleans follow the original Python export spelling.
pub fn context_csv(c: &Value) -> Result<String, String> {
    let fields = [
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
    ];
    let mut writer = csv::WriterBuilder::new()
        .terminator(csv::Terminator::Any(b'\n'))
        .from_writer(vec![]);
    writer.write_record(fields).map_err(|e| e.to_string())?;
    for r in c["production"].as_array().ok_or("Missing production")? {
        let record: Vec<String> = fields
            .iter()
            .map(|k| {
                if *k == "dataset" {
                    "USGS production".into()
                } else {
                    py_text(&r[*k])
                }
            })
            .collect();
        writer.write_record(record).map_err(|e| e.to_string())?;
    }
    for r in c["refining"].as_array().ok_or("Missing refining")? {
        let record: Vec<String> = fields
            .iter()
            .map(|k| match *k {
                "dataset" => "IEA refining".into(),
                "commodity" => py_text(&r["name"]),
                "stage" => "refining".into(),
                _ => py_text(&r[*k]),
            })
            .collect();
        writer.write_record(record).map_err(|e| e.to_string())?;
    }
    String::from_utf8(writer.into_inner().map_err(|e| e.to_string())?).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cp1252_preserves_source_punctuation_and_rejects_undefined_bytes() {
        assert_eq!(
            decode_cp1252(&[0x93, b'A', 0x94, 0x97, 0xe9]).unwrap(),
            "“A”—é"
        );
        assert!(decode_cp1252(&[0x81]).is_err());
    }

    #[test]
    fn python_csv_scalar_spelling() {
        assert_eq!(py_text(&json!(true)), "True");
        assert_eq!(py_text(&json!(Value::Null)), "");
        assert_eq!(
            py_text(&json!(0.00006451612903225807)),
            "6.451612903225807e-05"
        );
        assert_eq!(py_text(&json!(1e16)), "1e+16");
    }
}
