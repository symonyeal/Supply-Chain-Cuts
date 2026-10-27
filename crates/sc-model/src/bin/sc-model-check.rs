// N: physical network; config: recourse parameters; states: dense outage-month vectors.
use serde_json::{Value, json};
use std::io::{self, BufRead, Write};

fn main() {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let response = (|| -> Result<Value, String> {
            let row: Value = serde_json::from_str(&line.map_err(|x| x.to_string())?)
                .map_err(|x| x.to_string())?;
            let states: Vec<Vec<f64>> =
                serde_json::from_value(row["states"].clone()).map_err(|x| x.to_string())?;
            let mut result = sc_model::evaluate(&row["network"], &row["config"], &states)?;
            result["key"] = row["key"].clone();
            Ok(result)
        })()
        .unwrap_or_else(|error| json!({"error":error}));
        if writeln!(out, "{response}")
            .and_then(|_| out.flush())
            .is_err()
        {
            break;
        }
    }
}
