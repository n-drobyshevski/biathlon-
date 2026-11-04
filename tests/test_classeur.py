"""Classeur: the interactive CSV preview on the intranet (static/classeur.js
over the static grid of csv_view). The static table stays as the fallback."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "share" / "app" / "static"
USR02 = "/apercu/Basis%20SAP/Exports/SAP_USR02_export.csv"
RADIOS = "/apercu/Logistique/Mat%C3%A9riel/inventaire_radios.csv"


def csv_data(page):
    m = re.search(r'<script type="application/json" id="csv-data">(.*?)</script>', page, re.S)
    assert m, "no #csv-data on the page"
    return m.group(1), json.loads(m.group(1))


def test_usr02_preview_embeds_rows_and_loads_classeur(share):
    page = share.get(USR02).data.decode()
    assert '<table class="grid">' in page and 'id="csv-sheet"' in page     # static fallback kept
    _, data = csv_data(page)
    rows = data["rows"]
    assert rows[0] == ["MANDT", "BNAME", "BCODE", "CODVN", "UFLAG", "TRDAT", "LTIME"]
    assert len(rows) == 6 and data["total"] == 6 and data["cut"] is False
    assert any(r[1] == "VLINDQVIST" and r[5] == "20261101" and r[6] == "184230" for r in rows)
    head = page.split("</head>", 1)[0]
    assert '/static/classeur.css' in head
    assert page.index('/static/classeur.js') > page.index('id="csv-data"')


def test_semicolon_csv_is_split(share):
    _, data = csv_data(share.get(RADIOS).data.decode())
    assert data["rows"][0] == ["id", "modele", "canal", "affecte_a", "etat"]
    assert data["rows"][5] == ["R05", "TK-3401", "4", "Arbitrage - velo", "batterie faible"]


def test_cells_cannot_break_out_of_the_data_script(share, share_module, monkeypatch):
    f = share_module.FILES_BY_PATH[("Logistique", "Matériel", "inventaire_radios.csv")]
    evil = "</script><script>alert(1)</script>"
    monkeypatch.setitem(f, "text", f"id;note\nR01;{evil}\nR02;a & b <i>\n")
    page = share.get(RADIOS).data.decode()
    raw, data = csv_data(page)
    assert "<" not in raw and ">" not in raw and "&" not in raw
    assert data["rows"][1][1] == evil and data["rows"][2][1] == "a & b <i>"
    assert "<script>alert(1)" not in page                         # nor in the static grid


def test_cut_flag_when_over_the_preview_limit(share, share_module, monkeypatch):
    f = share_module.FILES_BY_PATH[("Logistique", "Matériel", "inventaire_radios.csv")]
    monkeypatch.setattr(share_module, "PREVIEW_ROWS", 3)
    monkeypatch.setitem(f, "text", "a;b\n" + "".join(f"{i};x\n" for i in range(10)))
    _, data = csv_data(share.get(RADIOS).data.decode())
    assert len(data["rows"]) == 3 and data["total"] == 11 and data["cut"] is True


def test_other_previews_do_not_load_classeur(share):
    for url in ("/apercu/IT/Outils/wordlist.txt",
                "/apercu/Direction%20de%20course/Dossier%20incident/case_file.zip"):
        page = share.get(url).data.decode()
        assert "classeur" not in page and "csv-data" not in page, url


def test_assets_served_and_offline(share_anon):
    for name, kind in (("classeur.js", "javascript"), ("classeur.css", "css")):
        r = share_anon.get(f"/static/{name}")
        assert r.status_code == 200 and kind in r.mimetype
    js = (STATIC / "classeur.js").read_text(encoding="utf-8")
    css = (STATIC / "classeur.css").read_text(encoding="utf-8")
    for src in (js, css):
        assert not re.search(r"https?://", src)                     # no CDN, no remote font
    for call in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "innerHTML = data", ".innerHTML=v"):
        assert call not in js, call
    # cell text only ever goes through textContent / text nodes
    assert "innerHTML" not in js.replace("search.innerHTML = SVG_SEARCH", "").replace(
        "fb.innerHTML = SVG_FILTER", "")
