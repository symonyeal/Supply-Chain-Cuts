//! Physical network, preserving raw-row accumulation and node insertion order.
// B: bill of materials; E/I: exports/imports; a: physical coefficients; R/S: requirement/supply.
use crate::{Sources, num};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

const HS: [(&str, &str); 9] = [
    ("li_carbonate", "283691"),
    ("refined_ni", "750210"),
    ("refined_co", "810520"),
    ("synthetic_graphite", "380110"),
    ("cell", "850760"),
    ("polysilicon", "280461"),
    ("wafer", "381800"),
    ("pv_cell", "854142"),
    ("module", "854143"),
];
const PV: [&str; 4] = ["polysilicon", "wafer", "pv_cell", "module"];
type Flows = BTreeMap<(String, String), f64>;

// CPython 3.14 sum(float): Neumaier compensation; explicit += sites remain uncorrected.
fn sum(values: impl IntoIterator<Item = f64>) -> f64 {
    let (mut hi, mut lo) = (0.0f64, 0.0f64);
    for x in values {
        let t = hi + x;
        lo += if hi.abs() >= x.abs() {
            (hi - t) + x
        } else {
            (x - t) + hi
        };
        hi = t;
    }
    hi + lo
}

pub(super) fn bill(sources: &Sources<'_>, ncm: f64) -> Result<Value, String> {
    if !(0.0..=1.0).contains(&ncm) {
        return Err("NCM622 fraction must be in [0,1]".into());
    }
    let rows = sources.rows("data/raw/xu2020/bom_mid_size_bev.csv", false)?;
    let (mut b, mut lfp, mut ncmb) = (
        BTreeMap::<String, f64>::new(),
        BTreeMap::<String, f64>::new(),
        BTreeMap::<String, f64>::new(),
    );
    for r in rows {
        let chem = r["chemistry"].as_str();
        if chem != "LFP" && chem != "NCM622" {
            continue;
        }
        let weight = if chem == "NCM622" { ncm } else { 1.0 - ncm };
        let kg = num(&r["kg_per_pack"])?;
        *b.entry(r["material"].clone()).or_default() += weight * kg / num(&r["pack_kwh"])?;
        (if chem == "LFP" { &mut lfp } else { &mut ncmb }).insert(r["material"].clone(), kg / 66.0);
    }
    let energies: BTreeMap<String, f64> = sources
        .rows("data/raw/xu2020/specific_energy.csv", false)?
        .iter()
        .map(|r| Ok((r["chemistry"].clone(), num(&r["wh_per_kg"])?)))
        .collect::<Result<_, String>>()?;
    let cam_lfp = lfp["Li"] * (6.94 + 55.845 + 30.974 + 4.0 * 15.999) / 6.94;
    let cam_ncm =
        sum(["Li", "Ni", "Co", "Mn"].iter().map(|m| ncmb[*m])) + ncmb["Li"] * 2.0 * 15.999 / 6.94;
    let pcam = sum([("Ni", 58.6934), ("Co", 58.9332), ("Mn", 54.938)]
        .iter()
        .map(|(x, m)| ncmb[*x] * (1.0 + 2.0 * 17.007 / m)));
    Ok(
        json!({"kg_kwh":b,"ncm_fraction":ncm,"cam_kg_kwh":(1.0-ncm)*cam_lfp+ncm*cam_ncm,"pcam_kg_kwh":ncm*pcam,"lce_kg_kwh":b["Li"]*5.323,"specific_energy_wh_kg":1.0/((1.0-ncm)/energies["LFP"]+ncm/energies["NCM622"]),"basis":"pack_BOM_and_pack_specific_energy_applied_to_cell_trade_scenario","source":"Xu2020 SI Tables 1,4,23; stoichiometric conversion; unit yield assumption"}),
    )
}

fn put(
    nodes: &mut Vec<Value>,
    exclude: &BTreeSet<(String, String)>,
    c: &str,
    p: &str,
    annual: f64,
    [basis, unit, source, note]: [&str; 4],
) {
    if annual <= 0.0 || exclude.contains(&(c.into(), p.into())) {
        return;
    }
    let v = json!({"country":c,"product":p,"annual":annual,"basis":basis,"unit":unit,"source":source,"note":note});
    if let Some(old) = nodes
        .iter_mut()
        .find(|r| r["country"] == c && r["product"] == p)
    {
        *old = v;
    } else {
        nodes.push(v);
    }
}
fn val(r: &Value, k: &str) -> f64 {
    r[k].as_f64().unwrap()
}
fn total(nodes: &[Value], p: &str) -> f64 {
    sum(nodes
        .iter()
        .filter(|r| r["product"] == p)
        .map(|r| val(r, "annual")))
}
fn depth(p: &str, a: &[(String, String, f64)]) -> usize {
    a.iter()
        .filter(|r| r.0 == p)
        .map(|r| 1 + depth(&r.1, a))
        .max()
        .unwrap_or(0)
}
fn closure(p: &str, a: &[(String, String, f64)]) -> BTreeSet<String> {
    let mut out = BTreeSet::from([p.to_string()]);
    for (r, q, _) in a {
        if q == p {
            out.extend(closure(r, a));
        }
    }
    out
}
fn trade(c: &str, p: &str, e: &BTreeMap<&str, Flows>, scale: f64) -> f64 {
    let hs = HS.iter().find(|r| r.0 == p).unwrap().1;
    scale
        * e[if PV.contains(&p) { "22" } else { "12" }]
            .get(&(c.into(), hs.into()))
            .copied()
            .unwrap_or(0.0)
}

pub(super) fn network(sources: &Sources<'_>, opts: &Value) -> Result<Value, String> {
    let sector = opts["sector"].as_str().unwrap_or("liion");
    let ncm = opts["ncm"].as_f64().unwrap_or(0.5);
    let cutoff = opts["cutoff"].as_f64().unwrap_or(0.01);
    let basis = opts["basis"].as_str().unwrap_or("production");
    if !["liion", "pv", "joint"].contains(&sector) || !(0.0..1.0).contains(&cutoff) {
        return Err("sector in liion,pv,joint and 0 <= cutoff < 1 required".into());
    }
    if !["production", "trade"].contains(&basis) {
        return Err("basis in production,trade required".into());
    }
    let mut excluded = BTreeSet::new();
    if let Some(ex) = opts["exclude"].as_array() {
        for pair in ex {
            excluded.insert((
                pair[0]
                    .as_str()
                    .ok_or("Invalid excluded country")?
                    .to_string(),
                pair[1]
                    .as_str()
                    .ok_or("Invalid excluded product")?
                    .to_string(),
            ));
        }
    }
    let b = bill(sources, ncm)?;
    let country_rows = sources.rows(crate::B, false)?;
    let countries: BTreeMap<String, String> = country_rows
        .iter()
        .map(|r| (r["country_code"].clone(), r["country_iso3"].clone()))
        .collect();
    let mut names: BTreeMap<String, String> = country_rows
        .iter()
        .map(|r| (r["country_name"].to_lowercase(), r["country_iso3"].clone()))
        .collect();
    for (name, c) in [
        ("congo (kinshasa)", "COD"),
        ("korea, republic of", "KOR"),
        ("korea, north", "PRK"),
        ("russia", "RUS"),
        ("turkey", "TUR"),
        ("vietnam", "VNM"),
        ("côte d’ivoire", "CIV"),
        ("côte d'ivoire", "CIV"),
        ("united states", "USA"),
        ("tanzania", "TZA"),
        ("bolivia", "BOL"),
        ("burma", "MMR"),
        ("laos", "LAO"),
    ] {
        names.insert(name.into(), c.into());
    }
    let mut exports = BTreeMap::new();
    let mut imports = BTreeMap::new();
    let mut missing = BTreeMap::new();
    for hs in ["12", "22"] {
        let (mut e, mut i) = (Flows::new(), Flows::new());
        let mut gaps = 0;
        for r in sources.rows(
            &format!("data/raw/baci/BACI_HS{hs}_Y2024_V202601_selected.csv"),
            false,
        )? {
            if r["q"].is_empty() {
                gaps += 1;
                continue;
            }
            let q = num(&r["q"])?;
            *e.entry((
                countries
                    .get(&r["i"])
                    .ok_or("Unmapped BACI origin")?
                    .clone(),
                r["k"].clone(),
            ))
            .or_default() += q;
            *i.entry((
                countries
                    .get(&r["j"])
                    .ok_or("Unmapped BACI destination")?
                    .clone(),
                r["k"].clone(),
            ))
            .or_default() += q;
        }
        exports.insert(hs, e);
        imports.insert(hs, i);
        missing.insert(hs, gaps);
    }
    let chapters = BTreeMap::from([
        ("LITHIUM", "mine_li"),
        ("COBALT", "mine_co"),
        ("NICKEL", "mine_ni"),
        ("GRAPHITE (NATURAL)", "graphite"),
        ("MANGANESE", "mine_mn"),
        ("COPPER", "refined_cu"),
        ("ALUMINUM", "aluminium"),
    ]);
    let mut prod: Vec<(String, String, f64)> = vec![];
    let mut unparsed = vec![];
    for r in sources.rows(crate::U, true)? {
        if r["Year"] != "2024"
            || !r["Section"].starts_with("World")
            || r["Statistics"] != "Production"
            || !chapters.contains_key(r["MCS chapter"].as_str())
        {
            continue;
        }
        if r["MCS chapter"] == "COPPER" && !r["Statistics_detail"].starts_with("Refinery") {
            continue;
        }
        let v = r["Value"].replace(',', "").trim().to_string();
        let Some(c) = names.get(&r["Country"].to_lowercase()) else {
            unparsed.push(json!({"country":r["Country"],"chapter":r["MCS chapter"],"value":v,"reason":"aggregate_or_unmapped"}));
            continue;
        };
        let Ok(value) = v.parse::<f64>() else {
            unparsed.push(json!({"country":c,"chapter":r["MCS chapter"],"value":v,"reason":"withheld_or_non_numeric"}));
            continue;
        };
        let p = chapters[r["MCS chapter"].as_str()];
        let value = value
            * if r["Unit"] == "thousand metric tons" {
                1000.0
            } else {
                1.0
            };
        if let Some(old) = prod.iter_mut().find(|r| r.0 == *c && r.1 == p) {
            old.2 = value;
        } else {
            prod.push((c.clone(), p.into(), value));
        }
    }
    let miit: BTreeMap<String, f64> = sources
        .rows("data/raw/miit/production_2024.csv", false)?
        .iter()
        .filter(|r| r["statistic"] == "production")
        .map(|r| Ok((r["product"].clone(), num(&r["value"])?)))
        .collect::<Result<_, String>>()?;
    let iso3: BTreeSet<String> = countries.values().cloned().collect();
    let mut nodes = vec![];
    if sector == "liion" || sector == "joint" {
        for (c, p, value) in prod {
            put(
                &mut nodes,
                &excluded,
                &c,
                &p,
                value / 1000.0,
                ["production", "kt", "USGS MCS2026, 2024 production", ""],
            );
        }
        for c in &iso3 {
            put(
                &mut nodes,
                &excluded,
                c,
                "li_carbonate",
                trade(c, "li_carbonate", &exports, 1e-3),
                [
                    "trade",
                    "kt",
                    "BACI HS12 2024 283691",
                    "Export proxy, kt Li2CO3",
                ],
            );
            put(
                &mut nodes,
                &excluded,
                c,
                "refined_ni",
                trade(c, "refined_ni", &exports, 1e-3),
                [
                    "trade",
                    "kt",
                    "BACI HS12 2024 750210",
                    "Export proxy; omits domestically absorbed metal",
                ],
            );
            put(
                &mut nodes,
                &excluded,
                c,
                "cell",
                trade(c, "cell", &exports, val(&b, "specific_energy_wh_kg") / 1e6),
                [
                    "trade",
                    "GWh",
                    "BACI HS12 2024 850760",
                    "Pack Wh/kg applied to mixed cell/pack exports",
                ],
            );
            let synthetic = trade(c, "synthetic_graphite", &exports, 1e-3);
            if synthetic != 0.0 {
                let annual = nodes
                    .iter()
                    .find(|r| r["country"] == c.as_str() && r["product"] == "graphite")
                    .map(|r| val(r, "annual"))
                    .unwrap_or(0.0)
                    + synthetic;
                put(
                    &mut nodes,
                    &excluded,
                    c,
                    "graphite",
                    annual,
                    [
                        "imputed",
                        "kt",
                        "USGS natural + BACI 380110 synthetic exports",
                        "Substitution assumed; synthetic exports include non-anode use",
                    ],
                );
            }
        }
        if basis == "production" {
            for r in sources.rows("data/raw/usgs/myb2023_cobalt_refinery.csv", false)? {
                if !r["value"].is_empty() {
                    put(
                        &mut nodes,
                        &excluded,
                        &r["iso3"],
                        "refined_co",
                        num(&r["value"])? / 1000.0,
                        [
                            "production",
                            "kt",
                            "USGS MYB 2023 Table 8",
                            &format!("2023 refinery output, {}", r["qualifier"]),
                        ],
                    );
                }
            }
            put(
                &mut nodes,
                &excluded,
                "CHN",
                "cell",
                miit["li_ion_cell"],
                ["production", "GWh", "MIIT 2024", ""],
            );
            put(
                &mut nodes,
                &excluded,
                "CHN",
                "li_carbonate",
                (miit["battery_grade_lithium_carbonate"]
                    + miit["battery_grade_lithium_hydroxide"] * (73.891 / (2.0 * 41.964)))
                    / 1000.0,
                [
                    "production",
                    "kt",
                    "MIIT 2024",
                    "Battery-grade carbonate + LiOH·H2O as LCE",
                ],
            );
            for r in sources.rows("data/raw/cochilco/lithium_chemicals_2024.csv", false)? {
                if r["product_source_label"] == "CARBONATO DE LITIO" {
                    put(
                        &mut nodes,
                        &excluded,
                        "CHL",
                        "li_carbonate",
                        num(&r["value"])? / 1000.0,
                        [
                            "production",
                            "kt",
                            "Cochilco Hoja1 AD21",
                            "Carbonate only; sulfate excluded",
                        ],
                    );
                }
            }
            if let Some(voltage) = opts["japan_voltage"].as_f64() {
                let q = sum(sources
                    .rows("data/raw/meti/liion_2024.csv", false)?
                    .iter()
                    .map(|r| num(&r["production_kAh"]).unwrap()));
                let text = opts["japan_voltage"].to_string();
                put(
                    &mut nodes,
                    &excluded,
                    "JPN",
                    "cell",
                    q * voltage / 1e6,
                    [
                        "imputed",
                        "GWh",
                        "METI 2024 h2daa2024k, items 0108/0109",
                        &format!(
                            "Sealed Li-ion production kAh times assumed {text} V; not installed capacity; scope excludes unreported battery categories"
                        ),
                    ],
                );
            }
            if opts["eu_sold"] == true {
                let e: Value = serde_json::from_slice(
                    &sources.read("data/raw/supplement/reconciliation.json")?,
                )
                .map_err(|e| e.to_string())?;
                let q = e["eurostat"]["201343Z1"]["DE"]["PRODQNT"]
                    .as_f64()
                    .or_else(|| {
                        e["eurostat"]["201343Z1"]["DE"]["PRODQNT"]
                            .as_str()
                            .and_then(|s| s.parse().ok())
                    })
                    .ok_or("Missing Eurostat quantity")?;
                put(
                    &mut nodes,
                    &excluded,
                    "DEU",
                    "li_carbonate",
                    q / 1e6,
                    [
                        "imputed",
                        "kt",
                        "Eurostat Prodcom 2024 201343Z1 sold quantity",
                        "Sold-output proxy, both purity grades; not actual production or battery grade",
                    ],
                );
            }
        } else {
            for c in &iso3 {
                put(
                    &mut nodes,
                    &excluded,
                    c,
                    "refined_co",
                    trade(c, "refined_co", &exports, 1e-3),
                    [
                        "trade",
                        "kt",
                        "BACI HS12 2024 810520",
                        "Export proxy; HS810520 mixes intermediates",
                    ],
                );
            }
        }
        let cells: Vec<(String, f64)> = nodes
            .iter()
            .filter(|r| r["product"] == "cell")
            .map(|r| (r["country"].as_str().unwrap().into(), val(r, "annual")))
            .collect();
        for (c, output) in cells {
            let china = c == "CHN" && basis == "production";
            for (p, statistic, coefficient) in [
                ("cam", "cathode_active_material", val(&b, "cam_kg_kwh")),
                (
                    "aam",
                    "anode_active_material",
                    val(&b["kg_kwh"], "Graphite"),
                ),
            ] {
                put(
                    &mut nodes,
                    &excluded,
                    &c,
                    p,
                    if china {
                        miit[statistic] / 1000.0
                    } else {
                        output * coefficient
                    },
                    [
                        if china { "production" } else { "imputed" },
                        "kt",
                        if china { "MIIT 2024" } else { "BOM x cell" },
                        "",
                    ],
                );
            }
            if ncm != 0.0 {
                put(
                    &mut nodes,
                    &excluded,
                    &c,
                    "pcam",
                    output * val(&b, "pcam_kg_kwh"),
                    [
                        "imputed",
                        "kt",
                        "BOM x cell",
                        "No pCAM production statistic; tariff-line coverage incomplete",
                    ],
                );
            }
        }
    }
    if sector == "pv" || sector == "joint" {
        for p in PV {
            let hs = HS.iter().find(|r| r.0 == p).unwrap().1;
            let factor = if p == "polysilicon" {
                1e-3
            } else {
                let gw = match p {
                    "wafer" => 60.9,
                    "pv_cell" => 57.5,
                    _ => 238.8,
                };
                gw / exports["22"][&("CHN".into(), hs.into())]
            };
            for c in &iso3 {
                let annual = exports["22"]
                    .get(&(c.clone(), hs.into()))
                    .copied()
                    .unwrap_or(0.0)
                    * factor;
                put(
                    &mut nodes,
                    &excluded,
                    c,
                    p,
                    annual,
                    [
                        "trade",
                        if p == "polysilicon" { "kt" } else { "GW" },
                        "BACI HS22 2024 / MIIT China exports",
                        "HS22 only; silicon and wafer codes include semiconductor products",
                    ],
                );
            }
            if basis == "production" {
                let key = if p == "pv_cell" {
                    "pv_cell".to_string()
                } else {
                    format!("pv_{p}")
                };
                put(
                    &mut nodes,
                    &excluded,
                    "CHN",
                    p,
                    if p == "polysilicon" {
                        miit[&key] / 1000.0
                    } else {
                        miit[&key]
                    },
                    [
                        "production",
                        if p == "polysilicon" { "kt" } else { "GW" },
                        "MIIT 2024",
                        if p == "polysilicon" {
                            "Strict lower bound"
                        } else {
                            ""
                        },
                    ],
                );
            }
        }
    }
    let mut a: Vec<(String, String, f64)> = vec![];
    if sector == "liion" || sector == "joint" {
        for (p, q, x) in [
            ("mine_li", "li_carbonate", 1.0 / 5.323),
            (
                "li_carbonate",
                "cam",
                val(&b, "lce_kg_kwh") / val(&b, "cam_kg_kwh"),
            ),
            ("graphite", "aam", 1.0),
            ("cam", "cell", val(&b, "cam_kg_kwh")),
            ("aam", "cell", b["kg_kwh"]["Graphite"].as_f64().unwrap()),
            ("refined_cu", "cell", b["kg_kwh"]["Cu"].as_f64().unwrap()),
            ("aluminium", "cell", b["kg_kwh"]["Al"].as_f64().unwrap()),
        ] {
            a.push((p.into(), q.into(), x));
        }
        if ncm != 0.0 {
            for (p, q, x) in [
                (
                    "pcam",
                    "cam",
                    val(&b, "pcam_kg_kwh") / val(&b, "cam_kg_kwh"),
                ),
                ("mine_co", "refined_co", 1.0),
                ("mine_ni", "refined_ni", 1.0),
            ] {
                a.push((p.into(), q.into(), x));
            }
            for (p, m) in [
                ("refined_co", "Co"),
                ("refined_ni", "Ni"),
                ("mine_mn", "Mn"),
            ] {
                a.push((
                    p.into(),
                    "pcam".into(),
                    b["kg_kwh"][m].as_f64().unwrap() / val(&b, "pcam_kg_kwh"),
                ));
            }
        }
    }
    if sector == "pv" || sector == "joint" {
        for (p, q, x) in [
            ("polysilicon", "wafer", 2.0),
            ("wafer", "pv_cell", 1.0),
            ("pv_cell", "module", 1.0),
        ] {
            a.push((p.into(), q.into(), x));
        }
    }
    let used: BTreeSet<String> = a.iter().flat_map(|r| [r.0.clone(), r.1.clone()]).collect();
    let mut totals = BTreeMap::<String, f64>::new();
    for r in &nodes {
        *totals
            .entry(r["product"].as_str().unwrap().into())
            .or_default() += val(r, "annual");
    }
    let (mut hhi, mut top) = (
        BTreeMap::<String, f64>::new(),
        BTreeMap::<String, f64>::new(),
    );
    for r in &nodes {
        let p = r["product"].as_str().unwrap();
        let share = val(r, "annual") / totals[p];
        *hhi.entry(p.into()).or_default() += share * share;
        let t = top.entry(p.into()).or_default();
        *t = t.max(share);
    }
    nodes.sort_by(|r, s| {
        (r["product"].as_str(), r["country"].as_str())
            .cmp(&(s["product"].as_str(), s["country"].as_str()))
    });
    let mut selected = vec![];
    let mut coverage = BTreeMap::<String, f64>::new();
    for mut r in nodes {
        let p = r["product"].as_str().unwrap().to_string();
        let share = val(&r, "annual") / totals[&p];
        r["share"] = json!(share);
        if share >= cutoff && used.contains(&p) {
            selected.push(r);
            *coverage.entry(p).or_default() += share;
        }
    }
    let finals: Vec<String> = ["cell", "module"]
        .iter()
        .filter(|p| totals.contains_key(**p))
        .map(|p| p.to_string())
        .collect();
    let mut order: Vec<String> = used
        .iter()
        .filter(|p| !finals.contains(p))
        .cloned()
        .collect();
    order.sort_by_key(|p| depth(p, &a));
    let mut scale: BTreeMap<String, f64> = finals.iter().map(|f| (f.clone(), 1.0)).collect();
    let (mut requirement, mut supply) = (
        BTreeMap::<String, f64>::new(),
        BTreeMap::<String, f64>::new(),
    );
    for _ in 0..2 {
        requirement = finals
            .iter()
            .map(|f| (f.clone(), scale[f] * total(&selected, f)))
            .collect();
        for p in &order {
            let r = sum(a
                .iter()
                .filter(|r| r.0 == *p)
                .map(|(_, q, x)| x * requirement[q]));
            requirement.insert(p.clone(), r);
        }
        if let Some((p, _)) = requirement.iter().find(|(_, r)| **r == 0.0) {
            return Err(format!(
                "Zero requirement for {p}; cutoff or exclusions removed the chain"
            ));
        }
        supply = requirement
            .iter()
            .map(|(p, r)| (p.clone(), total(&selected, p) / r))
            .collect();
        for f in &finals {
            scale.insert(
                f.clone(),
                scale[f] * closure(f, &a).iter().fold(1.0f64, |m, p| m.min(supply[p])),
            );
        }
    }
    for r in &mut selected {
        r["capacity"] =
            json!(val(r, "annual") / (12.0 * requirement[r["product"].as_str().unwrap()]));
    }
    hhi.retain(|p, _| used.contains(p));
    top.retain(|p, _| used.contains(p));
    let mut export_out = BTreeMap::new();
    let mut import_out = BTreeMap::new();
    for c in &iso3 {
        for (p, _) in HS {
            let e = trade(c, p, &exports, 1e-3);
            if e != 0.0 {
                export_out.insert(format!("{c}:{p}"), e);
            }
            import_out.insert(format!("{c}:{p}"), trade(c, p, &imports, 1e-3));
        }
    }
    Ok(
        json!({"sector":sector,"nodes":selected,"a":a,"requirement":requirement,"supply_ratio":supply,"finals":finals,"demand_scale":scale,"annual_totals":totals,"coverage":coverage,"cutoff":cutoff,"hhi":hhi,"top_share":top,"ncm":ncm,"capacity_basis":basis,"excluded":excluded.into_iter().map(|(c,p)|vec![c,p]).collect::<Vec<_>>(),"bom":b,"missing_baci_quantities":missing,"unparsed_usgs":unparsed,"exports":export_out,"imports":import_out}),
    )
}

#[cfg(test)]
mod tests {
    use super::sum;

    #[test]
    fn compensated_sum_retains_small_term() {
        assert_eq!(sum([1e16, 1.0, -1e16]), 1.0);
        assert_eq!(sum([]), 0.0);
    }
}
