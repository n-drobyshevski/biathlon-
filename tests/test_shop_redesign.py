"""DécaFlop storefront redesign: read-only shop, whitelisted filters, product
pages, and copy free of the old nudges and of long dashes."""
import os
import re
import sys
from html import unescape

import pytest

from test_shop_crawl import crawl


def test_filters_and_sort_are_whitelisted(shop):
    page = shop.get("/natation?marque=<x>&prix=<y>&note=9&tri=<z>").data.decode()
    assert "<x>" not in page and "&lt;x&gt;" not in page
    assert "<z>" not in page and "&lt;z&gt;" not in page
    assert "5 produits" in page                      # unknown values fall back to no filter


def test_brand_filter_and_price_sort(shop_module, shop):
    catalogue = sys.modules["shop"]          # the storefront module app.py imports
    page = shop.get("/velo?tri=prix-croissant").data.decode()
    order = re.findall(r'class="card" href="/produit/([a-z0-9-]+)"', page)
    prices = [catalogue.num(catalogue.PRODUCTS[s]["price"]) for s in order]
    assert prices == sorted(prices) and len(order) == 5
    only = shop.get("/course-a-pied?marque=bofbof").data.decode()
    cards = re.findall(r'class="card" href="/produit/([a-z0-9-]+)"', only)
    assert cards == ["gels-energetiques"]


def test_every_product_page(shop_module, shop):
    catalogue = sys.modules["shop"]
    assert len(catalogue.PRODUCTS) == 15
    for slug in catalogue.PRODUCTS:
        for name in catalogue.photos(slug):
            assert os.path.isfile(os.path.join(catalogue.PHOTO_DIR, name + ".jpg")), name
        page = shop.get(f"/produit/{slug}").data.decode()
        assert f'<img src="/static/img/p/{slug}.jpg"' in page
        assert ('name="taille"' in page) or ("Taille unique" in page)
        assert 'aria-disabled="true">Ajouter au panier' in page
        assert "Disponibilité en magasin" in page and "DécaFlop Stade" in page
        assert "Acheteur vérifié" in page


@pytest.mark.parametrize("path", ["/compte", "/panier", "/informations-legales", "/location", "/atelier",
                                  "/destockage", "/aide", "/magasins", "/triathlon"])
def test_new_pages_render(shop, path):
    r = shop.get(path)
    assert r.status_code == 200
    assert "<form" not in r.data.decode().split("</header>", 1)[1]   # no form besides the search


def test_search_is_not_reflected(shop):
    page = shop.get("/?q=%3Cscript%3Ealert(1)%3C/script%3E").data.decode()
    assert "<script>alert(1)" not in page and "alert(1)" not in page
    assert "recherche en ligne est indisponible" in page


def test_copy_has_no_nudges_or_long_dashes(shop):
    _, pages = crawl(shop)
    assert len(pages) > 20
    for url, body in pages.items():
        text = unescape(re.sub(r"<[^>]+>", " ", body))
        for bad in ("robots.txt", "Tous flops", "ne pas le chercher", "politique de retour discutable"):
            assert bad not in text, (url, bad)
        for ch in ("—", "–", "→", "…", "·"):
            assert ch not in text, (url, repr(ch))


def test_intranet_pages_have_no_long_dashes(share):
    for url in ("/", "/documents", "/d/Basis%20SAP/Exports?f=sap_hint.txt", "/annuaire", "/activite", "/aide",
                "/recherche?q=sap"):
        text = unescape(re.sub(r"<[^>]+>", " ", share.get(url).data.decode()))
        for ch in ("—", "–", "·"):
            assert ch not in text, (url, repr(ch))


def test_every_image_on_the_site_loads(shop):
    _, pages = crawl(shop)
    srcs = {src for body in pages.values() for src in re.findall(r'<img src="(/[^"]+)"', body)}
    assert len(srcs) >= 17
    for src in srcs:
        if src.startswith("/medias/"):
            continue                                   # press/news files, covered by test_shop_media
        r = shop.get(src)
        assert r.status_code == 200 and r.mimetype == "image/jpeg", src
