"""Locate the built native executables; tests that need one skip until it is built."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def native():
    """Return the release executable `name` from cargo's target directory, or skip."""
    release = Path(os.environ.get('CARGO_TARGET_DIR', ROOT / 'target')) / 'release'

    def find(name):
        path = release / (name + ('.exe' if os.name == 'nt' else ''))
        if not path.is_file():
            pytest.skip(f'{path} not built: cargo build --workspace --release --locked')
        return path

    return find
