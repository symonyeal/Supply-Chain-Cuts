//! Read-only local static server. p: requested asset; R: canonical site root.
use std::{
    fs,
    io::{Read, Write},
    net::TcpListener,
    path::Path,
    time::Duration,
};

/// Content type by file extension; any other extension is served as opaque bytes.
const MIME: [(&str, &str); 7] = [
    ("html", "text/html; charset=utf-8"),
    ("css", "text/css; charset=utf-8"),
    ("js", "text/javascript; charset=utf-8"),
    ("json", "application/json"),
    ("csv", "text/csv; charset=utf-8"),
    ("png", "image/png"),
    ("svg", "image/svg+xml"),
];

/// Status, body and content type answering `method` on `path`: only GET and HEAD, and only
/// existing files inside R.
fn response(
    root: &Path,
    method: &str,
    path: &str,
) -> Result<(&'static str, Vec<u8>, &'static str), String> {
    let file = root.join(path).canonicalize();
    if !["GET", "HEAD"].contains(&method) {
        return Ok((
            "405 Method Not Allowed",
            b"GET or HEAD required".to_vec(),
            "text/plain",
        ));
    }
    let Some(p) = file.ok().filter(|p| p.starts_with(root) && p.is_file()) else {
        return Ok(("404 Not Found", b"Not found".to_vec(), "text/plain"));
    };
    let extension = p.extension().and_then(|s| s.to_str()).unwrap_or("");
    let mime = MIME
        .iter()
        .find(|(x, _)| *x == extension)
        .map_or("application/octet-stream", |(_, m)| m);
    Ok(("200 OK", fs::read(p).map_err(|e| e.to_string())?, mime))
}

pub fn serve(root: &Path, address: &str) -> Result<(), String> {
    let root = root.canonicalize().map_err(|e| e.to_string())?;
    let listener = TcpListener::bind(address).map_err(|e| e.to_string())?;
    eprintln!(
        "Supply Chain Cuts: http://{}",
        listener.local_addr().map_err(|e| e.to_string())?
    );
    for stream in listener.incoming() {
        let mut stream = stream.map_err(|e| e.to_string())?;
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .map_err(|e| e.to_string())?;
        let mut bytes = [0; 8192];
        let n = match stream.read(&mut bytes) {
            Ok(n) => n,
            Err(_) => continue,
        };
        let request = String::from_utf8_lossy(&bytes[..n]);
        let parts: Vec<&str> = request
            .lines()
            .next()
            .unwrap_or("")
            .split_whitespace()
            .collect();
        if parts.len() < 2 {
            continue;
        }
        let method = parts[0];
        let raw = parts[1].split('?').next().unwrap_or("");
        let path = if raw == "/" {
            "index.html"
        } else {
            raw.trim_start_matches('/')
        };
        let (status, body, mime) = response(&root, method, path)?;
        let header = format!(
            "HTTP/1.1 {status}\r\nContent-Type: {mime}\r\nContent-Length: {}\r\nConnection: close\r\nX-Content-Type-Options: nosniff\r\n\r\n",
            body.len()
        );
        if stream.write_all(header.as_bytes()).is_ok() && method != "HEAD" {
            let _ = stream.write_all(&body);
        }
    }
    Ok(())
}
