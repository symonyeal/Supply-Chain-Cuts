"""Archive member integrity and distinct annual BACI snapshots."""
import hashlib
import io
import zipfile

from data.research import fetch_baci as baci


def test_distinct_years_and_original_selected_bytes(tmp_path, monkeypatch):
    b = io.BytesIO()
    rows = b't,i,j,k,v,q\n2012,1,2,850760,3,4\n2012,1,2,999999,5,6\n'
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for t in (2012, 2013):
            z.writestr(f"BACI_HS12_Y{t}_V202601.csv", rows.replace(b"2012", str(t).encode()))
    monkeypatch.setattr(baci, "ROOT", tmp_path)
    monkeypatch.setattr(baci, "OUT", tmp_path)
    monkeypatch.setattr(baci, "read", lambda u, a, c: io.BytesIO(b.getvalue()[a:c+1]))
    with zipfile.ZipFile(b) as z:
        for t, x in zip((2012, 2013), z.infolist(), strict=True):
            e = baci.freeze("fixture", x, 0, "12", retrieved="2026-10-16")
            raw = z.read(x)
            selected = b'\n'.join(raw.split(b'\n')[:2]) + b'\n'
            assert (tmp_path / e["path"]).read_bytes() == selected
            assert e["archive_member_sha256"] == hashlib.sha256(raw).hexdigest()
            assert f"Y{t}_" in e["path"]
    assert len(list(tmp_path.glob("*_selected.csv"))) == 2
