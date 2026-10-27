//! Frozen-law risk reproduction. L: exact cut union; m/n: residual failures/draws.
use cut_risk::{Input, sampling, stats};
use sc_model::Model;
use serde_json::{Value, json};
use std::collections::BTreeMap;
use std::time::{Duration, Instant};

pub fn input(network: &Value, law: &Value, cuts: &Value) -> Result<Input, String> {
    let v: Vec<(String, String)> = network["nodes"]
        .as_array()
        .ok_or("Network nodes required")?
        .iter()
        .map(|x| {
            Ok((
                x["country"].as_str().ok_or("Country required")?.to_string(),
                x["product"].as_str().ok_or("Product required")?.to_string(),
            ))
        })
        .collect::<Result<_, String>>()?;
    let law_nodes: Vec<(String, String)> =
        serde_json::from_value(law["nodes"].clone()).map_err(|e| e.to_string())?;
    let probabilities: &Vec<Value> = law["rates"]["p"]
        .as_array()
        .ok_or("Frozen rates.p required")?;
    if probabilities.len() != law_nodes.len() {
        return Err("One frozen onset rate per law node required".into());
    }
    let p = v
        .iter()
        .map(|node| {
            let i = law_nodes
                .iter()
                .position(|x| x == node)
                .ok_or("Network node has no frozen onset rate")?;
            probabilities[i]
                .as_f64()
                .ok_or("Invalid frozen probability")
        })
        .collect::<Result<Vec<_>, _>>()?;
    let rows = cuts
        .get("cuts")
        .unwrap_or(cuts)
        .as_array()
        .ok_or("Cut list required")?;
    let mut dense = vec![];
    for row in rows {
        let row = row.as_array().ok_or("Invalid cut state")?;
        if row.is_empty() || row[0].is_array() {
            let mut d = vec![0; v.len()];
            for pair in row {
                let pair = pair
                    .as_array()
                    .ok_or("Sparse (node,duration) pairs required")?;
                if pair.len() != 2 {
                    return Err("Sparse pair needs node and duration".into());
                }
                let i = pair[0].as_u64().ok_or("Invalid node index")? as usize;
                if i >= v.len() {
                    return Err("Cut node outside network".into());
                }
                d[i] = pair[1].as_i64().ok_or("Invalid outage duration")?;
            }
            dense.push(d);
        } else {
            dense.push(
                serde_json::from_value(Value::Array(row.clone())).map_err(|e| e.to_string())?,
            );
        }
    }
    if let Some(nodes) = cuts.get("nodes") {
        let expected = serde_json::to_value(&v).map_err(|e| e.to_string())?;
        if nodes != &expected {
            return Err("Cut roster differs from selected network".into());
        }
    }
    Ok(Input {
        v,
        p,
        rho: law["rates"]["rho"]
            .as_f64()
            .ok_or("Frozen rates.rho required")?,
        durations: serde_json::from_value(law["durations"]["durations"].clone())
            .map_err(|e| e.to_string())?,
        weights: serde_json::from_value(law["durations"]["weights"].clone())
            .map_err(|e| e.to_string())?,
        cuts: dense,
    })
}

pub fn run(network: &Value, config: &Value, law: &Value, cuts: &Value) -> Result<Value, String> {
    if cuts["complete"] != true {
        return Err("Risk requires a completed native cut search".into());
    }
    if config.get("f").is_some() {
        return Err("Full-outage cuts do not certify a partial-loss probability law".into());
    }
    if cuts["algorithm"] != "capacity_dominance_lattice" || cuts["network"] != *network {
        return Err("Risk requires a native cut certificate for this exact network".into());
    }
    let defaults = json!({"alpha":0.25,"h":0,"sigma":0,"L":6,"T":24,"choice":false,
        "shares":[0,1],"durations":[3,6,12],"aggregate":true,"k":3});
    for (key, default) in defaults.as_object().unwrap() {
        let selected = config.get(key).unwrap_or(default);
        let certified = cuts["config"].get(key).unwrap_or(default);
        let equal = if selected.is_number() && certified.is_number() {
            selected.as_f64() == certified.as_f64()
        } else {
            selected == certified
        };
        if !equal {
            return Err(format!("Cut certificate configuration mismatch: {key}"));
        }
    }
    if config.get("durations").unwrap_or(&defaults["durations"]) != &law["durations"]["durations"] {
        return Err("The frozen law and certified cut duration grids must match".into());
    }
    let k = config["k"].as_u64().unwrap_or(3) as usize;
    let input = input(network, law, cuts)?;
    let bounds = stats::bracket(&input, k, true).map_err(str::to_string)?;
    let lower = bounds["L"].as_f64().unwrap();
    let model = Model::from_network(network, config)?;
    let alpha = config["alpha"].as_f64().unwrap_or(0.25);
    let n = config["n"].as_u64().unwrap_or(4000) as usize;
    let seed = config["seed"].as_u64().unwrap_or(0);
    let seconds = config["time_limit"].as_f64().unwrap_or(60.0);
    if n < 2 || !seconds.is_finite() || seconds <= 0.0 || !(0.0..=1.0).contains(&alpha) {
        return Err("Valid sampling count, threshold and time limit required".into());
    }
    let states = sampling::states(&input, n, seed).map_err(str::to_string)?;
    let start = Instant::now();
    let deadline = start + Duration::from_secs_f64(seconds);
    let mut cache = BTreeMap::new();
    let mut m = 0;
    for (i, state) in states.iter().enumerate() {
        if Instant::now() > deadline {
            return Ok(json!({"status":"limit","complete":false,
            "samples_completed":i,"n":n,"L":lower,"seed":seed,"lp_states":cache.len()}));
        }
        if input
            .cuts
            .iter()
            .any(|cut| state.iter().zip(cut).all(|(d, c)| d >= c))
        {
            continue;
        }
        // The complete search already decided every state of support <= k.
        if state.iter().filter(|&&d| d > 0).count() <= k {
            continue;
        }
        let failed = if let Some(&fail) = cache.get(state) {
            fail
        } else {
            let durations: Vec<f64> = state.iter().map(|&d| d as f64).collect();
            let solved = model.solve(&durations, false, None)?;
            if solved["status"] != "optimal" {
                return Err(format!("Recourse solve: {solved}"));
            }
            let fail = solved["phi"].as_f64().ok_or("Primal objective missing")?
                > alpha * model.total + 1e-7;
            cache.insert(state.clone(), fail);
            fail
        };
        if failed {
            m += 1;
        }
    }
    let r = m as f64 / n as f64;
    let ci = stats::binomial_interval(m, n).map_err(str::to_string)?;
    Ok(
        json!({"status":"optimal","bounds":bounds,"residual":{"L":lower,"estimate":lower+r,
        "se":(r*(1.0-r)/(n-1) as f64).sqrt(),"ci95":[lower+ci[0],(lower+ci[1]).min(1.0)],
        "residual_estimate":r,"residual_events":m,"zero_residuals":m==0,"lp_states":cache.len(),
        "n":n,"seed":seed,"complete":true,"k":k,"method":"lower_bound_plus_residual",
        "interval_method":"clopper_pearson_binomial"},"seconds":start.elapsed().as_secs_f64(),
        "law_source":"supplied_frozen_onset_law","highs":sc_model::version()}),
    )
}
