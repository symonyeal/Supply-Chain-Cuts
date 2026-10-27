// V: country/product nodes; S: sparse cut; C: certificate map; R: cut bundle.
// N: sector network; L/U: probability bounds; D: outage months; w: duration masses.
// x: one configuration; p: predecessor; phi: least cumulative shortfall.
use serde_json::{Map, Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

macro_rules! check {
    ($ok:expr, $msg:expr) => {
        let valid: bool = $ok;
        if !valid {
            return Err($msg.to_string());
        }
    };
}

fn read(p: &Path) -> Result<Value, String> {
    let text = fs::read_to_string(p).map_err(|e| format!("{}: {e}", p.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("{}: {e}", p.display()))
}
fn a(x: &Value) -> &[Value] {
    x.as_array().map(Vec::as_slice).unwrap_or(&[])
}
fn obj(x: &Value) -> Result<&Map<String, Value>, String> {
    x.as_object().ok_or_else(|| "Expected object".to_string())
}
fn f(x: &Value) -> f64 {
    x.as_f64().unwrap_or(f64::NAN)
}
fn s(x: &Value) -> &str {
    x.as_str().unwrap_or("")
}
fn b(x: &Value) -> bool {
    x.as_bool().unwrap_or(false)
}
fn len(x: &Value) -> usize {
    a(x).len()
}
fn select(x: &Value, keys: &[&str]) -> Value {
    Value::Object(
        keys.iter()
            .map(|k| (k.to_string(), x[*k].clone()))
            .collect(),
    )
}
fn close(x: f64, y: f64) -> bool {
    (x - y).abs() <= 1e-9 * x.abs().max(y.abs())
}
fn files(p: &Path) -> Result<Vec<PathBuf>, String> {
    let mut out = fs::read_dir(p)
        .map_err(|e| e.to_string())?
        .map(|e| e.map(|v| v.path()).map_err(|e| e.to_string()))
        .collect::<Result<Vec<_>, _>>()?;
    out.retain(|p| p.extension().is_some_and(|x| x == "json"));
    out.sort();
    Ok(out)
}

/// Round only at the presentation boundary, to five significant decimal digits.
pub fn plain(x: Value) -> Value {
    match x {
        Value::Object(m) => Value::Object(m.into_iter().map(|(k, v)| (k, plain(v))).collect()),
        Value::Array(v) => Value::Array(v.into_iter().map(plain).collect()),
        Value::Number(ref n) if n.is_f64() => {
            // Scientific formatting gives the same ties-to-even significant-digit operation.
            let z = format!("{:.4e}", n.as_f64().unwrap())
                .parse::<f64>()
                .unwrap();
            json!(z)
        }
        _ => x,
    }
}

fn cut_key(x: &Value) -> String {
    serde_json::to_string(x).unwrap()
}
fn certificates(r: &Value) -> Result<BTreeMap<String, Value>, String> {
    let mut out = BTreeMap::new();
    for c in a(&r["certificates"]) {
        let mut coords = Vec::new();
        for p in a(&c["predecessors"]) {
            let d = match p["D"].as_i64() {
                Some(0) => 3,
                Some(3) => 6,
                Some(6) => 12,
                _ => return Err("Invalid predecessor duration".into()),
            };
            let v = p["v"].as_i64().ok_or("Invalid predecessor node")?;
            coords.push((v, d));
        }
        coords.sort();
        out.insert(cut_key(&json!(coords)), c.clone());
    }
    let keys: BTreeSet<_> = a(&r["cuts"]).iter().map(cut_key).collect();
    check!(
        out.keys().cloned().collect::<BTreeSet<_>>() == keys,
        "Cut/predecessor certificate coverage differs"
    );
    Ok(out)
}

fn witness(c: &Value, total: f64) -> Value {
    Value::Array(
        a(&c["predecessors"])
            .iter()
            .map(|p| json!([p["v"], p["D"], f(&p["phi"]) / total]))
            .collect(),
    )
}

fn country_union(law: &Value, cuts: &Value, dj: i64, l: f64) -> Result<Value, String> {
    let v: Vec<(String, String)> =
        serde_json::from_value(law["nodes"].clone()).map_err(|e| e.to_string())?;
    let probabilities: Vec<f64> =
        serde_json::from_value(law["rates"]["p"].clone()).map_err(|e| e.to_string())?;
    check!(
        len(&law["durations"]["weights"]) == 3,
        "Expected three duration weights"
    );
    let durations: Vec<i64> = [3, 6, 12].into_iter().filter(|d| *d <= dj).collect();
    let weights: Vec<f64> = durations
        .iter()
        .map(|e| {
            [3_i64, 6, 12]
                .iter()
                .zip(a(&law["durations"]["weights"]))
                .filter(|(d, _)| (**d).min(dj) == *e)
                .map(|(_, w)| f(w))
                .sum()
        })
        .collect();
    let mut countries = BTreeSet::new();
    let mut sparse = Vec::new();
    for cut in a(cuts) {
        let coords: Vec<(usize, i64)> =
            serde_json::from_value(cut.clone()).map_err(|e| e.to_string())?;
        for &(i, _) in &coords {
            check!(i < v.len(), "Cut node out of range");
            countries.insert(v[i].0.clone());
        }
        sparse.push(coords);
    }
    let mut out = Map::new();
    for country in countries {
        let dense = sparse
            .iter()
            .filter(|cut| cut.iter().any(|&(i, _)| v[i].0 == country))
            .map(|cut| {
                let mut row = vec![0; v.len()];
                for &(i, d) in cut {
                    row[i] = d;
                }
                row
            })
            .collect();
        let z = cut_risk::exact_union(cut_risk::Input {
            v: v.clone(),
            p: probabilities.clone(),
            rho: f(&law["rates"]["rho"]),
            durations: durations.clone(),
            weights: weights.clone(),
            cuts: dense,
        })
        .map_err(str::to_string)?
            / l;
        check!(
            (0.0..=1.0 + 1e-9).contains(&z),
            "Country union outside [0,1]"
        );
        out.insert(country, json!(z));
    }
    Ok(Value::Object(out))
}

fn block(root: &Path, run: &str) -> Result<(Value, Value, Value, Value), String> {
    let d = root.join("results").join(run);
    let net = read(&d.join("network.json"))?;
    let checks = read(&d.join("data_checks.json"))?;
    let risk = read(&d.join("risk.json"))?;
    let n = &net[s(&risk["sector"])];
    check!(
        risk["nodes"]
            == Value::Array(
                a(&n["nodes"])
                    .iter()
                    .map(|x| json!([x["country"], x["product"]]))
                    .collect()
            ),
        "Network roster differs"
    );
    let mut cuts = BTreeMap::new();
    for path in files(&d.join("cuts"))? {
        let r = read(&path)?;
        check!(
            a(&r["certificates"]).iter().all(|c| b(&c["certified"])),
            "Uncertified cut"
        );
        if !r["pruned"].is_null() {
            let p = &r["pruned"];
            check!(
                b(&p["brute_equals_lattice"])
                    && (b(&p["milp_equals_brute"]) || !b(&p["milp_complete"])),
                "Pruned disagreement"
            );
        }
        if !r["milp_full"].is_null() {
            check!(
                b(&r["milp_full"]["equals_lattice"]) || !b(&r["milp_full"]["complete"]),
                "Full MILP disagreement"
            );
        }
        if !r["brute_full"].is_null() {
            check!(
                b(&r["brute_full"]["equals_lattice"]),
                "Full brute disagreement"
            );
        }
        cuts.insert(path.file_stem().unwrap().to_string_lossy().into_owned(), r);
    }
    let mut configs = Map::new();
    for (key, x) in obj(&risk["configs"])? {
        check!(
            0.0 <= f(&x["L"]) && f(&x["L"]) <= f(&x["U"]) && f(&x["U"]) <= 1.0,
            "Invalid probability bracket"
        );
        let task = key
            .rsplit_once('_')
            .ok_or("Configuration missing duration")?
            .0;
        let r = cuts
            .get(task)
            .ok_or_else(|| format!("Missing task {task}"))?;
        let cert = certificates(r)?;
        let mut phi = Vec::new();
        let mut predecessors = Vec::new();
        for cut in a(&x["cuts"]) {
            let c = cert.get(&cut_key(cut)).ok_or("Missing cut certificate")?;
            check!(
                len(&c["predecessors"]) == len(cut),
                "Predecessor count differs"
            );
            check!(
                a(&c["predecessors"])
                    .iter()
                    .all(|p| f(&p["phi"]) <= f(&r["theta"]) + 1e-7),
                "Predecessor exceeds failure threshold"
            );
            phi.push(f(&c["phi"]) / f(&r["total"]));
            predecessors.push(witness(c, f(&r["total"])));
        }
        let mut out = select(x, &["L", "U", "cuts", "attribution"]);
        out["phi"] = json!(phi);
        out["predecessors"] = json!(predecessors);
        out["country_union"] = country_union(
            &risk,
            &x["cuts"],
            x["DJ"].as_i64().ok_or("Invalid maximum outage")?,
            f(&x["L"]),
        )?;
        configs.insert(key.replace("base_", ""), out);
    }
    let head = &configs["a0.25_h0_s0_L6_D12"]["country_union"];
    check!(
        obj(&risk["attribution"]["country_union"])?
            .iter()
            .all(|(c, z)| close(f(&head[c]), f(z))),
        "Saved headline country unions differ"
    );
    let mut nodes = Map::new();
    for key in ["country", "product"] {
        let i = if key == "country" { 0 } else { 1 };
        nodes.insert(
            key.into(),
            Value::Array(a(&risk["nodes"]).iter().map(|v| v[i].clone()).collect()),
        );
    }
    for key in ["basis", "share", "annual", "unit", "source"] {
        nodes.insert(
            key.into(),
            Value::Array(a(&n["nodes"]).iter().map(|v| v[key].clone()).collect()),
        );
    }
    nodes.insert(
        "years".into(),
        Value::Array(
            a(&n["nodes"])
                .iter()
                .map(|v| json!(12.0 * f(&v["capacity"])))
                .collect(),
        ),
    );
    for key in ["p", "exposure", "onsets"] {
        nodes.insert(key.into(), risk["rates"][key].clone());
    }
    let mut estimates = Map::new();
    for (alpha, e) in obj(&risk["residual"])? {
        let alpha = alpha.parse::<f64>().map_err(|e| e.to_string())?.to_string();
        let c = &risk["configs"][format!("base_a{alpha}_h0_s0_L6_D12")];
        check!(
            e["method"] == "lower_bound_plus_residual"
                && e["interval_method"] == "clopper_pearson_binomial",
            "Wrong residual estimator"
        );
        check!(
            e["L"] == c["L"] && f(&e["estimate"]) >= f(&c["L"]),
            "Residual below bound"
        );
        check!(
            close(
                f(&e["estimate"]),
                f(&e["L"]) + f(&e["residual_events"]) / f(&e["n"])
            ),
            "Residual estimate inconsistent"
        );
        check!(
            f(&e["ci95"][0]) <= f(&c["U"]) && f(&e["ci95"][1]) >= f(&c["L"]),
            "Residual interval misses bracket"
        );
        check!(
            !b(&e["zero_residuals"]) || f(&e["ci95"][1]) > f(&e["L"]),
            "Zero residual has zero-width interval"
        );
        estimates.insert(
            alpha.clone(),
            json!({"IS":risk["IS"][&alpha],"MC":risk["MC"][&alpha],
            "residual":risk["residual"][&alpha]}),
        );
    }
    let out = json!({"meta":{"run":run,"revision":risk["stamp"]["revision"],
        "lock":risk["stamp"]["lock_sha256"],"rho":risk["rates"]["rho"],
        "durations":risk["durations"],"D1":risk["D1"]},"nodes":nodes,"configs":configs,
        "estimates":estimates,"attribution":risk["attribution"]});
    Ok((out, n.clone(), risk, checks))
}

fn chemistry(
    root: &Path,
    sector: &str,
    reference: &Value,
    law: &Value,
    cut_run: &str,
    risk_run: &str,
) -> Result<Value, String> {
    let d = root.join("results");
    let risk = read(&d.join(risk_run).join(format!("{sector}.json")))?;
    check!(
        !b(&risk["stamp"]["dirty"]) && b(&risk["network_unchanged"]) && b(&risk["rates_unchanged"]),
        "Chemistry changed frozen network/rates"
    );
    let mut configs = Map::new();
    for (key, x) in obj(&risk["configs"])? {
        let (task, dj) = key
            .rsplit_once("_D")
            .ok_or("Invalid chemistry configuration")?;
        let dj = dj.parse::<i64>().map_err(|e| e.to_string())?;
        let r = read(
            &d.join(cut_run)
                .join("cuts")
                .join(format!("{sector}_free_{task}.json")),
        )?;
        let bounded = read(
            &d.join(cut_run)
                .join("cuts")
                .join(format!("{sector}_bounded_{task}.json")),
        )?;
        check!(
            b(&r["complete"]) && b(&bounded["complete"]) && r["cuts"] == bounded["cuts"],
            "Chemistry free/bounded lists differ or are incomplete"
        );
        check!(
            !b(&r["stamp"]["dirty"]) && r["nodes"] == law["nodes"],
            "Dirty chemistry or roster differs"
        );
        let cert = certificates(&r)?;
        let cuts = Value::Array(
            a(&r["cuts"])
                .iter()
                .filter(|cut| {
                    a(cut)
                        .iter()
                        .all(|p| p[1].as_i64().is_some_and(|t| t <= dj))
                })
                .cloned()
                .collect(),
        );
        check!(
            len(&cuts) == len(&x["attribution"]),
            "Chemistry attribution count differs"
        );
        let mut phi = Vec::new();
        let mut predecessors = Vec::new();
        for cut in a(&cuts) {
            let c = cert.get(&cut_key(cut)).ok_or("Missing chemistry witness")?;
            let theta = f(&r["config"]["alpha"]) * f(&r["total"]);
            check!(
                b(&c["certified"]) && f(&c["gap"]) <= 1e-6,
                "Uncertified chemistry cut"
            );
            check!(f(&c["phi"]) > theta + 1e-7, "Chemistry cut does not fail");
            check!(
                a(&c["predecessors"])
                    .iter()
                    .all(|p| f(&p["phi"]) <= theta + 1e-7),
                "Chemistry predecessor fails"
            );
            phi.push(f(&c["phi"]) / f(&r["total"]));
            predecessors.push(witness(c, f(&r["total"])));
        }
        let union = country_union(law, &cuts, dj, f(&x["L"]))?;
        let mut out = x.clone();
        out["cuts"] = cuts;
        out["country_union"] = union;
        out["phi"] = json!(phi);
        out["predecessors"] = json!(predecessors);
        configs.insert(key.clone(), out);
    }
    for (alpha, e) in obj(&risk["residual"])? {
        let c = &configs[&format!("a{alpha}_h0_s0_L6_D12")];
        check!(
            e["L"] == c["L"] && f(&e["L"]) <= f(&e["estimate"]),
            "Chemistry residual below L"
        );
        check!(
            f(&e["ci95"][0]) <= f(&e["estimate"]) && f(&e["estimate"]) <= f(&e["ci95"][1]),
            "Chemistry residual outside interval"
        );
    }
    Ok(
        json!({"nodes":reference["nodes"],"configs":configs,"residual":risk["residual"],
        "meta":{"cut_run":cut_run,"risk_run":risk_run,"revision":risk["stamp"]["revision"]}}),
    )
}

fn severity(root: &Path, run: &str) -> Result<Value, String> {
    let d = root.join("results").join(run);
    let t = read(&d.join("severity.json"))?;
    check!(
        b(&t["registered"]) && !b(&t["stamp"]["dirty"]),
        "Unregistered/dirty severity"
    );
    let mut out = select(&t, &["table", "excluded", "method", "bootstrap_draws"]);
    out["run"] = json!(run);
    out["sectors"] = json!({});
    for sector in ["liion", "pv", "joint"] {
        let x = read(&d.join(format!("{sector}.json")))?;
        check!(
            x["status"] == "optimal" && !b(&x["stamp"]["dirty"]),
            "Severity not clean/optimal"
        );
        check!(
            b(&x["monotone"])
                && b(&x["full_agrees_with_W1"])
                && f(&x["max_monotonicity_violation"]) <= 1e-7,
            "Severity monotonicity/W1 mismatch"
        );
        check!(
            obj(&x["assigned_fractions"])?.values().all(|row| row
                .as_object()
                .is_some_and(|v| v.values().all(|z| (0.0..=1.0).contains(&f(z))))),
            "Severity fractions outside [0,1]"
        );
        let same = obj(&x["onsets_by_measure"])?.keys().all(|m| {
            x["assigned_fractions"]["central"]
                .get(m)
                .is_none_or(|z| f(z) == 1.0)
        });
        check!(
            !same || x["scenarios"]["central"]["failures"] == x["scenarios"]["full"]["failures"],
            "Full severity fallback changes failures"
        );
        out["sectors"][sector] = select(
            &x,
            &[
                "scenarios",
                "full_outage",
                "hard",
                "S3",
                "unidentified_onset_share",
                "n",
            ],
        );
        out["sectors"][sector]["same_as_full"] = json!(same);
    }
    Ok(out)
}

fn supply(root: &Path, run: &str) -> Result<Value, String> {
    let mut out = Vec::new();
    let mut revisions = BTreeSet::new();
    for path in files(&root.join("results").join(run))? {
        let x = read(&path)?;
        check!(
            b(&x["complete"]) && !b(&x["stamp"]["dirty"]),
            "Supply incomplete/dirty"
        );
        check!(
            a(&x["certificates"])
                .iter()
                .all(|c| b(&c["certified"]) && f(&c["gap"]) <= 1e-6),
            "Supply cut uncertified"
        );
        check!(
            x["baseline"]["status"] == "optimal" && f(&x["baseline"]["gap"]) <= 1e-6,
            "Supply baseline not optimal"
        );
        revisions.insert(s(&x["stamp"]["revision"]).to_string());
        check!(
            f(&x["baseline_share"]) <= 0.25 || x["cuts"] == json!([[]]),
            "Failed supply baseline has no empty cut"
        );
        out.push(
            json!({"case":x["case"],"choice":x["flexible"],"nodes":len(&x["network"]["nodes"]),
            "cuts":len(&x["cuts"]),"singletons":a(&x["cuts"]).iter().filter(|c| len(c)==1).count(),
            "baseline":x["baseline_share"],"vanish":len(&x["vanish"]),"appear":len(&x["appear"])}),
        );
    }
    check!(
        out.len() == 14 && revisions.len() == 1,
        "Supply case/revision count differs"
    );
    Ok(json!({"run":run,"revision":revisions.first(),"cases":out}))
}

fn pc(x: &Value) -> String {
    if x.is_null() {
        "–".into()
    } else {
        format!("{:.1}%", 100.0 * f(x))
    }
}
fn py_round2(x: &Value) -> String {
    if x.is_null() {
        "None".into()
    } else {
        let z = format!("{:.2}", f(x)).parse::<f64>().unwrap();
        let text = z.to_string();
        if text.contains('.') {
            text
        } else {
            format!("{text}.0")
        }
    }
}
fn test_rows(t: &Value) -> Result<Value, String> {
    let h1 = &t["H1_china_graphite_singleton"];
    let h2 = &t["H2_china_midstream_share_of_L"];
    let h3 = &t["H3_annual_failure"];
    let a1 = &t["A1_spearman"];
    let d1 = &t["D1_prequential"];
    let est = &h3["residual"];
    let b2 = &t["B2_capacity_basis"]["a0.25"];
    let b1 = &t["B1_reexport"];
    let single = if a(&h1["durations"]).is_empty() {
        "no".into()
    } else {
        a(&h1["durations"])
            .iter()
            .map(Value::to_string)
            .collect::<Vec<_>>()
            .join(", ")
    };
    let c1 = obj(&t["C1_chemistry"])?
        .iter()
        .filter(|(k, _)| k.ends_with("a0.25"))
        .map(|(k, v)| {
            format!(
                "NCM {}: {} vanish",
                &k.split('_').next().unwrap()[3..],
                len(&v["vanish_co_ni"])
            )
        })
        .collect::<Vec<_>>()
        .join("; ");
    let r1 = format!("singleton at {single} months; a 6-month loss cannot exceed 25% of 24 months");
    let r2 = format!(
        "{} (pCAM, CAM, AAM); secondary: with refined chemicals {}, and graphite {}",
        pc(&h2["midstream"]),
        pc(&h2["with_refined"]),
        pc(&h2["with_refined_and_graphite"])
    );
    let r3 = format!(
        "L = {}, U = {}, L + residual {} [{}, {}]",
        pc(&h3["L"]),
        pc(&h3["U"]),
        pc(&est["estimate"]),
        pc(&est["ci95"][0]),
        pc(&est["ci95"][1])
    );
    let ra = format!(
        "ρ_S = {} with HHI, {} with top share",
        py_round2(&a1["hhi"]),
        py_round2(&a1["top_share"])
    );
    let rb2 = format!(
        "α = 25%: {} vanish, {} appear",
        len(&b2["vanish"]),
        len(&b2["appear"])
    );
    let rb1 = format!(
        "{} cut set rests on a flagged node; in the rerun {} vanish and {} appear at α = 25%, because removing flagged cells lowers demand by {} and moves near-threshold combinations",
        len(&b1["withdrawn"]),
        len(&b1["a0.25"]["vanish"]),
        len(&b1["a0.25"]["appear"]),
        pc(&json!(1.0 - f(&b1["demand_ratio"])))
    );
    let rd1 = format!(
        "model {:.3} vs constant {:.3} on {} node-years, 2020–2024",
        f(&d1["model_log_loss"]),
        f(&d1["constant_log_loss"]),
        d1["test_node_years"]
    );
    let conc = f(&a1["hhi"]).max(f(&a1["top_share"])) >= 0.9;
    Ok(json!([
        [
            "Day-1 (i)",
            "China graphite is a singleton cut at α = 25%, D ≥ 6 months",
            r1,
            if h1["durations"] == json!([12]) {
                "6-month part rejected; 12-month part holds"
            } else {
                "killed"
            }
        ],
        [
            "Day-1 (ii)",
            "cut sets with a Chinese midstream node carry ≥ 80% of L",
            r2,
            if f(&h2["midstream"]) >= 0.8 {
                "holds"
            } else {
                "killed"
            }
        ],
        [
            "Day-1 (iii)",
            "annual P(fail) in [1%, 10%]",
            r3,
            if f(&h3["L"]) > 0.10 || f(&est["ci95"][1]) < 0.01 {
                "killed"
            } else {
                "holds"
            }
        ],
        [
            "A1",
            "Spearman(attribution, concentration) ≥ 0.9 ⇒ concentration suffices",
            ra,
            if conc {
                "killed: concentration suffices"
            } else {
                "survives: the network adds information"
            }
        ],
        [
            "B1",
            "cut sets that disappear without re-export nodes are withdrawn",
            rb1,
            "applied"
        ],
        [
            "B2",
            "cut sets that change on the trade basis are basis-dependent",
            rb2,
            "applied"
        ],
        [
            "C1",
            "Co/Ni cut sets that vanish at some NCM share are conditional on the mix",
            c1,
            "applied"
        ],
        [
            "D1",
            "no out-of-sample log-loss gain ⇒ probabilities are scenarios",
            rd1,
            if b(&d1["improves"]) {
                "survives: rates predict"
            } else {
                "killed: probabilities are scenarios"
            }
        ],
        [
            "E1",
            "tornado over α, D, h, σ, L",
            "see the controls above",
            "no kill condition"
        ]
    ]))
}

/// Assemble certified model exhibits from immutable result bundles, before presentation rounding.
pub fn build(root: &Path, runs: &[String]) -> Result<Value, String> {
    check!(
        !runs.is_empty() && runs.len() <= 4,
        "Expected LIION_RUN [PV_RUN JOINT_RUN SEVERITY_RUN]"
    );
    let (mut data, n, risk, checks) = block(root, &runs[0])?;
    let mut layers: Vec<String> = obj(&n["supply_ratio"])?.keys().cloned().collect();
    layers.sort_by(|p, q| {
        f(n["hhi"].get(q).unwrap_or(&json!(0))).total_cmp(&f(n["hhi"].get(p).unwrap_or(&json!(0))))
    });
    data["layers"] = json!({"product":layers,"S":layers.iter().map(|p| n["supply_ratio"][p].clone()).collect::<Vec<_>>(),
        "hhi":layers.iter().map(|p| n["hhi"][p].clone()).collect::<Vec<_>>(),
        "top":layers.iter().map(|p| n["top_share"][p].clone()).collect::<Vec<_>>()});
    data["tests"] = risk["tests"].clone();
    data["testRows"] = test_rows(&risk["tests"])?;
    data["hard"] = select(&risk["hard"], &["L", "U", "IS", "residual"]);
    data["hazards"] = risk["hazards"].clone();
    data["checks"] = select(
        &checks,
        &["exports_vs_production", "reexport_flags", "site_coverage"],
    );
    if runs.len() > 1 {
        data["pv"] = block(root, &runs[1])?.0;
    }
    let mut joint_law = None;
    if runs.len() > 2 {
        let (joint, _, law, _) = block(root, &runs[2])?;
        data["joint"] = joint;
        joint_law = Some(law);
    }
    if runs.len() > 3 {
        data["severity"] = severity(root, &runs[3])?;
    }
    data["choice"] = chemistry(
        root,
        "liion",
        &data,
        &risk,
        "chemistry-896581f",
        "chemistry-risk-d18c743",
    )?;
    data["supply"] = supply(root, "supply-4ae36c1")?;
    if let Some(law) = joint_law {
        data["joint_choice"] = chemistry(
            root,
            "joint",
            &data["joint"],
            &law,
            "chemistry-896581f",
            "chemistry-risk-d18c743",
        )?;
    }
    let ranges: Vec<(&str, Vec<String>)> = vec![
        (
            "Threshold α = 10–50%",
            ["0.1", "0.25", "0.5"]
                .iter()
                .map(|a| format!("a{a}_h0_s0_L6_D12"))
                .collect(),
        ),
        (
            "Longest outage = 3–12 mo",
            [3, 6, 12]
                .iter()
                .map(|d| format!("a0.25_h0_s0_L6_D{d}"))
                .collect(),
        ),
        (
            "Stock h = 0–3 mo",
            [0, 1, 3]
                .iter()
                .map(|h| format!("a0.25_h{h}_s0_L6_D12"))
                .collect(),
        ),
        (
            "Spare σ = 0–0.5",
            ["0", "0.1", "0.5"]
                .iter()
                .map(|s| format!("a0.25_h0_s{s}_L6_D12"))
                .collect(),
        ),
        (
            "Ramp = 6–24 mo (σ = 0.5)",
            [6, 24]
                .iter()
                .map(|t| format!("a0.25_h0_s0.5_L{t}_D12"))
                .collect(),
        ),
    ];
    let mut sensitivity: Vec<Value> = ranges
        .into_iter()
        .map(|(label, keys)| {
            let values: Vec<Value> = keys
                .iter()
                .map(|k| data["configs"][k]["L"].clone())
                .collect();
            json!({"label":label,"configs":keys,"values":values})
        })
        .collect();
    let spread = |r: &Value| {
        a(&r["values"])
            .iter()
            .map(f)
            .fold(f64::NEG_INFINITY, f64::max)
            - a(&r["values"]).iter().map(f).fold(f64::INFINITY, f64::min)
    };
    sensitivity.sort_by(|a, b| spread(b).total_cmp(&spread(a)));
    data["sensitivity"] = json!(sensitivity);
    Ok(data)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recovered_coordinates_join_witnesses_instead_of_enumeration_order() {
        let r = json!({"cuts":[[[0,3]],[[1,12]]],"certificates":[
            {"predecessors":[{"v":1,"D":6}],"phi":12},
            {"predecessors":[{"v":0,"D":0}],"phi":3}]});
        let cert = certificates(&r).unwrap();
        assert_eq!(cert[&cut_key(&r["cuts"][0])]["phi"], 3);
        assert_eq!(cert[&cut_key(&r["cuts"][1])]["phi"], 12);
        let mut bad = r;
        bad["certificates"][0]["predecessors"][0]["D"] = json!(3);
        assert!(certificates(&bad).is_err());
    }

    #[test]
    fn presentation_rounding_preserves_integer_and_zero_semantics() {
        assert_eq!(
            plain(json!([0.1234567, 123456.7, 0.00001234567, 1])),
            json!([0.12346, 123460.0, 0.000012346, 1])
        );
        assert_eq!(f(&plain(json!(-0.0))).to_bits(), (-0.0_f64).to_bits());
        assert_eq!(pc(&Value::Null), "–");
        assert_eq!(py_round2(&json!(0.5)), "0.5");
        assert_eq!(py_round2(&json!(1.0)), "1.0");
    }
}
