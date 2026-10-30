//! Scenario bracket and exact-binomial tail inversion, MODEL Annual probability.
//! n,m: draws/events; L,U: scenario bounds; k: complete cut support; p: binomial rate.
use crate::{Input, law::Law, union};
use serde_json::{Value, json};

// NumPy 2.4's positive-number pairwise sum order (loops_utils.h).
pub fn pairwise(x: &[f64]) -> f64 {
    let n = x.len();
    if n < 8 {
        return x.iter().fold(0.0, |s, &x| s + x);
    }
    if n > 128 {
        let m = (n / 2) / 8 * 8;
        return pairwise(&x[..m]) + pairwise(&x[m..]);
    }
    let mut r: [f64; 8] = x[..8].try_into().unwrap();
    let end = n / 8 * 8;
    for i in (8..end).step_by(8) {
        for j in 0..8 {
            r[j] += x[i + j];
        }
    }
    let mut sum = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]));
    for &x in &x[end..] {
        sum += x;
    }
    sum
}

fn convolve(a: &[f64], b: &[f64]) -> Vec<f64> {
    (0..a.len() + b.len() - 1)
        .map(|k| {
            let start = k.saturating_sub(b.len() - 1);
            let end = k.min(a.len() - 1);
            (start..=end).fold(0.0, |sum, i| sum + a[i] * b[k - i])
        })
        .collect()
}

pub fn bracket(input: &Input, k: usize, complete: bool) -> Result<Value, &'static str> {
    if !complete {
        return Err("A complete cut enumeration through k is required for U");
    }
    let law = Law::new(input)?;
    let lower = union(input, &law, &input.cuts);
    let positive: f64 = input
        .durations
        .iter()
        .zip(&input.weights)
        .filter(|(d, _)| **d > 0)
        .map(|(_, w)| w)
        .sum();
    let mut counts = vec![1.0];
    for (group, &s) in law.groups.iter().zip(&law.s) {
        let mut independent = vec![1.0];
        let mut common = vec![1.0];
        for &v in group {
            let q = law.q[v];
            independent = convolve(&independent, &[1.0 - q * positive, q * positive]);
            common = convolve(&common, &[1.0 - positive, positive]);
        }
        let group: Vec<f64> = independent
            .iter()
            .zip(&common)
            .map(|(&a, &b)| (1.0 - s) * a + s * b)
            .collect();
        counts = convolve(&counts, &group);
    }
    let tail = if k + 1 < counts.len() {
        pairwise(&counts[k + 1..])
    } else {
        0.0
    };
    let attribution: Vec<f64> = input
        .cuts
        .iter()
        .map(|cut| {
            if lower == 0.0 {
                0.0
            } else {
                union(input, &law, std::slice::from_ref(cut)) / lower
            }
        })
        .collect();
    Ok(
        json!({"L":lower,"U":(lower+tail).min(1.0),"tail":tail,"k":k,
        "attribution":attribution,"attribution_overlaps":true}),
    )
}

// Clopper-Pearson limits invert finite binomial tails. Accumulate positive PMFs
// relative to the mode to avoid underflow; only the tails around 0.025 are inverted.
fn cdf(k: usize, n: usize, p: f64, log_fact: &[f64]) -> f64 {
    if p == 0.0 {
        return 1.0;
    }
    if p == 1.0 {
        return if k >= n { 1.0 } else { 0.0 };
    }
    let mode = (((n + 1) as f64 * p).floor() as usize).min(k);
    let log_pmf = log_fact[n] - log_fact[mode] - log_fact[n - mode]
        + mode as f64 * p.ln()
        + (n - mode) as f64 * (-p).ln_1p();
    let mut sum = 1.0;
    let mut term = 1.0;
    for j in (1..=mode).rev() {
        term *= j as f64 / (n - j + 1) as f64 * (1.0 - p) / p;
        sum += term;
    }
    term = 1.0;
    for j in mode..k {
        term *= (n - j) as f64 / (j + 1) as f64 * p / (1.0 - p);
        sum += term;
    }
    (log_pmf.exp() * sum).min(1.0)
}

pub fn binomial_interval(m: usize, n: usize) -> Result<[f64; 2], &'static str> {
    if n == 0 || m > n {
        return Err("Binomial counts require 0 <= m <= n and n > 0");
    }
    let mut log_fact = vec![0.0; n + 1];
    for i in 1..=n {
        log_fact[i] = log_fact[i - 1] + (i as f64).ln();
    }
    let point = m as f64 / n as f64;
    let lower = if m == 0 {
        0.0
    } else {
        let mut a = 0.0;
        let mut b = point;
        for _ in 0..64 {
            let mid = (a + b) / 2.0;
            if cdf(n - m, n, 1.0 - mid, &log_fact) < 0.025 {
                a = mid;
            } else {
                b = mid;
            }
        }
        (a + b) / 2.0
    };
    let upper = if m == n {
        1.0
    } else {
        let mut a = point;
        let mut b = 1.0;
        for _ in 0..64 {
            let mid = (a + b) / 2.0;
            if cdf(m, n, mid, &log_fact) > 0.025 {
                a = mid;
            } else {
                b = mid;
            }
        }
        (a + b) / 2.0
    };
    Ok([lower, upper])
}
