// V: country/product nodes; p: annual onset probabilities; rho: common-shock share.
// D: outage months; w: conditional duration weights; C: active minimal cuts.
// s: country shock probabilities; q: residual node probabilities; t: decision index.
// j: country index; v/u: node indices; a: required outage; z: categorical mass.
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
mod law;
pub mod sampling;
pub mod stats;

type Cut = Vec<(usize, i64)>;
type Cuts = Vec<Cut>;
type State = (usize, Cuts, bool);

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Input {
    #[serde(rename = "V")]
    pub v: Vec<(String, String)>,
    pub p: Vec<f64>,
    pub rho: f64,
    pub durations: Vec<i64>,
    pub weights: Vec<f64>,
    pub cuts: Vec<Vec<i64>>,
}

fn categorical(p: f64, durations: &[i64], weights: &[f64]) -> Vec<(i64, f64)> {
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

pub fn exact_union(input: Input) -> Result<f64, &'static str> {
    let law = law::Law::new(&input)?;
    Ok(union(&input, &law, &input.cuts))
}

fn union(input: &Input, law: &law::Law, cuts: &[Vec<i64>]) -> f64 {
    let Input {
        durations, weights, ..
    } = input;
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
    let mut variables = Vec::new();
    for (j, group) in law.groups.iter().enumerate() {
        let nodes: Vec<usize> = group
            .iter()
            .copied()
            .filter(|v| relevant.contains(v))
            .collect();
        if !nodes.is_empty() {
            variables.push((j, None));
            variables.extend(nodes.into_iter().map(|v| (j, Some(v))));
        }
    }
    let mut recursion = Recursion {
        variables,
        s: law.s.clone(),
        independent: law
            .q
            .iter()
            .map(|&p| categorical(p, durations, weights))
            .collect(),
        common: categorical(1.0, durations, weights),
        cache: HashMap::new(),
    };
    recursion.visit(0, c.into_iter().collect(), false)
}
