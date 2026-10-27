// A: sparse constraint matrix; c: objective; l/u: column bounds; lo/hi: row bounds.
// x: primal solution; h: owned HiGHS instance; st: native status; p/i/v: CSC storage.
use std::collections::BTreeMap;
use std::ffi::{CStr, c_char, c_void};

unsafe extern "C" {
    fn Highs_create() -> *mut c_void;
    fn Highs_destroy(h: *mut c_void);
    fn Highs_version() -> *const c_char;
    fn Highs_passLp(
        h: *mut c_void,
        n: i32,
        m: i32,
        nnz: i32,
        format: i32,
        sense: i32,
        offset: f64,
        c: *const f64,
        l: *const f64,
        u: *const f64,
        lo: *const f64,
        hi: *const f64,
        p: *const i32,
        i: *const i32,
        v: *const f64,
    ) -> i32;
    fn Highs_setBoolOptionValue(h: *mut c_void, key: *const c_char, value: i32) -> i32;
    fn Highs_setIntOptionValue(h: *mut c_void, key: *const c_char, value: i32) -> i32;
    fn Highs_setStringOptionValue(h: *mut c_void, key: *const c_char, value: *const c_char) -> i32;
    fn Highs_run(h: *mut c_void) -> i32;
    fn Highs_getModelStatus(h: *const c_void) -> i32;
    fn Highs_getObjectiveValue(h: *const c_void) -> f64;
    fn Highs_getSolution(
        h: *const c_void,
        x: *mut f64,
        z: *mut f64,
        r: *mut f64,
        y: *mut f64,
    ) -> i32;
}

pub fn version() -> String {
    // SAFETY: the C API returns a static NUL-terminated version string.
    unsafe { CStr::from_ptr(Highs_version()) }
        .to_string_lossy()
        .into_owned()
}

#[derive(Clone)]
pub struct Matrix {
    pub n: usize,
    pub rows: Vec<BTreeMap<usize, f64>>,
}

impl Matrix {
    pub fn new(m: usize, n: usize) -> Self {
        Self {
            n,
            rows: vec![BTreeMap::new(); m],
        }
    }
    pub fn set(&mut self, i: usize, j: usize, x: f64) {
        if x != 0.0 {
            self.rows[i].insert(j, x);
        } else {
            self.rows[i].remove(&j);
        }
    }
    pub fn mul(&self, x: &[f64]) -> Vec<f64> {
        self.rows
            .iter()
            .map(|row| {
                let mut z = 0.0;
                for (&j, &a) in row {
                    z += a * x[j];
                }
                z
            })
            .collect()
    }
}

struct Handle(*mut c_void);
impl Drop for Handle {
    fn drop(&mut self) {
        // SAFETY: every successful create is destroyed exactly once by this owner.
        unsafe { Highs_destroy(self.0) };
    }
}

pub struct ResultLp {
    pub status: &'static str,
    pub fun: f64,
    pub x: Vec<f64>,
}

pub fn linprog(
    c: &[f64],
    a: &Matrix,
    b: &[f64],
    e: &Matrix,
    f: &[f64],
    lower: &[f64],
    upper: &[f64],
) -> Result<ResultLp, String> {
    let n = c.len();
    let m = a.rows.len() + e.rows.len();
    if a.n != n
        || e.n != n
        || b.len() != a.rows.len()
        || f.len() != e.rows.len()
        || lower.len() != n
        || upper.len() != n
    {
        return Err("Invalid LP dimensions".into());
    }
    let mut cols = vec![Vec::new(); n];
    for (i, row) in a.rows.iter().chain(&e.rows).enumerate() {
        for (&j, &v) in row {
            cols[j].push((i as i32, v));
        }
    }
    let mut p = vec![0_i32];
    let mut indices = Vec::new();
    let mut values = Vec::new();
    for col in cols {
        for (i, v) in col {
            indices.push(i);
            values.push(v);
        }
        p.push(indices.len().try_into().map_err(|_| "LP too large")?);
    }
    let lo: Vec<f64> = b
        .iter()
        .map(|_| f64::NEG_INFINITY)
        .chain(f.iter().copied())
        .collect();
    let hi: Vec<f64> = b.iter().chain(f).copied().collect();
    let ni = i32::try_from(n).map_err(|_| "LP too large")?;
    let mi = i32::try_from(m).map_err(|_| "LP too large")?;
    let mut x = vec![0.0; n];
    // SAFETY: all arrays have the validated C API lengths and live through each call.
    // The owned handle does not escape this call. HiGHS copies the passed LP.
    unsafe {
        let h = Handle(Highs_create());
        if h.0.is_null() {
            return Err("HiGHS allocation failed".into());
        }
        for (key, value) in [(c"output_flag", 0), (c"log_to_console", 0)] {
            if Highs_setBoolOptionValue(h.0, key.as_ptr(), value) < 0 {
                return Err("HiGHS option failed".into());
            }
        }
        // SciPy linprog(method='highs') sets presolve on and dual simplex strategy 1,
        // while leaving solver at its default 'choose'. No warm start is reused.
        if Highs_setStringOptionValue(h.0, c"presolve".as_ptr(), c"on".as_ptr()) < 0
            || Highs_setIntOptionValue(h.0, c"simplex_strategy".as_ptr(), 1) < 0
        {
            return Err("HiGHS option failed".into());
        }
        if Highs_passLp(
            h.0,
            ni,
            mi,
            indices.len() as i32,
            1,
            1,
            0.0,
            c.as_ptr(),
            lower.as_ptr(),
            upper.as_ptr(),
            lo.as_ptr(),
            hi.as_ptr(),
            p.as_ptr(),
            indices.as_ptr(),
            values.as_ptr(),
        ) < 0
        {
            return Err("HiGHS rejected LP".into());
        }
        let run = Highs_run(h.0);
        let st = Highs_getModelStatus(h.0);
        let status = match st {
            7 => "optimal",
            8 => "infeasible",
            10 => "unbounded",
            13 | 14 | 16 | 17 => "limit",
            _ => "numerical",
        };
        if status != "optimal" {
            return Ok(ResultLp {
                status,
                fun: f64::NAN,
                x: Vec::new(),
            });
        }
        if run < 0
            || Highs_getSolution(
                h.0,
                x.as_mut_ptr(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
            ) < 0
        {
            return Err("HiGHS solution retrieval failed".into());
        }
        Ok(ResultLp {
            status,
            fun: Highs_getObjectiveValue(h.0),
            x,
        })
    }
}
