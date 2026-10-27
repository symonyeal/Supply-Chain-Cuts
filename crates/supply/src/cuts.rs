//! Native lattice enumeration from chokepoint/brute.py, MODEL Lemma B.
//! D: node outage months; p: layer; r: node capacity rank; k: max support.
use sc_model::Model;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::time::{Duration, Instant};

fn minimal(cuts: Vec<Vec<i64>>) -> Vec<Vec<i64>> {
    cuts.iter()
        .filter(|d| {
            !cuts
                .iter()
                .any(|s| s != *d && s.iter().zip(*d).all(|(a, b)| a <= b))
        })
        .cloned()
        .collect()
}
struct Search<'a> {
    model: &'a Model,
    layers: BTreeMap<String, Vec<usize>>,
    ds: Vec<i64>,
    cache: BTreeMap<Vec<i64>, bool>,
    cuts: Vec<Vec<i64>>,
    found: Vec<Vec<i64>>,
    dmax: Vec<i64>,
    theta: f64,
    deadline: Instant,
}
impl Search<'_> {
    fn dominates(&self, d: &[i64]) -> bool {
        self.cuts
            .iter()
            .chain(&self.found)
            .any(|s| s.iter().zip(d).all(|(a, b)| a <= b))
    }
    fn fails(&mut self, d: &[i64]) -> Result<bool, String> {
        if Instant::now() > self.deadline {
            return Err("time_limit".into());
        }
        if self.dominates(d) {
            return Ok(true);
        }
        if let Some(&v) = self.cache.get(d) {
            return Ok(v);
        }
        let state: Vec<f64> = d.iter().map(|&x| x as f64).collect();
        let result = self.model.solve(&state, false, None)?;
        if result["status"] != "optimal" {
            return Err(format!("Recourse solve: {result}"));
        }
        let fail = result["phi"].as_f64().ok_or("Missing primal objective")? > self.theta + 1e-7;
        self.cache.insert(d.to_vec(), fail);
        Ok(fail)
    }
    fn completions(&self, e: &[i64], later: &[String], p: &str, r: usize) -> Vec<Vec<i64>> {
        let mut base = e.to_vec();
        let mut used = BTreeMap::from([(p.to_string(), r as isize)]);
        let mut options: Vec<Vec<(usize, i64)>> = vec![vec![]];
        for q in later {
            if q != p && later.iter().filter(|x| *x == q).count() == 1 {
                let mut best = 0;
                let mut chain = vec![];
                for &v in &self.layers[q] {
                    if self.dmax[v] > best {
                        best = self.dmax[v];
                        chain.push((v, best));
                    }
                }
                options = options
                    .iter()
                    .flat_map(|o| {
                        chain.iter().map(move |&x| {
                            let mut z = o.clone();
                            z.push(x);
                            z
                        })
                    })
                    .collect();
            } else {
                let rank = used.entry(q.clone()).or_insert(-1);
                *rank += 1;
                base[self.layers[q][*rank as usize]] = *self.ds.last().unwrap();
            }
        }
        options
            .iter()
            .map(|o| {
                let mut d = base.clone();
                for &(v, t) in o {
                    d[v] = t;
                }
                d
            })
            .collect()
    }
    fn visit(
        &mut self,
        pattern: &[String],
        d: &[i64],
        i: usize,
        prev: isize,
    ) -> Result<(), String> {
        let p = &pattern[i];
        let later = &pattern[i + 1..];
        let mut bound = 0;
        let stop = self.layers[p].len() - later.iter().filter(|q| *q == p).count();
        for r in (prev + 1) as usize..stop {
            let v = self.layers[p][r];
            let durations: Vec<i64> = self
                .ds
                .iter()
                .copied()
                .filter(|&x| bound < x && x <= self.dmax[v])
                .rev()
                .collect();
            for t in durations {
                let mut e = d.to_vec();
                e[v] = t;
                if self.dominates(&e) {
                    continue;
                }
                let mut failure = false;
                for c in self.completions(&e, later, p, r) {
                    if self.fails(&c)? {
                        failure = true;
                        break;
                    }
                }
                if !failure {
                    bound = t;
                    break;
                }
                if later.is_empty() {
                    self.found.push(e);
                } else {
                    self.visit(
                        pattern,
                        &e,
                        i + 1,
                        if later[0] == *p { r as isize } else { -1 },
                    )?;
                }
            }
        }
        Ok(())
    }
}
fn patterns(
    names: &[String],
    k: usize,
    start: usize,
    current: &mut Vec<String>,
    out: &mut Vec<Vec<String>>,
) {
    if current.len() == k {
        out.push(current.clone());
        return;
    }
    for i in start..names.len() {
        current.push(names[i].clone());
        patterns(names, k, i, current, out);
        current.pop();
    }
}

pub fn enumerate(network: &Value, config: &Value) -> Result<Value, String> {
    if config.get("f").is_some() {
        return Err(
            "Cut enumeration currently certifies full outages; use evaluate for partial losses"
                .into(),
        );
    }
    let model = Model::from_network(network, config)?;
    let n = model.v.len();
    let alpha = config["alpha"].as_f64().unwrap_or(0.25);
    let k = config["k"].as_u64().unwrap_or(3) as usize;
    let seconds = config["time_limit"].as_f64().unwrap_or(60.0);
    if !(0.0..=1.0).contains(&alpha) || !seconds.is_finite() || seconds <= 0.0 {
        return Err("Invalid threshold/time limit".into());
    }
    let ds: Vec<i64> = config["durations"]
        .as_array()
        .map(|a| a.iter().filter_map(Value::as_i64).collect())
        .unwrap_or(vec![3, 6, 12]);
    let ds: Vec<i64> = ds
        .into_iter()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    if ds.is_empty()
        || ds
            .iter()
            .any(|&d| d <= 0 || !model.ends.contains(&(d as usize)))
    {
        return Err("Durations must be positive model block ends".into());
    }
    let nodes = network["nodes"].as_array().ok_or("Missing network nodes")?;
    let mut order: Vec<usize> = (0..n).collect();
    order.sort_by(|&a, &b| {
        model.v[a]
            .1
            .cmp(&model.v[b].1)
            .then_with(|| {
                nodes[b]["capacity"]
                    .as_f64()
                    .unwrap()
                    .total_cmp(&nodes[a]["capacity"].as_f64().unwrap())
            })
            .then(a.cmp(&b))
    });
    let mut layers: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for v in order {
        layers.entry(model.v[v].1.clone()).or_default().push(v);
    }
    let start = Instant::now();
    let mut search = Search {
        model: &model,
        layers,
        ds: ds.clone(),
        cache: BTreeMap::new(),
        cuts: vec![],
        found: vec![],
        dmax: vec![*ds.last().unwrap(); n],
        theta: alpha * model.total,
        deadline: start + Duration::from_secs_f64(seconds),
    };
    if search.fails(&vec![0; n])? {
        search.cuts.push(vec![0; n]);
    } else {
        let names: Vec<String> = search.layers.keys().cloned().collect();
        for support in 1..=k.min(n) {
            search.found.clear();
            let mut all = vec![];
            patterns(&names, support, 0, &mut vec![], &mut all);
            for pattern in all {
                if pattern
                    .iter()
                    .any(|p| pattern.iter().filter(|q| *q == p).count() > search.layers[p].len())
                {
                    continue;
                }
                if let Err(error) = search.visit(&pattern, &vec![0; n], 0, -1) {
                    if error == "time_limit" {
                        return Ok(json!({"complete":false,"status":"limit",
                        "candidate_failing_states":minimal([search.cuts,search.found].concat()),
                        "lp_calls":search.cache.len(),"seconds":start.elapsed().as_secs_f64()}));
                    }
                    return Err(error);
                }
            }
            search.cuts = minimal([search.cuts, search.found.clone()].concat());
            if support == 1 {
                for s in &search.cuts {
                    let v = s.iter().position(|&d| d > 0).unwrap();
                    search.dmax[v] = ds.iter().copied().filter(|&d| d < s[v]).max().unwrap_or(0);
                }
            }
        }
    }
    search.cuts.sort();
    let mut certificates = vec![];
    for d in &search.cuts {
        let state: Vec<f64> = d.iter().map(|&x| x as f64).collect();
        let solved = model.solve(&state, true, None)?;
        if solved["status"] != "optimal" {
            return Err(format!("Cut certificate solve: {solved}"));
        }
        if solved["phi"].as_f64().ok_or("Missing primal objective")? <= search.theta + 1e-7
            || solved["gap"].as_f64().ok_or("Missing dual gap")? > 1e-6
        {
            return Err("Invalid failing-state or dual-gap certificate".into());
        }
        let mut pred = vec![];
        for (v, &t) in d.iter().enumerate().filter(|(_, d)| **d > 0) {
            let previous = ds.iter().copied().filter(|&x| x < t).max().unwrap_or(0);
            let mut p = state.clone();
            p[v] = previous as f64;
            let solved = model.solve(&p, false, None)?;
            if solved["status"] != "optimal"
                || solved["phi"].as_f64().unwrap() > search.theta + 1e-7
            {
                return Err("Nonminimal cut certificate".into());
            }
            pred.push(json!({"v":v,"D":previous,"phi":solved["phi"]}));
        }
        certificates.push(json!({"state":d,"phi":solved["phi"],"dual":solved["dual"],"gap":solved["gap"],"predecessors":pred}));
    }
    Ok(
        json!({"complete":true,"status":"optimal","algorithm":"capacity_dominance_lattice",
        "network":network,
        "nodes":model.v,"cuts":search.cuts,"certificates":certificates,"config":config,
        "total":model.total,"lp_calls":search.cache.len(),"seconds":start.elapsed().as_secs_f64()}),
    )
}
