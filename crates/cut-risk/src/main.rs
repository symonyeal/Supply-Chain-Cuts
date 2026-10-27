// JSON-lines compatibility entry point; the native supply CLI calls the same library.
use cut_risk::{Input, exact_union};
use std::io::{self, BufRead, Write};

fn main() {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let response = match line {
            Ok(line) => match serde_json::from_str::<Input>(&line) {
                Ok(input) => match exact_union(input) {
                    Ok(value) => serde_json::json!({"L": value,
                        "bits": format!("{:016x}", value.to_bits())}),
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
