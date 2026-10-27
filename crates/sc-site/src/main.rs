// root: repository path; runs: immutable result bundle names.
use std::path::Path;

fn main() {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let full = args.first().is_some_and(|v| v == "--full");
    if full {
        args.remove(0);
    }
    let Some(root) = args.first() else {
        eprintln!("Expected ROOT LIION_RUN [PV_RUN JOINT_RUN SEVERITY_RUN]");
        std::process::exit(1);
    };
    match sc_site::build(Path::new(root), &args[1..]) {
        Ok(data) => println!("{}", if full { data } else { sc_site::plain(data) }),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
