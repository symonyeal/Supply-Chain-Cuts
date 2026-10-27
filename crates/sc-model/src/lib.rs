//! Native transcription of the time-expanded recourse LP in docs/MODEL.md.
// V: country/product nodes; u: monthly capacities; a: input/output coefficients.
// d: monthly final demand; h: stock months; sigma: spare fraction; L: ramp months.
// R: production recipes; E/f: inventory equalities; A/b: inequality rows; c: shortfall cost.
// D: disruption months; f_loss: node capacity loss fractions; phi: cumulative shortfall.
// n: internal nodes; k: blocks; ell: block lengths; nr: production variables per block.
// m/s: input edges/inventory stocks; cap: capacity row indices; mcap: capacity-dual bounds.
mod highs;
pub use highs::version;

use highs::{Matrix, linprog};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone)]
struct Recipe {
    name: String,
    output: String,
    inputs: BTreeMap<String, f64>,
}

pub struct Model {
    pub v: Vec<(String, String)>,
    pub ends: Vec<usize>,
    pub total: f64,
    a: Matrix,
    b: Vec<f64>,
    e: Matrix,
    f: Vec<f64>,
    c: Vec<f64>,
    cap: Vec<Vec<usize>>,
    u: Vec<Vec<f64>>,
    mcap: Vec<Vec<f64>>,
}

fn number(value: &Value, key: &str, default: f64) -> Result<f64, String> {
    match value.get(key) {
        Some(x) => x
            .as_f64()
            .filter(|x| x.is_finite())
            .ok_or_else(|| format!("Invalid {key}")),
        None => Ok(default),
    }
}

fn required(value: &Value, key: &str) -> Result<f64, String> {
    value
        .get(key)
        .and_then(Value::as_f64)
        .filter(|x| x.is_finite())
        .ok_or_else(|| format!("Missing finite {key}"))
}

fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>, String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("Missing {key} array"))
}

impl Model {
    pub fn from_network(network: &Value, config: &Value) -> Result<Self, String> {
        let h = number(config, "h", 0.0)?;
        let sigma = number(config, "sigma", 0.0)?;
        let ramp_l = number(config, "L", 6.0)?;
        let horizon = number(config, "T", 24.0)?;
        if h < 0.0 || sigma < 0.0 || ramp_l <= 0.0 || horizon < 1.0 || horizon.fract() != 0.0 {
            return Err("Nonnegative recourse, positive L and positive integer T required".into());
        }
        let horizon = horizon as usize;
        let aggregate = config
            .get("aggregate")
            .and_then(Value::as_bool)
            .unwrap_or(true);
        let choice = config
            .get("choice")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let nodes = array(network, "nodes")?;
        let mut v = Vec::new();
        let mut original_u = Vec::new();
        for node in nodes {
            let country = node["country"]
                .as_str()
                .ok_or("Missing country")?
                .to_owned();
            let product = node["product"]
                .as_str()
                .ok_or("Missing product")?
                .to_owned();
            let u = required(node, "capacity")?;
            if u < 0.0 {
                return Err("Nonnegative capacity required".into());
            }
            v.push((country, product));
            original_u.push(u);
        }
        if v.is_empty() || v.iter().collect::<BTreeSet<_>>().len() != v.len() {
            return Err("Distinct nonempty nodes required".into());
        }
        let finals: Vec<String> = array(network, "finals")?
            .iter()
            .map(|x| {
                x.as_str()
                    .map(str::to_owned)
                    .ok_or_else(|| "Invalid final product".to_string())
            })
            .collect::<Result<_, _>>()?;
        if finals.is_empty() {
            return Err("At least one final product required".into());
        }
        let mut requirement: BTreeMap<String, f64> = network["requirement"]
            .as_object()
            .ok_or("Missing requirements")?
            .iter()
            .map(|(key, x)| {
                x.as_f64()
                    .filter(|x| x.is_finite() && *x > 0.0)
                    .map(|x| (key.clone(), x))
                    .ok_or_else(|| "Positive requirements required".to_string())
            })
            .collect::<Result<_, _>>()?;
        let mut coefficients = BTreeMap::new();
        for row in array(network, "a")? {
            let row = row.as_array().ok_or("Invalid input arc")?;
            if row.len() != 3 {
                return Err("Input arc needs three entries".into());
            }
            let p = row[0].as_str().ok_or("Invalid input product")?.to_owned();
            let q = row[1].as_str().ok_or("Invalid output product")?.to_owned();
            let x = row[2]
                .as_f64()
                .filter(|x| x.is_finite() && *x > 0.0)
                .ok_or("Positive input coefficients required")?;
            let rp = *requirement.get(&p).ok_or("Missing input requirement")?;
            let rq = *requirement.get(&q).ok_or("Missing output requirement")?;
            coefficients.insert((p, q), x * rq / rp);
        }
        let layers: BTreeSet<String> = v.iter().map(|(_, p)| p.clone()).collect();
        let mut recipes: BTreeMap<String, Vec<Recipe>> = layers
            .iter()
            .map(|p| {
                let inputs = coefficients
                    .iter()
                    .filter(|((_, q), _)| q == p)
                    .map(|((q, _), &x)| (q.clone(), x))
                    .collect();
                (
                    p.clone(),
                    vec![Recipe {
                        name: p.clone(),
                        output: p.clone(),
                        inputs,
                    }],
                )
            })
            .collect();
        let mut stock = coefficients.clone();
        let mut shares = Vec::new();
        if choice {
            if network["ncm"].as_f64() != Some(0.5) || !finals.iter().any(|p| p == "cell") {
                return Err("Chemistry choice requires the 50% reference cell network".into());
            }
            let share = config.get("shares").cloned().unwrap_or(json!([0, 1]));
            let share = share
                .as_array()
                .filter(|x| x.len() == 2)
                .ok_or("Two shares required")?;
            let lo = share[0].as_f64().ok_or("Invalid share")?;
            let hi = share[1].as_f64().ok_or("Invalid share")?;
            if !(0.0..=1.0).contains(&lo) || !(lo..=1.0).contains(&hi) {
                return Err("Chemistry shares require 0 <= lo <= hi <= 1".into());
            }
            shares.push(("cell".to_string(), lo, hi));
            let bom = array(network, "recipe_bom")?;
            if bom.len() != 2 {
                return Err("Two endpoint recipe BOMs required".into());
            }
            let cam_req = *requirement.get("cam").ok_or("Missing cam requirement")?;
            requirement.insert("cam_lfp".into(), cam_req);
            requirement.insert("cam_ncm".into(), cam_req);
            recipes.insert("cam".into(), Vec::new());
            recipes.insert("cell".into(), Vec::new());
            stock.retain(|(_, q), _| q != "cam" && q != "cell");
            let blend_cam =
                (required(&bom[0], "cam_kg_kwh")? + required(&bom[1], "cam_kg_kwh")?) / 2.0;
            for (name, b) in ["lfp", "ncm"].into_iter().zip(bom) {
                let cam = required(b, "cam_kg_kwh")?;
                let output = format!("cam_{name}");
                let mut cam_inputs = BTreeMap::from([(
                    "li_carbonate".to_string(),
                    required(b, "lce_kg_kwh")? / cam,
                )]);
                if name == "ncm" {
                    cam_inputs.insert("pcam".into(), required(b, "pcam_kg_kwh")? / cam);
                }
                let cell_inputs = BTreeMap::from([
                    (output.clone(), cam),
                    ("aam".into(), required(&b["kg_kwh"], "Graphite")?),
                    ("refined_cu".into(), required(&b["kg_kwh"], "Cu")?),
                    ("aluminium".into(), required(&b["kg_kwh"], "Al")?),
                ]);
                for (layer, out, inputs) in [
                    ("cam", output, cam_inputs),
                    ("cell", "cell".to_string(), cell_inputs),
                ] {
                    let inputs: BTreeMap<String, f64> = inputs
                        .into_iter()
                        .map(|(p, x)| {
                            let rp = *requirement
                                .get(&p)
                                .ok_or("Missing recipe input requirement")?;
                            let rq = *requirement
                                .get(&out)
                                .ok_or("Missing recipe output requirement")?;
                            Ok((p, x * rq / rp))
                        })
                        .collect::<Result<_, String>>()?;
                    let weight = if layer == "cam" {
                        cam / (2.0 * blend_cam)
                    } else {
                        0.5
                    };
                    for (p, &x) in &inputs {
                        *stock.entry((p.clone(), layer.to_owned())).or_default() += weight * x;
                    }
                    recipes.get_mut(layer).unwrap().push(Recipe {
                        name: name.into(),
                        output: out,
                        inputs,
                    });
                }
            }
            for rs in recipes.values_mut() {
                rs.retain(|r| {
                    !(r.output == "cell"
                        && ((hi == 0.0 && r.name == "ncm") || (lo == 1.0 && r.name != "ncm")))
                });
            }
        }
        let arcs: Vec<(String, String, f64)> = recipes
            .values()
            .flatten()
            .flat_map(|r| {
                r.inputs
                    .iter()
                    .map(|(p, &x)| (p.clone(), r.output.clone(), x))
            })
            .collect();
        let products: BTreeSet<String> = recipes
            .values()
            .flatten()
            .map(|r| r.output.clone())
            .chain(arcs.iter().map(|(p, _, _)| p.clone()))
            .chain(finals.iter().cloned())
            .collect();
        let mut remaining = products.clone();
        let mut order = Vec::new();
        while !remaining.is_empty() {
            let next: Vec<String> = remaining
                .iter()
                .filter(|p| {
                    !arcs
                        .iter()
                        .any(|(r, q, _)| q == *p && remaining.contains(r))
                })
                .cloned()
                .collect();
            if next.is_empty() {
                return Err("Product graph must be acyclic".into());
            }
            for p in next {
                remaining.remove(&p);
                order.push(p);
            }
        }
        let mut bound: BTreeMap<String, f64> = products
            .iter()
            .map(|p| (p.clone(), if finals.contains(p) { 1.0 } else { 0.0 }))
            .collect();
        for p in order.iter().rev() {
            let x = arcs
                .iter()
                .filter(|(r, _, _)| r == p)
                .map(|(_, q, x)| bound[q] / x)
                .fold(bound[p], f64::max);
            bound.insert(p.clone(), x);
        }
        let gamma = shares.iter().fold(1.0_f64, |z, (_, lo, hi)| {
            z.max(if *lo > 0.0 && *lo < 1.0 {
                1.0 / lo
            } else {
                1.0
            })
            .max(if *hi > 0.0 && *hi < 1.0 {
                1.0 / (1.0 - hi)
            } else {
                1.0
            })
        });
        let mut ends = BTreeSet::from([horizon]);
        let durations = config
            .get("durations")
            .cloned()
            .unwrap_or(json!([3, 6, 12]));
        for d in durations.as_array().ok_or("Invalid durations")? {
            let d = d
                .as_u64()
                .filter(|x| *x > 0)
                .ok_or("Positive integer durations required")?;
            if d < horizon as u64 {
                ends.insert(d as usize);
            }
        }
        if sigma != 0.0 {
            ends.extend(1..=horizon.min(ramp_l.ceil() as usize));
        }
        let ends: Vec<usize> = ends.into_iter().collect();
        let ell: Vec<f64> = ends
            .iter()
            .enumerate()
            .map(|(t, &e)| (e - if t == 0 { 0 } else { ends[t - 1] }) as f64)
            .collect();
        let ramp: Vec<f64> = ends
            .iter()
            .map(|&e| 1.0 + sigma * (e as f64 / ramp_l).min(1.0))
            .collect();
        let (internal_v, internal_u) = if h == 0.0 && aggregate {
            let mut u: BTreeMap<String, f64> = BTreeMap::new();
            for ((_, p), &x) in v.iter().zip(&original_u) {
                *u.entry(p.clone()).or_default() += x;
            }
            let internal_v = u.keys().map(|p| ("ALL".to_string(), p.clone())).collect();
            (internal_v, u.values().copied().collect::<Vec<_>>())
        } else {
            (v.clone(), original_u.clone())
        };
        let n = internal_v.len();
        let k = ends.len();
        let finals_n = finals.len();
        let products: Vec<String> = products.into_iter().collect();
        let mut production = Vec::new();
        let mut edges = Vec::new();
        for (i, (_, p)) in internal_v.iter().enumerate() {
            for r in &recipes[p] {
                production.push((i, r.clone()));
            }
            let inputs: BTreeSet<String> = recipes[p]
                .iter()
                .flat_map(|r| r.inputs.keys().cloned())
                .collect();
            for q in inputs {
                edges.push((q, i));
            }
        }
        let nr = production.len();
        let m = edges.len();
        let s = edges.len();
        let block_n = nr + m + s + finals_n;
        let inequality_n = k * (n + products.len() + finals_n + shares.len()) + 2 * shares.len();
        let mut a = Matrix::new(inequality_n, k * block_n);
        let mut e = Matrix::new(k * s, k * block_n);
        let mut b = vec![0.0; inequality_n];
        let mut f = vec![0.0; k * s];
        let mut c = vec![0.0; k * block_n];
        for t in 0..k {
            let offset = t * block_n;
            for (i, &u) in internal_u.iter().enumerate() {
                b[t * n + i] = u * ramp[t];
            }
            for (i, (v, recipe)) in production.iter().enumerate() {
                a.set(t * n + v, offset + i, 1.0);
                let r =
                    k * n + t * products.len() + products.binary_search(&recipe.output).unwrap();
                a.set(r, offset + i, -1.0);
            }
            for (i, (q, _)) in edges.iter().enumerate() {
                let r = k * n + t * products.len() + products.binary_search(q).unwrap();
                a.set(r, offset + nr + i, 1.0);
            }
            for (l, q) in finals.iter().enumerate() {
                let r = k * (n + products.len()) + t * finals_n + l;
                for (i, (_, recipe)) in production.iter().enumerate() {
                    if &recipe.output == q {
                        a.set(r, offset + i, -1.0);
                    }
                }
                a.set(r, offset + nr + m + s + l, -1.0);
                b[r] = -1.0 / 12.0;
                c[offset + nr + m + s + l] = ell[t];
            }
            for (i, (q, w)) in edges.iter().enumerate() {
                let r = t * s + i;
                e.set(r, offset + nr + m + i, 1.0);
                if t != 0 {
                    e.set(r, offset - block_n + nr + m + i, -1.0);
                } else {
                    let coefficient = *stock
                        .get(&(q.clone(), internal_v[*w].1.clone()))
                        .unwrap_or(&0.0);
                    f[r] = h * coefficient * internal_u[*w];
                }
                e.set(r, offset + nr + i, -ell[t]);
                for (j, (v, recipe)) in production.iter().enumerate() {
                    if v == w {
                        e.set(r, offset + j, ell[t] * recipe.inputs.get(q).unwrap_or(&0.0));
                    }
                }
            }
            for (l, (q, lo, hi)) in shares.iter().enumerate() {
                let r = k * (n + products.len() + finals_n) + t * shares.len() + l;
                b[r] = 1.0 / 12.0;
                for (i, (_, recipe)) in production.iter().enumerate() {
                    if &recipe.output == q {
                        a.set(r, offset + i, 1.0);
                        let r0 = k * (n + products.len() + finals_n + shares.len()) + 2 * l;
                        let ncm = if recipe.name == "ncm" { 1.0 } else { 0.0 };
                        a.set(r0, offset + i, ell[t] * (lo - ncm));
                        a.set(r0 + 1, offset + i, ell[t] * (ncm - hi));
                    }
                }
            }
        }
        let mapping: Vec<usize> = v
            .iter()
            .enumerate()
            .map(|(i, (_, p))| {
                if h == 0.0 && aggregate {
                    internal_v.iter().position(|(_, q)| q == p).unwrap()
                } else {
                    i
                }
            })
            .collect();
        let cap = (0..k)
            .map(|t| mapping.iter().map(|&i| t * n + i).collect())
            .collect();
        let u = ramp
            .iter()
            .map(|&r| original_u.iter().map(|&x| x * r).collect())
            .collect();
        let mv: Vec<f64> = v
            .iter()
            .map(|(_, p)| {
                gamma
                    * recipes[p]
                        .iter()
                        .map(|r| bound[&r.output])
                        .fold(f64::NEG_INFINITY, f64::max)
            })
            .collect();
        let mcap = ell
            .iter()
            .map(|&t| mv.iter().map(|&x| t * x).collect())
            .collect();
        Ok(Self {
            v,
            ends,
            total: finals_n as f64 * (horizon as f64 / 12.0),
            a,
            b,
            e,
            f,
            c,
            cap,
            u,
            mcap,
        })
    }

    pub fn solve(&self, state: &[f64], dual: bool, loss: Option<&[f64]>) -> Result<Value, String> {
        if state.len() != self.v.len()
            || state.iter().any(|x| {
                !x.is_finite()
                    || *x < 0.0
                    || (*x > 0.0 && !self.ends.iter().any(|&d| d as f64 == *x))
            })
        {
            return Err("One nonnegative block-end duration per node required".into());
        }
        let ones = vec![1.0; self.v.len()];
        let loss = loss.unwrap_or(&ones);
        if loss.len() != self.v.len()
            || loss
                .iter()
                .any(|x| !x.is_finite() || !(0.0..=1.0).contains(x))
        {
            return Err("One finite loss fraction in [0,1] per node required".into());
        }
        let mut b = self.b.clone();
        for row in &self.cap {
            for &i in row {
                b[i] = 0.0;
            }
        }
        for (t, &end) in self.ends.iter().enumerate() {
            for (v, &d) in state.iter().enumerate() {
                let active = if end as f64 <= d { 1.0 } else { 0.0 };
                b[self.cap[t][v]] += self.u[t][v] * (1.0 - loss[v] * active);
            }
        }
        let lower = vec![0.0; self.c.len()];
        let upper = vec![f64::INFINITY; self.c.len()];
        let result = linprog(&self.c, &self.a, &b, &self.e, &self.f, &lower, &upper)?;
        if result.status != "optimal" {
            return Ok(json!({"status": result.status}));
        }
        let mut residual = 0.0_f64;
        for (ax, &rhs) in self.a.mul(&result.x).iter().zip(&b) {
            residual = residual.max(ax - rhs);
        }
        for (ex, &rhs) in self.e.mul(&result.x).iter().zip(&self.f) {
            residual = residual.max((ex - rhs).abs());
        }
        for &x in &result.x {
            residual = residual.max(-x);
        }
        // Python max starts with +0 and retains its first operand on a zero tie.
        // Rust f64::max may instead retain -0 from a negated primal variable.
        if residual == 0.0 {
            residual = 0.0;
        }
        let mut out = json!({"status":"optimal", "message":"Optimization terminated successfully. (HiGHS Status 7: Optimal)",
            "phi":result.fun, "dual":null, "gap":null, "residual":residual});
        if dual {
            let ma = self.a.rows.len();
            let me = self.e.rows.len();
            let mut a = Matrix::new(self.c.len(), ma + me);
            for (i, row) in self.a.rows.iter().enumerate() {
                for (&j, &x) in row {
                    a.set(j, i, -x);
                }
            }
            for (i, row) in self.e.rows.iter().enumerate() {
                for (&j, &x) in row {
                    a.set(j, ma + i, x);
                }
            }
            let mut lower = vec![0.0; ma];
            lower.extend(vec![f64::NEG_INFINITY; me]);
            let mut upper = vec![f64::INFINITY; ma + me];
            for t in 0..self.ends.len() {
                for v in 0..self.v.len() {
                    upper[self.cap[t][v]] = self.mcap[t][v];
                }
            }
            let objective: Vec<f64> = b.iter().copied().chain(self.f.iter().map(|x| -x)).collect();
            let result_dual = linprog(
                &objective,
                &a,
                &self.c,
                &Matrix::new(0, ma + me),
                &[],
                &lower,
                &upper,
            )?;
            if result_dual.status != "optimal" {
                return Ok(json!({"status":format!("dual_{}", result_dual.status)}));
            }
            out["dual"] = json!(-result_dual.fun);
            out["gap"] = json!((result.fun + result_dual.fun).abs());
        }
        Ok(out)
    }

    pub fn shape(&self) -> [usize; 3] {
        [self.a.rows.len(), self.e.rows.len(), self.c.len()]
    }
}

pub fn evaluate(network: &Value, config: &Value, states: &[Vec<f64>]) -> Result<Value, String> {
    let model = Model::from_network(network, config)?;
    let loss = config
        .get("f")
        .map(|x| {
            x.as_array()
                .ok_or("Loss vector required")?
                .iter()
                .map(|x| x.as_f64().ok_or("Invalid loss fraction"))
                .collect::<Result<Vec<_>, _>>()
        })
        .transpose()?;
    let dual = config.get("dual").and_then(Value::as_bool).unwrap_or(true);
    let mut out = Vec::new();
    for state in states {
        let mut row = model.solve(state, dual, loss.as_deref())?;
        row["D"] = json!(state);
        out.push(row);
    }
    Ok(
        json!({"ends":model.ends, "total":model.total, "shape":model.shape(), "states":out,
        "highs":version()}),
    )
}
