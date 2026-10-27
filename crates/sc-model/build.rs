// HiGHS: pinned native LP solver; opt: release compiler flags; dst: installed library.
use std::env;

fn main() {
    let target = env::var("TARGET").unwrap();
    let opt = if target.contains("msvc") {
        "/O2 /DNDEBUG /fp:precise"
    } else {
        "-O2 -DNDEBUG -ffp-contract=off"
    };
    let crt = if env::var("CARGO_CFG_TARGET_FEATURE")
        .unwrap_or_default()
        .split(',')
        .any(|x| x == "crt-static")
    {
        "MultiThreaded"
    } else {
        "MultiThreadedDLL"
    };
    let dst = cmake::Config::new("HiGHS")
        .profile("Release")
        .cflag(opt)
        .cxxflag(opt)
        .define("FAST_BUILD", "ON")
        .define("BUILD_SHARED_LIBS", "OFF")
        .define("BUILD_CXX_EXE", "OFF")
        .define("BUILD_EXAMPLES", "OFF")
        .define("BUILD_TESTING", "OFF")
        .define("ZLIB", "OFF")
        .define("CMAKE_MSVC_RUNTIME_LIBRARY", crt)
        .define("CMAKE_INTERPROCEDURAL_OPTIMIZATION", "FALSE")
        .build();
    println!("cargo:rustc-link-search=native={}/lib", dst.display());
    println!("cargo:rustc-link-search=native={}/lib64", dst.display());
    println!("cargo:rustc-link-lib=static=highs");
    if target.contains("apple") {
        println!("cargo:rustc-link-lib=c++");
    } else if target.contains("linux") || target.contains("windows-gnu") {
        println!("cargo:rustc-link-lib=stdc++");
    }
    println!("cargo:rerun-if-changed=HiGHS/Version.txt");
    println!("cargo:rerun-if-changed=build.rs");
}
