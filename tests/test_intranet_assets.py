"""Intranet DécaFlop: shared chrome copies, realism rules, and every tool still
solves the same way after the redesign."""
import importlib.util
import os
import pathlib
import re
import subprocess
import sys
from urllib.parse import quote

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APPS = {
    "share": ROOT / "share" / "app",
    "01": ROOT / "challenges" / "01-web-staff" / "app",
    "04": ROOT / "challenges" / "04-web-idor" / "app",
    "06": ROOT / "challenges" / "06-web-sqli" / "app",
    "10": ROOT / "challenges" / "10-web-jwt" / "app",
    "11": ROOT / "challenges" / "11-web-gitleak" / "app",
    "12": ROOT / "challenges" / "12-web-ssti" / "app",
    "14": ROOT / "challenges" / "14-sap-gateway" / "app",
}
HOST = "http://10.0.0.5:9999"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _client(key, monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return _load(f"intra_{key}", APPS[key] / "app.py").app.test_client()


# ---------------------------------------------------------------- shared copies
def test_intranet_css_copies_identical():
    copies = {k: (p / "static" / "intranet.css").read_bytes() for k, p in APPS.items()}
    ref = copies["share"]
    assert all(v == ref for v in copies.values()), [k for k, v in copies.items() if v != ref]


def test_intranet_py_copies_identical():
    copies = {k: (p / "intranet.py").read_bytes() for k, p in APPS.items() if k != "11"}
    ref = copies["share"]
    assert all(v == ref for v in copies.values()), [k for k, v in copies.items() if v != ref]


def test_chrome_never_links_staff_portal_or_hub():
    src = (APPS["share"] / "intranet.py").read_text()
    assert "staff-portal" not in src
    assert "8080" not in src and "8001" not in src


# ---------------------------------------------------------------- share
def test_share_pages_render(share):
    for url in ("/", "/documents", "/annuaire", "/activite", "/aide", "/recherche", "/recherche?q=sap"):
        r = share.get(url)
        assert r.status_code == 200, url
        assert "staff-portal" not in r.data.decode()


def test_share_search_finds_every_evidence_file(share, share_module):
    for f in share_module.FILES:
        if f["decoy"]:
            continue
        stem = f["name"].rsplit(".", 1)[0][:8]
        page = share.get("/recherche?q=" + quote(stem)).data.decode()
        assert f["name"] in page, f["name"]


def test_share_search_escapes_query(share):
    page = share.get("/recherche?q=" + quote('<script>alert(1)</script>')).data.decode()
    assert "<script>alert(1)" not in page
    assert "&lt;script&gt;" in page


def test_share_search_is_accent_insensitive(share):
    assert "ZDFLOP_RESULT_EXPORT.abap" in share.get("/recherche?q=developpements").data.decode()


def test_share_bad_sort_is_ignored_not_echoed(share):
    r = share.get("/d/Basis%20SAP/Exports?tri=<x>&ordre=<y>")
    assert r.status_code == 200
    body = r.data.decode()
    assert "<x>" not in body and "&lt;x&gt;" not in body
    asc = share.get("/d/Basis%20SAP/Exports?tri=date&ordre=asc").data.decode()
    desc = share.get("/d/Basis%20SAP/Exports?tri=date&ordre=desc").data.decode()
    assert asc.index("SAP_USR02_export.csv") < asc.index("sap_hint.txt")
    assert desc.index("sap_hint.txt") < desc.index("SAP_USR02_export.csv")


def test_share_callout_has_download(share):
    body = share.get("/d/IT/Outils?f=wordlist.txt").data.decode()
    assert 'href="/telecharger/IT/Outils/wordlist.txt"' in body


def test_share_empty_folder(share):
    r = share.get("/d/Communication/Visuels")
    assert r.status_code == 200 and "Ce dossier est vide" in r.data.decode()


def test_share_directory_leaves_out_saboteur(share):
    page = share.get("/annuaire").data.decode()
    assert "lindqvist" not in page.lower()
    assert "Mette Sorensen" in page
    # unknown service filter falls back to everyone, never echoed
    other = share.get("/annuaire?service=<b>x</b>").data.decode()
    assert "<b>x</b>" not in other and "Mette Sorensen" in other


def test_share_decoys_hold_no_secrets(share_module):
    for f in share_module.FILES:
        if f["decoy"]:
            assert "TRIATHLON{" not in f["text"]
            assert "DecaFlop2026" not in f["text"]
            assert "transition2026" not in f["text"]


@pytest.mark.parametrize("login", ["equipe-it", "DECAFLOP\\equipe-it", "equipe-it@decaflop.local"])
def test_share_accepts_domain_forms(share_module, login):
    share_module._FAILS.clear()
    c = share_module.app.test_client()
    r = c.post("/login", data={"identifiant": login, "motdepasse": "transition2026"})
    assert r.status_code == 302 and c.get("/").status_code == 200


# ---------------------------------------------------------------- 01 staff portal
def test_staff_portal_speaks_in_world(shop):
    page = shop.get("/staff-portal-7f3a9", base_url="http://10.0.0.5:8001").data.decode()
    assert "robots.txt" not in page and "caché" not in page
    assert 'id="flag"' in page and "TRIATHLON{" in page
    assert "/static/intranet.css" in page


# ---------------------------------------------------------------- 04
def test_04_idor_still_works_and_no_player_talk(monkeypatch):
    c = _client("04", monkeypatch, FLAG="TRIATHLON{idor_x}")
    r = c.get("/login")
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile/1042")
    mine = c.get("/profile/1042").data.decode()
    admin = c.get("/profile/1000").data.decode()
    assert "TRIATHLON{idor_x}" in admin and "TRIATHLON{" not in mine
    assert "v.lindqvist" in admin
    for page in (mine, admin, c.get("/").data.decode()):
        for phrase in ("plus bas", "n'est-ce pas", "Pour la démo", "Vous consultez"):
            assert phrase not in page


# ---------------------------------------------------------------- 06
def test_06_sqli_error_and_bypass(monkeypatch):
    c = _client("06", monkeypatch, FLAG="TRIATHLON{sqli_x}")
    err = c.post("/login", data={"username": "'", "password": "x"}).data.decode()
    assert "Erreur SQL" in err
    ok = c.post("/login", data={"username": "' OR '1'='1' -- ", "password": "x"}).data.decode()
    assert "TRIATHLON{sqli_x}" in ok
    assert "TRIATHLON{" not in c.post("/login", data={"username": "a", "password": "b"}).data.decode()


# ---------------------------------------------------------------- 10
def test_10_docs_page_is_intranet(monkeypatch):
    c = _client("10", monkeypatch, FLAG="TRIATHLON{x}")
    home = c.get("/", base_url=HOST).data.decode()
    assert "/static/intranet.css" in home and "🔑" not in home
    assert HOST + "/api/token" in home


# ---------------------------------------------------------------- 11
def test_11_index_and_nginx_listing(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "python").write_text("#!/bin/sh\nexit 0\n")
    (bindir / "python").chmod(0o755)
    site = tmp_path / "site"
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", SITE_DIR=str(site), FLAG="TRIATHLON{g}")
    subprocess.run(["sh", str(APPS["11"] / "entrypoint.sh")], check=True, env=env, capture_output=True)
    c = _client("11", monkeypatch, SITE_DIR=str(site))
    index = c.get("/").data.decode()
    assert "/static/intranet.css" in index and "⏱" not in index
    assert c.get("/static/intranet.css").status_code == 200
    listing = c.get("/.git/").data.decode()
    assert "<h1>Index of /.git/</h1><hr><pre>" in listing
    assert re.search(r'<a href="HEAD">HEAD</a>\s+\d\d-[A-Z][a-z]{2}-\d{4} \d\d:\d\d\s+\d+', listing)
    assert c.get("/.git/HEAD").status_code == 200


# ---------------------------------------------------------------- 12
def test_12_ssti_still_evaluates(monkeypatch):
    c = _client("12", monkeypatch, FLAG="TRIATHLON{ssti_x}")
    assert ">49<" in c.post("/generate", data={"name": "{{7*7}}"}).data.decode()
    assert "TRIATHLON{ssti_x}" in c.post("/generate", data={"name": "{{config}}"}).data.decode()
    assert "TRIATHLON{" not in c.get("/").data.decode()


# ---------------------------------------------------------------- 14
def test_14_register_escapes_and_gives_flag(monkeypatch):
    c = _client("14", monkeypatch, FLAG="TRIATHLON{gw_x}")
    # The gateway now sits behind the Level 3 SAP logon; reach it unauthenticated
    # and you are bounced to the logon screen, not handed the flag.
    assert c.post("/sap/gw/register", data={"tp": "x"}).status_code == 302
    c.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})
    assert "TRIATHLON{" not in c.get("/").data.decode()
    page = c.post("/sap/gw/register", data={"tp": "<img src=x>"}).data.decode()
    assert "TRIATHLON{gw_x}" in page
    assert "<img src=x>" not in page and "&lt;img src=x&gt;" in page
    assert "cela vous donne" not in page
    assert c.get("/sap/gw/reginfo").mimetype == "text/plain"


def test_14_smgw_page_and_flag_env(monkeypatch):
    monkeypatch.delenv("FLAG", raising=False)
    c = _client("14", monkeypatch, FLAG_14="TRIATHLON{from_14}")
    c.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})
    assert c.get("/sap/cmd?cmd=smgw").headers["Location"].endswith("/sap/smgw")
    page = c.get("/sap/smgw").data.decode()
    assert "Fichiers de contrôle d'accès" in page and "FULL" in page and "sap-tooltip-bubble" in page
    assert "sap-statusbar--warning" in page and "TRIATHLON{" not in page
    done = c.post("/sap/gw/register", data={"tp": "Z_ANY", "host": "203.0.113.9"}).data.decode()
    assert "sap-statusbar--success" in done and "Journal d'enregistrement" in done
    assert "TRIATHLON{from_14}" in done
    # reginfo stays a plain-text ACL file and never carries the flag
    r = c.get("/sap/gw/reginfo")
    assert r.mimetype == "text/plain" and b"TRIATHLON{" not in r.data


def test_14_se16n_matches_usr02_csv_handout(monkeypatch, dist):
    """The on-screen USR02 table and SAP_USR02_export.csv are the same data."""
    import csv
    from html import unescape
    mod = _load("intra_14_se16n", APPS["14"] / "app.py")
    c = mod.app.test_client()
    assert c.get("/sap/se16n?table=USR02").status_code == 302          # behind the logon
    c.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})
    page = c.get("/sap/se16n?table=USR02").data.decode()
    handout = list(csv.DictReader(open(dist / "SAP_USR02_export.csv")))
    screen = {r["BNAME"]: r for r in mod.USR02}
    assert [r["BNAME"] for r in handout] == [r["BNAME"] for r in mod.USR02]
    for h in handout:
        r = screen[h["BNAME"]]
        assert (r["BCODE"], r["LDATE"], r["LTIME"], r["MANDT"]) == (h["BCODE"], h["TRDAT"], h["LTIME"], h["MANDT"])
        assert r["UFLAG"] == int(h["UFLAG"])
        assert h["BCODE"] in page                                       # and it is what is rendered
    assert page.count("sap-row-highlight") == 1 and "VLINDQVIST" in page.split("sap-row-highlight")[1][:80]
    assert "5 entrée(s) trouvée(s)" in unescape(page) and "TRIATHLON{" not in page
    bad = c.get("/sap/se16n?table=USR01").data.decode()
    assert "Table non autorisée pour cet audit." in bad and "sap-table" not in bad


def test_14_sm37_job_overview_and_log(monkeypatch):
    from html import unescape
    c = _client("14", monkeypatch, FLAG_14="TRIATHLON{sm37_x}")
    assert c.get("/sap/sm37").status_code == 302 and c.get("/sap/sm37/log?job=X").status_code == 302
    c.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})
    page = c.get("/sap/sm37").data.decode()
    assert page.count("sap-row-highlight") == 1 and page.count('href="/sap/sm37/log?job=ZDFLOP_RESULT_EXPORT"') == 1
    assert page.index("18:42:00") < page.index("02:00:00")            # most recent first
    log = c.get("/sap/sm37/log?job=ZDFLOP_RESULT_EXPORT")
    text = unescape(log.data.decode())
    assert log.status_code == 200 and "47 enregistrements sélectionnés" in text and "mission 15" in text
    assert "TRIATHLON{" not in page and "TRIATHLON{" not in text      # no flag on either screen
    for job in ("ZDFLOP_NIGHTLY_SYNC", "<b>x</b>", ""):
        r = c.get("/sap/sm37/log", query_string={"job": job})
        assert r.status_code == 404 and "Journal introuvable." in r.data.decode()
        assert "<b>x</b>" not in r.data.decode()


def test_15_abap_handout_is_short_split_and_never_whole(dist, share):
    flag = "TRIATHLON{sap_abap_test}"                       # FLAG_15_SAP_ABAP in conftest
    raw = (dist / "ZDFLOP_RESULT_EXPORT.abap").read_bytes()
    text = raw.decode("utf-8")
    assert b"\r" not in raw and text.count("\n") <= 40 and text.startswith("REPORT zdflop_result_export.")
    assert flag not in text                                 # never one literal
    parts = [re.search(rf"lv_partie{i} TYPE string VALUE '([^']*)'", text).group(1) for i in (1, 2, 3)]
    assert "".join(parts) == flag and parts[2].endswith("}")
    assert max(map(len, parts)) - min(map(len, parts)) <= 1  # roughly equal thirds
    assert re.search(r"CONCATENATE lv_partie1 lv_partie2 lv_partie3 INTO lv_jeton_final", text)
    leurre = [ln for ln in text.splitlines() if "lv_leurre" in ln]
    assert leurre and flag not in leurre[0] and "* Leurre" in text
    note = (dist / "abap_lisezmoi.txt").read_bytes()
    assert b"\r" not in note and flag.encode() not in note
    assert 6 <= note.decode("utf-8").count("\n") <= 8 and b"CONCATENATE" in note
    # players can actually fetch both files from the share
    for name in ("ZDFLOP_RESULT_EXPORT.abap", "abap_lisezmoi.txt"):
        assert share.get(f"/telecharger/Basis%20SAP/D%C3%A9veloppements/{name}").status_code == 200


# ------------------------------------------------- flag pages, copy rules
def test_flag_pages_have_no_long_dashes_or_player_talk(monkeypatch, shop):
    from html import unescape

    def text(s):
        return unescape(re.sub(r"<[^>]+>", " ", s))

    c04 = _client("04", monkeypatch, FLAG="TRIATHLON{a}")
    c04.get("/login")
    c10 = _client("10", monkeypatch, FLAG="TRIATHLON{b}")
    c14 = _client("14", monkeypatch, FLAG="TRIATHLON{c}")
    c14.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})
    pages = {
        "01 portal": shop.get("/staff-portal-7f3a9").data.decode(),
        "01 robots": shop.get("/robots.txt").data.decode(),
        "04 admin": c04.get("/profile/1000").data.decode(),
        "06 dashboard": _client("06", monkeypatch, FLAG="TRIATHLON{d}").post(
            "/login", data={"username": "' OR 1=1 -- ", "password": "x"}).data.decode(),
        "10 docs": c10.get("/").data.decode(),
        "12 cert": _client("12", monkeypatch, FLAG="TRIATHLON{e}").post(
            "/generate", data={"name": "Astrid Bjornsen"}).data.decode(),
        "14 register": c14.post("/sap/gw/register", data={"tp": "Z_X"}).data.decode(),
        "14 reginfo": c14.get("/sap/gw/reginfo").data.decode(),
    }
    for name, body in pages.items():
        for ch in ("—", "–", "·", "→", "…"):
            assert ch not in text(body), (name, repr(ch))
        for phrase in ("trop faible", "Pour savoir QUI", "récupérez"):
            assert phrase not in body, (name, phrase)
    # 04's audit trail is a dated table and still names the saboteur's accounts
    assert "<th style=\"width:160px\">Date</th>" in pages["04 admin"]
    assert "v.lindqvist" in pages["04 admin"] and "VLINDQVIST" in pages["04 admin"]
    assert "USR02" in pages["06 dashboard"]          # still points at challenge 09
