//! Native lattice enumeration from chokepoint/brute.py, MODEL Lemma B.
//! D: node outage months; p: layer; r: node capacity rank; k: max support.
use sc_model::{Model, certified_failure, survives};
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
        let fail = self.model.fails(&state, self.theta)?;
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
    /// Minimal failing states of support <= k over n nodes, support by support (Lemma B):
    /// true when complete, false at the time limit with the candidates left in cuts and found.
    fn lattice(&mut self, k: usize, n: usize) -> Result<bool, String> {
        if self.fails(&vec![0; n])? {
            self.cuts.push(vec![0; n]);
            return Ok(true);
        }
        let names: Vec<String> = self.layers.keys().cloned().collect();
        for support in 1..=k.min(n) {
            self.found.clear();
            let mut all = vec![];
            patterns(&names, support, 0, &mut vec![], &mut all);
            for pattern in all {
                if pattern
                    .iter()
                    .any(|p| pattern.iter().filter(|q| *q == p).count() > self.layers[p].len())
                {
                    continue;
                }
                match self.visit(&pattern, &vec![0; n], 0, -1) {
                    Err(error) if error == "time_limit" => return Ok(false),
                    result => result?,
                }
            }
            self.cuts = minimal([std::mem::take(&mut self.cuts), self.found.clone()].concat());
            if support == 1 {
                for s in &self.cuts {
                    let v = s.iter().position(|&d| d > 0).unwrap();
                    self.dmax[v] = self
                        .ds
                        .iter()
                        .copied()
                        .filter(|&d| d < s[v])
                        .max()
                        .unwrap_or(0);
                }
            }
        }
        Ok(true)
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

/// Node indices by layer p, each layer in descending capacity (rank r), ties by index.
fn layers(model: &Model, network: &Value) -> Result<BTreeMap<String, Vec<usize>>, String> {
    let nodes = network["nodes"].as_array().ok_or("Missing network nodes")?;
    let mut order: Vec<usize> = (0..model.nodes().len()).collect();
    order.sort_by(|&a, &b| {
        model.nodes()[a]
            .1
            .cmp(&model.nodes()[b].1)
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
        layers
            .entry(model.nodes()[v].1.clone())
            .or_default()
            .push(v);
    }
    Ok(layers)
}

/// Each cut's failure certificate (dual value above theta, small gap) and, for every
/// disrupted node, the surviving predecessor with that node's duration one grid step shorter.
fn certificates(
    model: &Model,
    cuts: &[Vec<i64>],
    ds: &[i64],
    theta: f64,
) -> Result<Vec<Value>, String> {
    let mut certificates = vec![];
    for d in cuts {
        let state: Vec<f64> = d.iter().map(|&x| x as f64).collect();
        let solved = model.solve(&state, true, None)?;
        if solved["status"] != "optimal" {
            return Err(format!("Cut certificate solve: {solved}"));
        }
        if !certified_failure(&solved, theta) {
            return Err("Invalid failing-state or dual-gap certificate".into());
        }
        let mut pred = vec![];
        for (v, &t) in d.iter().enumerate().filter(|(_, d)| **d > 0) {
            let previous = ds.iter().copied().filter(|&x| x < t).max().unwrap_or(0);
            let mut p = state.clone();
            p[v] = previous as f64;
            let solved = model.solve(&p, false, None)?;
            if !survives(&solved, theta) {
                return Err("Nonminimal cut certificate".into());
            }
            pred.push(json!({"v":v,"D":previous,"phi":solved["phi"]}));
        }
        certificates.push(json!({"state":d,"phi":solved["phi"],"dual":solved["dual"],"gap":solved["gap"],"predecessors":pred}));
    }
    Ok(certificates)
}

fn enumerate(network: &Value, config: &Value) -> Result<Value, String> {
    sc_data::config::validate(config)?;
    if config.get("f").is_some() {
        return Err(
            "Cut enumeration currently certifies full outages; use evaluate for partial losses"
                .into(),
        );
    }
    let model = Model::from_network(network, config)?;
    let n = model.nodes().len();
    let alpha = config["alpha"].as_f64().unwrap_or(0.25);
    let k = config["k"].as_u64().unwrap_or(3) as usize;
    let seconds = config["time_limit"].as_f64().unwrap_or(60.0);
    if !(0.0..1.0).contains(&alpha) || !seconds.is_finite() || seconds <= 0.0 {
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
            .any(|&d| d <= 0 || !model.ends().contains(&(d as usize)))
    {
        return Err("Durations must be positive model block ends".into());
    }
    let start = Instant::now();
    let mut search = Search {
        model: &model,
        layers: layers(&model, network)?,
        ds: ds.clone(),
        cache: BTreeMap::new(),
        cuts: vec![],
        found: vec![],
        dmax: vec![*ds.last().unwrap(); n],
        theta: alpha * model.total(),
        deadline: start + Duration::from_secs_f64(seconds),
    };
    if !search.lattice(k, n)? {
        return Ok(json!({"complete":false,"status":"limit",
        "candidate_failing_states":minimal([search.cuts,search.found].concat()),
        "lp_calls":search.cache.len(),"seconds":start.elapsed().as_secs_f64()}));
    }
    search.cuts.sort();
    let certificates = certificates(&model, &search.cuts, &ds, search.theta)?;
    Ok(
        json!({"complete":true,"status":"optimal","algorithm":"capacity_dominance_lattice",
        "network":network,
        "nodes":model.nodes(),"cuts":search.cuts,"certificates":certificates,"config":config,
        "total":model.total(),"lp_calls":search.cache.len(),"seconds":start.elapsed().as_secs_f64()}),
    )
}

/// Only a complete local search can construct an accepted cut family.
pub struct Accepted(Value);
impl Accepted {
    pub fn report(&self) -> &Value {
        &self.0
    }
}
pub enum Outcome {
    Complete(Accepted),
    Incomplete(Value),
}
impl Outcome {
    pub fn report(&self) -> &Value {
        match self {
            Self::Complete(c) => c.report(),
            Self::Incomplete(v) => v,
        }
    }
}
pub fn search(network: &Value, config: &Value) -> Result<Outcome, String> {
    let value = enumerate(network, config)?;
    Ok(if value["complete"] == true {
        Outcome::Complete(Accepted(value))
    } else {
        Outcome::Incomplete(value)
    })
}
/// Errors unless every model key of the selected config equals the certified one, both read
/// with the model defaults and numbers compared as f64.
pub fn certified_under(config: &Value, certified: &Value) -> Result<(), String> {
    let defaults = json!({"alpha":0.25,"h":0,"sigma":0,"L":6,"T":24,"choice":false,"shares":[0,1],"durations":[3,6,12],"aggregate":true,"k":3});
    for (key, default) in defaults.as_object().unwrap() {
        let selected = config.get(key).unwrap_or(default);
        let certified = certified.get(key).unwrap_or(default);
        if !(selected == certified
            || selected.is_number()
                && certified.is_number()
                && selected.as_f64() == certified.as_f64())
        {
            return Err(format!("Cut certificate configuration mismatch: {key}"));
        }
    }
    Ok(())
}
/// Individual witnesses cannot establish exhaustion. Re-enumerate imported families.
pub fn admit(network: &Value, config: &Value, supplied: &Value) -> Result<Accepted, String> {
    if supplied["complete"] != true {
        return Err("Risk requires a complete cut family".into());
    }
    if supplied["network"] != *network {
        return Err("Cut certificate requires this exact network".into());
    }
    certified_under(config, &supplied["config"])?;
    let Outcome::Complete(fresh) = search(network, config)? else {
        return Err("Imported cut admission requires a completed independent search".into());
    };
    for key in [
        "complete",
        "status",
        "algorithm",
        "network",
        "nodes",
        "cuts",
        "certificates",
        "total",
    ] {
        if supplied.get(key) != fresh.report().get(key) {
            return Err(if key == "nodes" {
                "Cut roster differs from selected network".into()
            } else {
                format!("Imported cut family fails admission: {key}")
            });
        }
    }
    Ok(Accepted(supplied.clone()))
}
