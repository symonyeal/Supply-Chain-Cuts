//! Small data-parity command boundary; all production APIs are in the library.
use serde_json::Value;
use std::{
    io::{self, Read},
    path::Path,
};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let opts: Value = serde_json::from_str(&input).unwrap_or(serde_json::json!({}));
    let root = Path::new(args.get(2).map(String::as_str).unwrap_or("."));
    let result = match args.get(1).map(String::as_str) {
        Some("context") => sc_data::context(root).map(|v| v.to_string()),
        Some("context-csv") => sc_data::context(root).and_then(|v| sc_data::context_csv(&v)),
        Some("network") => sc_data::network(root, &opts).map(|v| v.to_string()),
        Some("verify") => sc_data::verify(root).map(|v| v.to_string()),
        _ => Err("Expected verify, context, context-csv or network".to_string()),
    };
    match result {
        Ok(text) => print!("{text}"),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
