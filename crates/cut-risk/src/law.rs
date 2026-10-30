//! Validated country-shock law shared by exact integration, counts and sampling.
//! groups: country-ordered node indices; s: shock rates; q: residual onset rates.
use crate::Input;
use std::collections::BTreeMap;

pub(crate) struct Law {
    pub groups: Vec<Vec<usize>>,
    pub s: Vec<f64>,
    pub q: Vec<f64>,
}

impl Law {
    pub fn new(input: &Input) -> Result<Self, &'static str> {
        let sum: f64 = input.weights.iter().sum();
        if input.p.len() != input.v.len()
            || input
                .p
                .iter()
                .any(|x| !x.is_finite() || !(0.0..=1.0).contains(x))
            || !(0.0..=1.0).contains(&input.rho)
            || input.durations.len() != input.weights.len()
            || input.weights.iter().any(|x| !x.is_finite() || *x < 0.0)
            || (sum - 1.0).abs() > 1e-8 + 1e-5
            || input.cuts.iter().any(|cut| cut.len() != input.v.len())
        {
            return Err("Valid node probabilities, rho, weights and dense cuts required");
        }
        let mut groups: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
        for (v, (country, _)) in input.v.iter().enumerate() {
            groups.entry(country).or_default().push(v);
        }
        let groups: Vec<_> = groups.into_values().collect();
        let mut s = Vec::with_capacity(groups.len());
        let mut q = input.p.clone();
        for group in &groups {
            let x = input.rho
                * group
                    .iter()
                    .map(|&v| input.p[v])
                    .fold(f64::INFINITY, f64::min);
            s.push(x);
            for &v in group {
                q[v] = if x < 1.0 {
                    (input.p[v] - x) / (1.0 - x)
                } else {
                    0.0
                };
            }
        }
        Ok(Self { groups, s, q })
    }
}
