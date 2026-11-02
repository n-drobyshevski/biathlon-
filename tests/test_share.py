"""Intranet DFlop (wiki) — auth gate, page rendering, byte-for-byte downloads,
404 / traversal, and clean decoys."""
import sys

import pytest


# ---------------------------------------------------------------- auth
@pytest.mark.parametrize("path", ["/", "/espace/basis", "/espace/basis/export-usr02",
                                  "/telecharger/SAP_USR02_export.csv"])
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
    assert c.get("/").status_code == 302                    # still not authenticated


def test_login_is_rate_limited(share_module):
    share_module._FAILS.clear()
    c = share_module.app.test_client()
    codes = [c.post("/login", data={"identifiant": "x", "motdepasse": "y"}).status_code
             for _ in range(8)]
    assert 429 in codes
    share_module._FAILS.clear()


def test_logout_redirects_and_deauths(share):
    assert share.get("/").status_code == 200
    share.get("/logout")
    r = share.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


# ---------------------------------------------------------------- browsing
def test_home_and_every_space_and_page_render(share, share_module):
    assert share.get("/").status_code == 200
    for s in share_module.SPACES:
        assert share.get("/espace/" + s["key"]).status_code == 200, s["key"]
        for p in s["pages"]:
            url = "/espace/" + s["key"] + "/" + p["slug"]
            assert share.get(url).status_code == 200, url


def test_home_lists_spaces_and_recent_activity(share):
    home = share.get("/").data.decode()
    assert "Intranet DFlop" in home
    assert "Incident" in home and "INC-2026-11-01" in home
    assert "Activité récente" in home


# ---------------------------------------------------------------- downloads
def _attach_urls(share_module):
    return {name: "/telecharger/" + name for name in share_module.FILES}


def test_every_attachment_byte_identical(share, share_module, dist):
    urls = _attach_urls(share_module)
    assert len(urls) == 8
    for name, url in urls.items():
        r = share.get(url)
        assert r.status_code == 200, name
        assert r.data == (dist / name).read_bytes(), name


def test_poster_and_photo_not_served_here(share):
    assert share.get("/telecharger/decaflop_poster.png").status_code == 404
    assert share.get("/telecharger/transition_shot.jpg").status_code == 404


@pytest.mark.parametrize("path", [
    "/espace/nope",
    "/espace/basis/nope",
    "/telecharger/nope.txt",
    "/telecharger/decaflop_poster.png",
    "/telecharger/..%2f..%2fapp.py",
    "/espace/basis/export-usr02/../../../etc/passwd",
])
def test_unknown_and_traversal_are_404(share, path):
    assert share.get(path).status_code == 404


def test_missing_file_shows_unavailable_and_404(share, monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules["share_app"], "HANDOUT_DIR", str(tmp_path))
    page = share.get("/espace/basis/export-usr02").data.decode()
    assert "pas encore disponible" in page
    assert "/telecharger/SAP_USR02_export.csv" not in page       # no dead download link
    assert share.get("/telecharger/SAP_USR02_export.csv").status_code == 404


# ---------------------------------------------------------------- content safety
def test_pages_render_attachments_and_meta(share):
    page = share.get("/espace/chrono/capture-wifi-cabine").data.decode()
    assert "Pièces jointes" in page
    assert "timing_booth.pcap" in page
    assert "modifié par" in page                                 # wiki meta line


def test_no_page_leaks_secrets(share, share_module):
    for s in share_module.SPACES:
        for p in s["pages"]:
            html = share.get("/espace/" + s["key"] + "/" + p["slug"]).data.decode()
            assert "TRIATHLON{" not in html
            assert "transition2026" not in html
            assert "DecaFlop2026" not in html


def test_no_search_box(share):
    # the wiki has no text input that echoes back (only the login form has inputs)
    assert "<input" not in share.get("/").data.decode()
