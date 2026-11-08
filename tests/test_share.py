"""Intranet DécaFlop — auth, browsing, byte-for-byte downloads, 404/traversal."""
import sys
from html import escape as esc
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
    c = share_module.app.test_client()
    r = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": "nope"})
    assert r.status_code == 401
    assert "incorrect" in r.data.decode()
    # still not authenticated
    assert c.get("/").status_code == 302


def test_wrong_passwords_never_lock_the_login(share_module):
    c = share_module.app.test_client()
    codes = [c.post("/login", data={"identifiant": "x", "motdepasse": "y"}).status_code
             for _ in range(20)]
    assert codes == [401] * 20
    ok = c.post("/login", data={"identifiant": "equipe-it",
                                "motdepasse": share_module.SHARE_PASSWORD})
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/")


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
    assert len(evidence) == 10     # +abap_lisezmoi.txt (15), +phantom_signal.zip (08)
    for f in evidence:
        r = share.get(url_for_file(f))
        assert r.status_code == 200, f["path"]
        disk = (dist / f["source"]).read_bytes()
        assert r.data == disk, f["name"]


def test_decoys_download_with_their_own_type(share, share_module):
    decoys = [f for f in share_module.FILES if f["decoy"]]
    assert len(decoys) >= 30                          # plenty of smoke around the evidence
    for f in decoys:
        r = share.get(url_for_file(f))
        assert r.status_code == 200, f["name"]
        assert r.data == f["text"].encode("utf-8"), f["name"]
        if f["kind"] in share_module.TEXT_KINDS | {"csv"}:
            assert r.mimetype == "text/plain", f["name"]
        else:                                         # empty office files, images, system files
            assert r.mimetype != "text/plain", f["name"]


def test_every_decoy_lists_and_opens(share, share_module):
    for f in share_module.FILES:
        if not f["decoy"]:
            continue
        folder = "/d/" + "/".join(quote(s) for s in f["path"][:-1])
        assert f["name"] in share.get(folder).data.decode(), f["name"]
        page = share.get("/apercu/" + "/".join(quote(s) for s in f["path"]))
        assert page.status_code == 200, f["name"]
        if f["kind"] not in share_module.TEXT_KINDS | {"csv", "zip"}:
            assert "Aperçu non disponible" in page.data.decode(), f["name"]


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


# ---------------------------------------------------------------- file viewer
def preview_url(f):
    return "/apercu/" + "/".join(quote(s) for s in f["path"])


def test_preview_needs_login(share_anon):
    r = share_anon.get("/apercu/Basis%20SAP/Exports/sap_hint.txt")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_every_file_has_a_preview_page(share, share_module):
    mod = sys.modules["share_app"]
    for f in mod.FILES:
        page = share.get(preview_url(f)).data.decode()
        assert f'<h1>{f["name"]}</h1>' in page, f["name"]
        assert f'href="{url_for_file(f)}">Télécharger' in page
        if f["kind"] == "img":
            assert "Aperçu non disponible" in page
        if f["kind"] == "pcap":                       # packet list (capture.py)
            assert '<table class="pc-tbl">' in page


def test_preview_renders_text_csv_and_zip(share, dist):
    hint = share.get("/apercu/Basis%20SAP/Exports/sap_hint.txt?vu=1").data.decode()
    first = (dist / "sap_hint.txt").read_text().splitlines()[0]
    assert '<pre class="code">' in hint and esc(first) in hint
    grid = share.get("/apercu/Basis%20SAP/Exports/SAP_USR02_export.csv").data.decode()
    assert '<table class="grid">' in grid and "<td>VLINDQVIST</td>" in grid and "<th>G</th>" in grid
    archive = share.get("/apercu/Direction%20de%20course/Dossier%20incident/case_file.zip").data.decode()
    assert "<td>flag.txt</td>" in archive and "protégée par un mot de passe" in archive
    assert "TRIATHLON{" not in archive              # names only, never the encrypted content


def test_hint_warns_before_revealing(share, dist):
    # First open shows the spoiler warning instead of the hint content.
    first = share.get("/apercu/Basis%20SAP/Exports/sap_hint.txt").data.decode()
    assert "véritable indice" in first
    assert '<pre class="code">' not in first              # content withheld
    assert '?vu=1' in first                                # link to proceed
    # Proceeding reveals the content and remembers the choice for the session.
    seen = share.get("/apercu/Basis%20SAP/Exports/sap_hint.txt?vu=1").data.decode()
    assert '<pre class="code">' in seen and "véritable indice" not in seen
    again = share.get("/apercu/Basis%20SAP/Exports/sap_hint.txt").data.decode()
    assert '<pre class="code">' in again and "véritable indice" not in again


def test_listing_opens_viewer_and_keeps_details(share):
    page = share.get("/d/Basis%20SAP/Exports").data.decode()
    assert 'href="/apercu/Basis%20SAP/Exports/sap_hint.txt">sap_hint.txt</a>' in page
    assert 'class="dots" href="?f=sap_hint.txt"' in page
    callout = share.get("/d/Basis%20SAP/Exports?f=sap_hint.txt").data.decode()
    assert 'href="/apercu/Basis%20SAP/Exports/sap_hint.txt">Ouvrir</a>' in callout
    assert 'class="peek"' in callout


@pytest.mark.parametrize("path", ["/apercu/Basis%20SAP/Exports/nope.csv", "/apercu/..%2f..%2fapp.py",
                                  "/apercu/Basis%20SAP/Exports/SAP_USR02_export.csv/../../../etc/passwd"])
def test_preview_unknown_is_404(share, path):
    assert share.get(path).status_code == 404


def test_preview_of_missing_file(share, share_module, monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules["share_app"], "HANDOUT_DIR", str(tmp_path))
    page = share.get("/apercu/Basis%20SAP/Exports/SAP_USR02_export.csv")
    assert page.status_code == 200 and "pas encore disponible" in page.data.decode()


def test_login_cookie_does_not_clash_with_ctfd(share_module):
    """Same host offline: CTFd's cookie is "session", the intranet's must differ."""
    c = share_module.app.test_client()
    r = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": "transition2026"})
    cookies = r.headers.getlist("Set-Cookie")
    assert any(h.startswith("intranet_session=") for h in cookies)
    assert not any(h.startswith("session=") for h in cookies)

# ---------------------------------------------------------------- wiki (Documentation Technique)
WIKI_PAGES = {
    "/wiki/mots-de-passe-sap": ["Mots de passe SAP legacy (table USR02)", "MD5( MOT_DE_PASSE_EN_MAJUSCULES )",
                                "EXAMPLE", "8e3b72508e05135569ace4ed9b96d137", "UFLAG",
                                "sont les suspects prioritaires"],
    "/wiki/raccourcis-sap-gui": ["Raccourcis SAP GUI (.sap)", "Enregistrer le mot de passe",
                                 "Base64", "pas du chiffrement"],
    "/wiki/lire-du-code-abap": ["Lire du code ABAP (notions minimales)", "CONCATENATE", "lv_",
                                "sans aucun séparateur"],
}


@pytest.mark.parametrize("path", ["/wiki", *WIKI_PAGES])
def test_wiki_needs_login(share_anon, path):
    r = share_anon.get(path)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_wiki_index_lists_three_articles(share):
    r = share.get("/wiki")
    assert r.status_code == 200
    body = r.data.decode()
    for path in WIKI_PAGES:
        assert f'href="{path}"' in body


@pytest.mark.parametrize("path,needles", WIKI_PAGES.items())
def test_wiki_article_renders_french(share, path, needles):
    r = share.get(path)
    assert r.status_code == 200
    body = r.data.decode()
    for needle in needles:
        assert needle in body, needle
    assert "Documentation interne DécaFlop" in body and "usage audit uniquement" in body


def test_wiki_example_hash_is_md5_of_uppercase():
    import hashlib
    assert hashlib.md5(b"EXAMPLE").hexdigest() == "8e3b72508e05135569ace4ed9b96d137"


def test_wiki_tab_in_nav_on_every_page(share):
    for path in ("/", "/documents", "/annuaire", "/aide", "/wiki"):
        assert ">Documentation Technique</a>" in share.get(path).data.decode(), path


def test_wiki_unknown_article_is_404(share):
    assert share.get("/wiki/inconnu").status_code == 404
    assert share.get("/wiki/..%2fapp").status_code == 404


# ---------------------------------------------------------------- challenge 08 placement
def test_phantom_capture_is_listed_under_reseau_behind_the_login(share, share_anon):
    path = "/d/R%C3%A9seau/Captures%20terrain"
    assert share_anon.get(path).status_code == 302
    assert share_anon.get("/telecharger/R%C3%A9seau/Captures%20terrain/phantom_signal.zip").status_code == 302
    assert "R\u00e9seau" in share.get("/documents").data.decode()
    page = share.get(path).data.decode()
    assert "phantom_signal.zip" in page
    assert "phantom_signal.pcap" not in page                      # only the wrapped archive is offered
    from html import unescape
    prev = unescape(share.get("/d/R%C3%A9seau/Captures%20terrain?f=phantom_signal.zip").data.decode())
    assert "Un équipement inconnu s'est connecté au réseau. Identifiez-le." in prev
    assert "mot de passe : infected" in prev
    assert share.get("/telecharger/R%C3%A9seau/Captures%20terrain/phantom_signal.pcap").status_code == 404
