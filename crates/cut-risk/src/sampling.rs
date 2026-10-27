//! Categorical onset sampling in the reference NumPy PCG64 draw order.
//! s,inc: 128-bit PCG state/stream; ss: SeedSequence pool; H: country shocks.
//! Adapted from symonyeal/Sparse-Portfolio-Optimization pf-core/rng.rs (MIT).
//! Original algorithms: NumPy 2.4 SeedSequence and PCG64 XSL-RR 128/64.
use crate::Input;
use std::collections::BTreeMap;

const M: u128 = (2549297995355413924u128 << 64) | 4865540595714422341u128;

fn hashmix(v: u32, h: &mut u32) -> u32 {
    let mut v = v ^ *h;
    *h = h.wrapping_mul(0x931e8875);
    v = v.wrapping_mul(*h);
    v ^ (v >> 16)
}

fn mix(x: u32, y: u32) -> u32 {
    let r = 0xca01f9ddu32
        .wrapping_mul(x)
        .wrapping_sub(0x4973f715u32.wrapping_mul(y));
    r ^ (r >> 16)
}

fn seed_state(seed: u64) -> [u64; 4] {
    let entropy = if seed > u32::MAX as u64 {
        vec![seed as u32, (seed >> 32) as u32]
    } else {
        vec![seed as u32]
    };
    let mut ss = [0u32; 4];
    let mut h = 0x43b0d7e5;
    for (i, p) in ss.iter_mut().enumerate() {
        *p = hashmix(*entropy.get(i).unwrap_or(&0), &mut h);
    }
    for i in 0..4 {
        for j in 0..4 {
            if i != j {
                let t = hashmix(ss[i], &mut h);
                ss[j] = mix(ss[j], t);
            }
        }
    }
    let mut hb = 0x8b51f9ddu32;
    let mut w = [0u32; 8];
    for (i, o) in w.iter_mut().enumerate() {
        let mut d = ss[i % 4] ^ hb;
        hb = hb.wrapping_mul(0x58f38ded);
        d = d.wrapping_mul(hb);
        *o = d ^ (d >> 16);
    }
    std::array::from_fn(|k| w[2 * k] as u64 | ((w[2 * k + 1] as u64) << 32))
}

pub struct Gen {
    s: u128,
    inc: u128,
}
impl Gen {
    pub fn new(seed: u64) -> Self {
        let v = seed_state(seed);
        let initial = (v[0] as u128) << 64 | v[1] as u128;
        let sequence = (v[2] as u128) << 64 | v[3] as u128;
        let mut g = Self {
            s: 0,
            inc: (sequence << 1) | 1,
        };
        g.step();
        g.s = g.s.wrapping_add(initial);
        g.step();
        g
    }
    fn step(&mut self) {
        self.s = self.s.wrapping_mul(M).wrapping_add(self.inc);
    }
    pub fn random(&mut self) -> f64 {
        self.step();
        let x = ((self.s >> 64) as u64 ^ self.s as u64).rotate_right((self.s >> 122) as u32);
        (x >> 11) as f64 * (1.0 / 9007199254740992.0)
    }
}

pub fn states(input: &Input, n: usize, seed: u64) -> Result<Vec<Vec<i64>>, &'static str> {
    crate::exact_union(input.clone())?; // Apply exactly the same parameter validation.
    let mut groups: BTreeMap<&str, Vec<usize>> = BTreeMap::new();
    for (v, (country, _)) in input.v.iter().enumerate() {
        groups.entry(country).or_default().push(v);
    }
    let mut q = input.p.clone();
    let s: Vec<f64> = groups
        .values()
        .map(|group| {
            let s = input.rho
                * group
                    .iter()
                    .map(|&v| input.p[v])
                    .fold(f64::INFINITY, f64::min);
            for &v in group {
                q[v] = if s < 1.0 {
                    (input.p[v] - s) / (1.0 - s)
                } else {
                    0.0
                };
            }
            s
        })
        .collect();
    let mut rng = Gen::new(seed);
    let h: Vec<Vec<bool>> = (0..n)
        .map(|_| s.iter().map(|&s| rng.random() < s).collect())
        .collect();
    let mut onset: Vec<Vec<bool>> = (0..n)
        .map(|_| q.iter().map(|&q| rng.random() < q).collect())
        .collect();
    for (j, group) in groups.values().enumerate() {
        for i in 0..n {
            for &v in group {
                onset[i][v] |= h[i][j];
            }
        }
    }
    let mut cdf = Vec::new();
    let mut sum = 0.0;
    for &w in &input.weights {
        sum += w;
        cdf.push(sum);
    }
    for x in &mut cdf {
        *x /= sum;
    }
    Ok(onset
        .iter()
        .map(|row| {
            row.iter()
                .map(|&on| {
                    let u = rng.random();
                    let index = cdf.partition_point(|&x| x <= u);
                    if on { input.durations[index] } else { 0 }
                })
                .collect()
        })
        .collect())
}
