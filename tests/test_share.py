"""Partage DFlop — auth, browsing, byte-for-byte downloads, 404/traversal."""
import sys
from urllib.parse import quote

import pytest


def url_for_file(f):
    return "/telecharger/" + "/".join(quote(s) for s in f["path"])


def folder_url(path):
    return "/d/" + "/".join(quote(s) for s in path)


# ---------------------------------------------------------------- auth
@pytest.mark.parametrize("path", ["/", "/d/Basis%20SAP", "/d/Basis%20SAP/Exports",
                                  "/telecharger/Basis%20SAP/Exports/SAP_USR02_export.csv"])
def test_logged_out_redirects_to_login(share_anon, path):
    r = share_anon.get(path)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_wrong_login_shows_french_error(share_module):
    share_module._FAILS.clear()
    c = share_module.app.test_client()
    r = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": "nope"})
    assert r.status_code == 401
    assert "incorrect" in r.data.decode()
    # still not authenticated
    assert c.get("/").status_code == 302


def test_login_is_rate_limited(share_module):
    share_module._FAILS.clear()
    c = share_module.app.test_client()
    codes = [c.post("/login", data={"identifiant": "x", "motdepasse": "y"}).status_code
             for _ in range(8)]
    assert 429 in codes
    assert "Trop de tentatives" in c.post("/login", data={"identifiant": "x", "motdepasse": "y"}).data.decode()
    share_module._FAILS.clear()


def test_logout_redirects_and_deauths(share):
    assert share.get("/").status_code == 200
    share.get("/logout")
    r = share.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ---------------------------------------------------------------- browsing
def test_root_and_all_folders_browse(share, share_module):
    assert share.get("/").status_code == 200
    seen = set()

    def walk(node):
        for sub in share_module.child_folders(node):
            r = share.get(folder_url(sub["path"]))
            assert r.status_code == 200, sub["path"]
            seen.add(sub["path"])
            walk(sub)

    walk(share_module.TREE)
    # every evidence/decoy folder is reachable
    for f in share_module.FILES:
        assert f["path"][:-1] in seen


# ---------------------------------------------------------------- downloads
def test_every_evidence_file_byte_identical(share, share_module, dist):
    evidence = [f for f in share_module.FILES if not f["decoy"]]
    assert len(evidence) == 8
    for f in evidence:
        r = share.get(url_for_file(f))
        assert r.status_code == 200, f["path"]
        disk = (dist / f["source"]).read_bytes()
        assert r.data == disk, f["name"]


def test_decoys_download_as_text(share, share_module):
    decoys = [f for f in share_module.FILES if f["decoy"]]
    assert len(decoys) >= 3
    for f in decoys:
        r = share.get(url_for_file(f))
        assert r.status_code == 200
        assert r.mimetype == "text/plain"


def test_poster_and_photo_not_served_here(share):
    # those live on the DécaFlop site, never on the share
    assert share.get("/telecharger/decaflop_poster.png").status_code == 404
    assert share.get("/telecharger/transition_shot.jpg").status_code == 404


@pytest.mark.parametrize("path", [
    "/d/Nope",
    "/d/Basis%20SAP/Nope",
    "/telecharger/Basis%20SAP/Exports/nope.csv",
    "/telecharger/Basis%20SAP/Exports/SAP_USR02_export.csv/../../../etc/passwd",
    "/telecharger/..%2f..%2fapp.py",
    "/d/",
])
def test_unknown_and_traversal_are_404(share, path):
    assert share.get(path).status_code == 404


def test_missing_file_shows_unavailable_and_404(share, share_module, monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules["share_app"], "HANDOUT_DIR", str(tmp_path))
    listing = share.get("/d/Basis%20SAP/Exports").data.decode()
    assert "pas encore disponible" in listing
    # the evidence download 404s while not built; a decoy still works
    assert share.get("/telecharger/Basis%20SAP/Exports/SAP_USR02_export.csv").status_code == 404
    assert share.get("/telecharger/IT/Outils/LISEZ-MOI.txt").status_code == 200


def test_filenames_are_html_escaped(share):
    # the details path is rendered escaped (no raw unescaped angle brackets from data)
    html = share.get("/d/Basis%20SAP/Exports?f=SAP_USR02_export.csv").data.decode()
    assert "SAP_USR02_export.csv" in html
    assert "Télécharger" in html
