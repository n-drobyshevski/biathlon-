"""04 (Espace athlètes) and 12 (Certificats de finaliste) face competitors, who
reach them from the DécaFlop site's championship page: they wear the site's
public look (vitrine.py + decaflop.css), never the staff intranet chrome."""
import importlib.util
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = {"04": ROOT / "challenges" / "04-web-idor" / "app",
          "12": ROOT / "challenges" / "12-web-ssti" / "app"}
SITE_APP = ROOT / "challenges" / "01-web-staff" / "app"
DOMAIN = "ctf.example.com"


def _client(num, monkeypatch):
    monkeypatch.setenv("FLAG", "TRIATHLON{vitrine}")
    spec = importlib.util.spec_from_file_location(f"vitrine_{num}", PUBLIC[num] / "app.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.app.test_client()


def test_copies_identical_and_css_is_the_sites():
    for rel in ("vitrine.py", "static/vitrine.css"):
        assert (PUBLIC["04"] / rel).read_bytes() == (PUBLIC["12"] / rel).read_bytes(), rel
    site_css = (SITE_APP / "static" / "decaflop.css").read_bytes()
    for num, app in PUBLIC.items():
        assert (app / "static" / "decaflop.css").read_bytes() == site_css, num
        assert not (app / "intranet.py").exists(), num             # no intranet chrome left


def test_header_matches_the_sites_sections():
    src = (PUBLIC["04"] / "vitrine.py").read_text()
    shop = (SITE_APP / "shop.py").read_text()
    nav = re.search(r"^NAV = (\[.*?\])\n", src, re.S | re.M).group(1)
    site_nav = re.search(r"^NAV = (\[.*?\])\n", shop, re.S | re.M).group(1)
    assert eval(nav) == eval(site_nav)                              # same sections, same order


@pytest.mark.parametrize("num,path", [("04", "/"), ("04", "/infos"), ("04", "/profile/1042"),
                                      ("04", "/profile/1000"), ("12", "/")])
def test_public_pages_wear_the_site_look(monkeypatch, num, path):
    c = _client(num, monkeypatch)
    if num == "04":
        c.get("/login")
    page = c.get(path, base_url="http://10.0.0.5:8004").data.decode()
    assert '/static/decaflop.css' in page and '<header class="hd">' in page
    assert 'href="http://10.0.0.5:8001/triathlon" aria-current="page"' in page   # Triathlon section
    assert "DécaFlop <span>Intranet</span>" not in page                      # no staff suite bar
    assert "Applications" not in page and "Annuaire" not in page
    for port in (8006, 8010, 8011, 8014, 8020):                              # no internal tool advertised
        assert f":{port}/" not in page.split('<nav class="dfab"')[0], (path, port)
    assert "<!--" not in page and "{{" not in page


def test_public_links_follow_the_site_online(monkeypatch):
    c = _client("04", monkeypatch)
    page = c.get("/", base_url=f"http://idor.{DOMAIN}", headers={"X-Forwarded-Proto": "https"}).data.decode()
    head = page.split('<main', 1)[0]
    assert f'href="https://site.{DOMAIN}/triathlon"' in head and f'href="https://site.{DOMAIN}/"' in head
    assert not re.search(r'href="https?://[^"]*:\d+', head)


def test_challenges_still_work_in_the_new_look(monkeypatch):
    c04 = _client("04", monkeypatch)
    c04.get("/login")
    admin = c04.get("/profile/1000").data.decode()
    assert "TRIATHLON{vitrine}" in admin and "v.lindqvist" in admin           # IDOR unchanged
    assert "TRIATHLON{" not in c04.get("/profile/1042").data.decode()
    c12 = _client("12", monkeypatch)
    assert ">49<" in c12.post("/generate", data={"name": "{{7*7}}"}).data.decode()   # SSTI unchanged
    assert "TRIATHLON{vitrine}" in c12.post("/generate", data={"name": "{{config.FLAG}}"}).data.decode()


def test_site_championship_page_links_both_spaces():
    shop = (SITE_APP / "shop.py").read_text()
    assert "app_url('athletes')" in shop and "app_url('certificats')" in shop
