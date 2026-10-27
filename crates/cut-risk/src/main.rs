// V: country/product nodes; p: annual onset probabilities; rho: common-shock share.
// D: outage months; w: conditional duration weights; C: active minimal cuts.
// s: country shock probabilities; q: residual node probabilities; t: decision index.
// j: country index; v/u: node indices; a: required outage; z: categorical mass.
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::io::{self, BufRead, Write};

type Cut = Vec<(usize, i64)>;
type Cuts = Vec<Cut>;
type State = (usize, Cuts, bool);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    #[serde(rename = "V")]
    v: Vec<(String, String)>,
    p: Vec<f64>,
    rho: f64,
    durations: Vec<i64>,
    weights: Vec<f64>,
    cuts: Vec<Vec<i64>>,
}

fn law(p: f64, durations: &[i64], weights: &[f64]) -> Vec<(i64, f64)> {
    let mut out = BTreeMap::from([(0, 1.0 - p)]);
    for (&d, &w) in durations.iter().zip(weights) {
        *out.entry(d).or_insert(0.0) += p * w;
    }
    out.into_iter().filter(|(_, z)| *z != 0.0).collect()
}

struct Recursion {
    variables: Vec<(usize, Option<usize>)>,
    s: Vec<f64>,
    independent: Vec<Vec<(i64, f64)>>,
    common: Vec<(i64, f64)>,
    cache: HashMap<State, f64>,
}

impl Recursion {
    fn visit(&mut self, t: usize, active: Cuts, shock: bool) -> f64 {
        if active.iter().any(Vec::is_empty) {
            return 1.0;
        }
        if active.is_empty() {
            return 0.0;
        }
        let key = (t, active, shock);
        if let Some(&z) = self.cache.get(&key) {
            return z;
        }
        let (j, v) = self.variables[t];
        let prob = match v {
            None => {
                // Preserve Python's multiplication/addition order; never use mul_add.
                let left = self.visit(t + 1, key.1.clone(), false);
                let right = self.visit(t + 1, key.1.clone(), true);
                (1.0 - self.s[j]) * left + self.s[j] * right
            }
            Some(v) => {
                let outcomes = if shock {
                    &self.common
                } else {
                    &self.independent[v]
                }
                .clone();
                let mut prob = 0.0;
                for (d, z) in outcomes {
                    let remaining: BTreeSet<Cut> = key
                        .1
                        .iter()
                        .filter(|cut| cut.iter().all(|&(u, a)| u != v || d >= a))
                        .map(|cut| cut.iter().copied().filter(|&(u, _)| u != v).collect())
                        .collect();
                    prob += z * self.visit(t + 1, remaining.into_iter().collect(), shock);
                }
                prob
            }
        };
        self.cache.insert(key, prob);
        prob
    }
}

fn exact_union(input: Input) -> Result<f64, &'static str> {
    let Input {
        v,
        p,
        rho,
        durations,
        weights,
        cuts,
    } = input;
    let sum: f64 = weights.iter().sum();
    if p.len() != v.len()
        || p.iter().any(|x| !x.is_finite() || !(0.0..=1.0).contains(x))
        || !(0.0..=1.0).contains(&rho)
        || durations.len() != weights.len()
        || weights.iter().any(|x| !x.is_finite() || *x < 0.0)
        || (sum - 1.0).abs() > 1e-8 + 1e-5
        || cuts.iter().any(|cut| cut.len() != v.len())
    {
        return Err("Valid node probabilities, rho, weights and dense cuts required");
    }
    let mut groups: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for (i, (country, _)) in v.iter().enumerate() {
        groups.entry(country).or_default().push(i);
    }
    let c: BTreeSet<Cut> = cuts
        .iter()
        .map(|cut| {
            cut.iter()
                .enumerate()
                .filter(|(_, d)| **d != 0)
                .map(|(v, &d)| (v, d))
                .collect()
        })
        .collect();
    let relevant: BTreeSet<usize> = c.iter().flatten().map(|&(v, _)| v).collect();
    let mut s = Vec::new();
    let mut q = p.clone();
    let mut variables = Vec::new();
    for (j, group) in groups.values().enumerate() {
        let x = rho * group.iter().map(|&v| p[v]).fold(f64::INFINITY, f64::min);
        s.push(x);
        let nodes: Vec<usize> = group
            .iter()
            .copied()
            .filter(|v| relevant.contains(v))
            .collect();
        if !nodes.is_empty() {
            variables.push((j, None));
            variables.extend(nodes.into_iter().map(|v| (j, Some(v))));
        }
        for &v in group {
            q[v] = if x < 1.0 { (p[v] - x) / (1.0 - x) } else { 0.0 };
        }
    }
    let mut recursion = Recursion {
        variables,
        s,
        independent: q.iter().map(|&p| law(p, &durations, &weights)).collect(),
        common: law(1.0, &durations, &weights),
        cache: HashMap::new(),
    };
    Ok(recursion.visit(0, c.into_iter().collect(), false))
}

fn main() {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let response = match line {
            Ok(line) => match serde_json::from_str::<Input>(&line) {
                Ok(input) => match exact_union(input) {
                    Ok(value) => {
                        serde_json::json!({"L": value, "bits": format!("{:016x}", value.to_bits())})
                    }
                    Err(message) => serde_json::json!({"error": message}),
                },
                Err(error) => serde_json::json!({"error": error.to_string()}),
            },
            Err(error) => serde_json::json!({"error": error.to_string()}),
        };
        if writeln!(out, "{response}")
            .and_then(|_| out.flush())
            .is_err()
        {
            break;
        }
    }
}
