"""Solve the handouts the way the hints say, in pure Python (no Docker).

07: the stick is a real FAT16 filesystem whose ROTATION.PNG was deleted: the
    entry is marked 0xE5, its clusters are free, its bytes are still there.
09: wordlist.txt is lower case and BCODE is MD5(UPPER(word)), so cracking needs
    the upper-case rule the hint now gives (hashcat -j u / john --rules=:u).
10: the same wordlist must crack the HS256 secret (HOSTING.md promises it).
"""
import base64
import hashlib
import hmac
import importlib.util
import io
import struct

from PIL import Image

from conftest import ROOT


def _fat(img):
    bps, spc, reserved, nfats, root_entries, total, _media, fat_size = struct.unpack_from(
        "<HBHBHHBH", img, 11)
    root_off = (reserved + nfats * fat_size) * bps
    data_sec = reserved + nfats * fat_size + root_entries * 32 // bps
    fat = struct.unpack_from(f"<{fat_size * bps // 2}H", img, reserved * bps)
    clusters = (total - data_sec) // spc
    entries = []
    for i in range(root_entries):
        e = img[root_off + 32 * i: root_off + 32 * (i + 1)]
        if e[0] == 0:
            break
        name, attr = e[:11], e[11]
        cluster, size = struct.unpack_from("<HI", e, 26)
        entries.append((name, attr, cluster, size))
    def read(cluster, size):
        off = (data_sec + (cluster - 2) * spc) * bps
        return img[off: off + size]
    return clusters, fat, entries, read, img[54:62]


def test_usb_is_fat16_with_the_png_deleted_but_recoverable(dist):
    img = (dist / "referee_usb.img").read_bytes()
    assert img[510:512] == b"\x55\xaa"
    clusters, fat, entries, read, fstype = _fat(img)
    assert fstype == b"FAT16   " and clusters >= 4085      # a reader really treats it as FAT16
    by_name = {e[0][1:]: e for e in entries}
    rot = by_name[b"OTATIONPNG"]
    assert rot[0][:1] == b"\xe5"                         # deleted entry
    assert all(fat[c] == 0 for c in range(rot[2], rot[2] + rot[3] // 512 + 1))   # chain freed
    png = read(rot[2], rot[3])                           # what icat recovers
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert Image.open(io.BytesIO(png)).size == (940, 150)
    # carving finds the very same bytes (binwalk / foremost / CyberChef route)
    start = img.index(b"\x89PNG")
    assert img[start: img.index(b"IEND", start) + 8] == png
    # live files are intact and chained
    live = by_name[b"ISEZMOITXT"]
    assert live[0][:1] == b"L" and fat[live[2]] == 0xFFFF
    assert "Ne rien stocker" in read(live[2], live[3]).decode("cp1252")


def _wordlist(dist):
    return (dist / "wordlist.txt").read_text().split()


def test_usr02_cracks_only_with_the_uppercase_rule(dist):
    rows = [r.split(",") for r in (dist / "SAP_USR02_export.csv").read_text().splitlines()[1:]]
    bcode = next(r[2] for r in rows if r[1] == "VLINDQVIST").lower()
    words = _wordlist(dist)
    assert not [w for w in words if hashlib.md5(w.encode()).hexdigest() == bcode]
    hits = [w.upper() for w in words if hashlib.md5(w.upper().encode()).hexdigest() == bcode]
    assert hits == ["CHIP7"]


def _jwt_app(monkeypatch, secret=None):
    if secret is None:
        monkeypatch.delenv("JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("JWT_SECRET", secret)
    path = ROOT / "challenges" / "10-web-jwt" / "app" / "app.py"
    spec = importlib.util.spec_from_file_location("jwt_app_solve", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _crack_hs256(token, words):
    head, payload, sig = token.split(".")
    want = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
    for w in words:
        if hmac.compare_digest(hmac.new(w.encode(), f"{head}.{payload}".encode(),
                                        hashlib.sha256).digest(), want):
            return w
    return None


def test_wordlist_cracks_the_results_api_secret(dist, monkeypatch):
    app = _jwt_app(monkeypatch).app
    token = app.test_client().get("/api/token").get_json()["token"]
    assert _crack_hs256(token, _wordlist(dist)) == "DecaFlop2026"


def test_wordlist_follows_a_rotated_jwt_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "Kalmar-Relay-77")
    spec = importlib.util.spec_from_file_location("gen_rotated", ROOT / "handouts" / "generate.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    gen.OUT = str(tmp_path)
    gen.gen_sap()
    words = (tmp_path / "wordlist.txt").read_text().split()
    token = _jwt_app(monkeypatch, "Kalmar-Relay-77").app.test_client().get("/api/token").get_json()["token"]
    assert _crack_hs256(token, words) == "Kalmar-Relay-77"
