"""Git must preserve frozen raw bytes under Windows newline settings."""
import subprocess
from pathlib import Path


def test_raw_bytes_survive_git_conversion(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / ".gitattributes").write_bytes(Path(".gitattributes").read_bytes())
    p = tmp_path / "data/raw/source.csv"
    p.parent.mkdir(parents=True)
    b = b"a,b\r\n1,2\r\n"
    p.write_bytes(b)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "core.autocrlf=true", "add", "."],
                   check=True, capture_output=True)
    R = subprocess.run(["git", "-C", str(tmp_path), "show", ":data/raw/source.csv"],
                       check=True, capture_output=True)
    assert R.stdout == b
