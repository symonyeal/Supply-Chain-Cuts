// Native entry point. R: source root; N: physical network; c: scenario configuration.
mod cuts;
mod publication;
mod risk;
mod server;
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs,
    io::{self, Read},
    path::{Path, PathBuf},
};

const HELP: &str = "Supply Chain Cuts — native Rust pipeline

  supply build [--root .] [--out site]        Verify sources; rebuild explorer JS and CSV
  supply serve [--root .] [--listen 127.0.0.1:8000]
  supply verify [--root .]                    Verify every committed input hash
  supply context [--root .] [--out site]       Build observational context from raw sources
  supply network [--root .] [--sector liion|pv|joint] [--config FILE] [--out FILE]
  supply evaluate [--network FILE] [--config FILE] --states FILE [--out FILE]
  supply cuts [--network FILE] [--config FILE] [--out FILE]
  supply risk [--network FILE] [--config FILE] --law FILE --cuts FILE [--out FILE]
  supply run [--config FILE] --law FILE --out DIRECTORY
  supply probability                         Exact union: JSON-lines on stdin/stdout
  supply sample-law --law FILE [--config FILE] [--out FILE]
  supply interval                            Binomial [m,n] pairs on stdin/stdout

Config JSON controls source options (sector,ncm,cutoff,basis,exclusions), recourse
(choice,shares,T,h,sigma,L,durations), search (alpha,k,time_limit) and sampling
(n,seed). Defaults retain reference behaviour. Search/sampling time limit:60s.
Risk uses an explicitly supplied frozen onset law; it does not silently refit rates.
An incomplete cut search cannot be used to certify a risk upper bound.
";

fn read(path: &Path) -> Result<Value, String> {
    serde_json::from_slice(&fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?)
        .map_err(|e| e.to_string())
}
fn write(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    // Write beside the target, then rename, so a failed write never leaves a partial file.
    let mut candidate = path.as_os_str().to_owned();
    candidate.push(".candidate");
    fs::write(&candidate, bytes).map_err(|e| e.to_string())?;
    fs::rename(&candidate, path).map_err(|e| e.to_string())
}
fn emit(value: &Value, out: Option<&String>) -> Result<(), String> {
    let text = serde_json::to_string_pretty(value).map_err(|e| e.to_string())? + "\n";
    if let Some(path) = out {
        write(Path::new(path), text.as_bytes())
    } else {
        print!("{text}");
        Ok(())
    }
}
fn context(root: &Path, out: &Path) -> Result<Value, String> {
    let c = sc_data::context(root)?;
    write(
        &out.join("context.js"),
        format!("window.CONTEXT={c};\n").as_bytes(),
    )?;
    write(
        &out.join("context.csv"),
        sc_data::context_csv(&c)?.as_bytes(),
    )?;
    Ok(
        json!({"production":c["production"].as_array().unwrap().len(),
        "refining":c["refining"].as_array().unwrap().len()}),
    )
}
fn network(root: &Path, opts: &BTreeMap<String, String>, config: &Value) -> Result<Value, String> {
    let mut n = if let Some(path) = opts.get("network") {
        read(Path::new(path))?
    } else {
        sc_data::network(root, config)?
    };
    if config["choice"].as_bool().unwrap_or(false) {
        n["recipe_bom"] = json!([sc_data::bill(root, 0.0)?, sc_data::bill(root, 1.0)?]);
    }
    Ok(n)
}
fn execute() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() || args.iter().any(|x| x == "--help" || x == "-h") {
        print!("{HELP}");
        return Ok(());
    }
    let command = &args[0];
    let mut opts = BTreeMap::new();
    let mut i = 1;
    while i < args.len() {
        let key = args[i]
            .strip_prefix("--")
            .ok_or("Expected --option value")?;
        if ![
            "root", "out", "network", "config", "sector", "states", "law", "cuts", "listen",
        ]
        .contains(&key)
        {
            return Err(format!("Unknown option: --{key}"));
        }
        let value = args.get(i + 1).ok_or("Option needs a value")?;
        if opts.insert(key.to_string(), value.clone()).is_some() {
            return Err(format!("Repeated option: {key}"));
        }
        i += 2;
    }
    let root = PathBuf::from(opts.get("root").map(String::as_str).unwrap_or("."));
    let mut config = if let Some(path) = opts.get("config") {
        read(Path::new(path))?
    } else {
        json!({})
    };
    if !config.is_object() {
        return Err("Config must be a JSON object".into());
    }
    if let Some(sector) = opts.get("sector") {
        config["sector"] = json!(sector);
    }
    sc_data::config::validate(&config)?;
    match command.as_str() {
        "verify" => emit(&sc_data::verify(&root)?, opts.get("out")),
        "context" => {
            let out = opts
                .get("out")
                .map(PathBuf::from)
                .unwrap_or(root.join("site"));
            let generation = publication::Generation::new(&out, "context")?;
            let result = context(&root, generation.root())?;
            generation.project()?;
            emit(&result, None)
        }
        "build" => {
            let checked = sc_data::verify(&root)?;
            let out = opts
                .get("out")
                .map(PathBuf::from)
                .unwrap_or(root.join("site"));
            let generation = publication::Generation::new(&out, "site")?;
            let c = context(&root, generation.root())?;
            let runs: Vec<String> =
                serde_json::from_value(sc_site::release(&root)?["runs"].clone())
                    .map_err(|e| e.to_string())?;
            let data = sc_site::plain(sc_site::build(&root, &runs)?);
            let saved: usize = [
                &data,
                &data["choice"],
                &data["pv"],
                &data["joint"],
                &data["joint_choice"],
            ]
            .iter()
            .filter_map(|block| block["configs"].as_object().map(|x| x.len()))
            .sum();
            write(
                &generation.root().join("data.js"),
                format!("window.DATA = {data};\n").as_bytes(),
            )?;
            generation.project()?;
            emit(
                &json!({"sources":checked["count"],"context":c,"builder":"native Rust",
                "saved_configurations":saved}),
                None,
            )
        }
        "serve" => server::serve(
            &root.join("site"),
            opts.get("listen")
                .map(String::as_str)
                .unwrap_or("127.0.0.1:8000"),
        ),
        "network" => emit(&network(&root, &opts, &config)?, opts.get("out")),
        "evaluate" => {
            let states = read(Path::new(
                opts.get("states").ok_or("--states FILE required")?,
            ))?;
            let states: Vec<Vec<f64>> =
                serde_json::from_value(states).map_err(|e| e.to_string())?;
            emit(
                &sc_model::evaluate(&network(&root, &opts, &config)?, &config, &states)?,
                opts.get("out"),
            )
        }
        "cuts" => emit(
            cuts::search(&network(&root, &opts, &config)?, &config)?.report(),
            opts.get("out"),
        ),
        "risk" => {
            let law = read(Path::new(opts.get("law").ok_or("--law FILE required")?))?;
            let cuts = read(Path::new(opts.get("cuts").ok_or("--cuts FILE required")?))?;
            let n = network(&root, &opts, &config)?;
            let accepted = cuts::admit(&n, &config, &cuts)?;
            emit(&risk::run(&n, &config, &law, &accepted)?, opts.get("out"))
        }
        "run" => {
            let out = PathBuf::from(opts.get("out").ok_or("--out DIRECTORY required")?);
            let generation = publication::Generation::new(&out, "run")?;
            generation.require_new()?;
            let out = generation.root();
            let law_path = Path::new(opts.get("law").ok_or("--law FILE required")?);
            let law_bytes = fs::read(law_path).map_err(|e| e.to_string())?;
            let law: Value = serde_json::from_slice(&law_bytes).map_err(|e| e.to_string())?;
            let checked = sc_data::verify(&root)?;
            let n = network(&root, &opts, &config)?;
            let search = cuts::search(&n, &config)?;
            let cut = search.report();
            emit(
                &n,
                Some(&out.join("network.json").to_string_lossy().into_owned()),
            )?;
            emit(
                cut,
                Some(&out.join("cuts.json").to_string_lossy().into_owned()),
            )?;
            let result = if let cuts::Outcome::Complete(accepted) = &search {
                risk::run(&n, &config, &law, accepted)?
            } else {
                json!({"status":"incomplete_cuts","complete":false})
            };
            emit(
                &result,
                Some(&out.join("risk.json").to_string_lossy().into_owned()),
            )?;
            let executable = fs::read(std::env::current_exe().map_err(|e| e.to_string())?)
                .map_err(|e| e.to_string())?;
            let hashes: [(&str, String); 3] = ["network.json", "cuts.json", "risk.json"]
                .map(|name| (name, sc_data::digest(&fs::read(out.join(name)).unwrap())));
            let stamp = json!({"engine":"native Rust","version":env!("CARGO_PKG_VERSION"),
                "output_sha256":hashes.into_iter().collect::<BTreeMap<_,_>>(),
                "binary_sha256":sc_data::digest(&executable),"source_lock_sha256":sc_data::digest(
                    &fs::read(root.join("SOURCES.lock")).map_err(|e|e.to_string())?),
                "law_sha256":sc_data::digest(&law_bytes),"network_sha256":sc_data::digest(
                    serde_json::to_string(&n).map_err(|e|e.to_string())?.as_bytes()),
                "config":config,"solver":sc_model::version(),"committed_sources":checked["count"],
                "status":result["status"],"cuts_complete":cut["complete"]});
            emit(
                &stamp,
                Some(&out.join("manifest.json").to_string_lossy().into_owned()),
            )?;
            generation.accept_new()?;
            emit(&stamp, None)
        }
        "sample-law" => {
            let law = read(Path::new(opts.get("law").ok_or("--law FILE required")?))?;
            let input = risk::input(&network(&root, &opts, &config)?, &law, &json!({"cuts":[]}))?;
            let n = config["n"].as_u64().unwrap_or(4000) as usize;
            let seed = config["seed"].as_u64().unwrap_or(0);
            emit(
                &json!(cut_risk::sampling::states(&input, n, seed).map_err(str::to_string)?),
                opts.get("out"),
            )
        }
        "probability" => {
            let mut text = String::new();
            io::stdin()
                .read_to_string(&mut text)
                .map_err(|e| e.to_string())?;
            for line in text.lines().filter(|s| !s.trim().is_empty()) {
                let value: Value = serde_json::from_str(line).map_err(|e| e.to_string())?;
                let operation = value
                    .get("operation")
                    .and_then(Value::as_str)
                    .unwrap_or("union");
                let k = value
                    .get("k")
                    .map_or(Some(3), Value::as_u64)
                    .ok_or("Invalid k")?;
                let mut row = value.clone();
                let fields = row.as_object_mut().ok_or("Input object required")?;
                fields.remove("operation");
                fields.remove("k");
                let input: cut_risk::Input =
                    serde_json::from_value(row).map_err(|e| e.to_string())?;
                if operation == "bracket" {
                    // The caller asserts its cut list is complete through support k.
                    println!(
                        "{}",
                        cut_risk::stats::bracket(&input, k as usize, true)
                            .map_err(str::to_string)?
                    );
                } else if operation == "union" {
                    let x = cut_risk::exact_union(input).map_err(str::to_string)?;
                    println!("{}", json!({"L":x,"bits":format!("{:016x}",x.to_bits())}));
                } else {
                    return Err("Unknown probability operation".into());
                }
            }
            Ok(())
        }
        "interval" => {
            let mut text = String::new();
            io::stdin()
                .read_to_string(&mut text)
                .map_err(|e| e.to_string())?;
            let pairs: Vec<[usize; 2]> = serde_json::from_str(&text).map_err(|e| e.to_string())?;
            let intervals: Result<Vec<_>, _> = pairs
                .iter()
                .map(|&[m, n]| cut_risk::stats::binomial_interval(m, n))
                .collect();
            emit(&json!(intervals.map_err(str::to_string)?), opts.get("out"))
        }
        _ => Err(format!("Unknown command: {command}\n{HELP}")),
    }
}
fn main() {
    if let Err(error) = execute() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
