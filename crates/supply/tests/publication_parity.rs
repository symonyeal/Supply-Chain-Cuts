//! `src/publication.rs` is shared byte for byte with Resilient-Supplier-Panels (`src/publication.rs`).
//! Both repositories pin the same hash; a change to either copy fails here until the pin and the
//! other copy are updated together.
use sha2::{Digest, Sha256};

const PIN: &str = "9e64f4ad4e91ea6fb27af70959da5916de8d83785c4bfb508827d47300ac8a93";

#[test]
fn publication_matches_the_shared_copy() {
    let text = include_str!("../src/publication.rs").replace("\r\n", "\n");
    assert_eq!(format!("{:x}", Sha256::digest(text.as_bytes())), PIN);
}
