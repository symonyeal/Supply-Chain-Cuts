"""Verify frozen bytes on disk and in Git: python analysis/check_inputs.py RUN_ID."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from chokepoint.fetch import stamp


def main():
    root, out = Path("."), Path("results") / sys.argv[1]
    rows = []
    for x in json.loads((root / "SOURCES.lock").read_text(encoding="utf-8"))["sources"]:
        if x["committed"]:
            R = subprocess.run(["git", "cat-file", "blob", f"HEAD:{x['path']}"],
                               capture_output=True, check=True)
            rows.append({"path": x["path"], "expected": x["sha256"],
                         "git_sha256": hashlib.sha256(R.stdout).hexdigest()})
    result = {"stamp": stamp(), "files": rows,
              "git_bytes_match": all(x["expected"] == x["git_sha256"] for x in rows)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "checks.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(len(rows), "committed inputs; Git bytes match:", result["git_bytes_match"])
    assert result["git_bytes_match"]


if __name__ == "__main__":
    main()
