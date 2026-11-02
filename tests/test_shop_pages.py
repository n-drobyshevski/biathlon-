"""Espace presse, Actualités, discoverability, and placeholders."""
import sys


def test_presse_page(shop):
    html = shop.get("/presse").data.decode()
    assert "Espace presse" in html
    # download link with the download attribute, pointing at /medias
    assert 'href="/medias/decaflop_poster.png" download' in html
    assert "partout" in html                         # "partagez-la partout !"
    assert "120" in html                             # Marketing, poste 120
    assert "staff-portal" not in html


def test_actualites_list(shop):
    html = shop.get("/actualites").data.decode()
    for slug in ("parc-a-velos-pret", "navettes-spectateurs", "magasins-ouverts-week-end"):
        assert f"/actualites/{slug}" in html


def test_photo_post_shows_photo(shop):
    html = shop.get("/actualites/parc-a-velos-pret").data.decode()
    assert '<img src="/medias/transition_shot.jpg"' in html
    assert 'href="/medias/transition_shot.jpg"' in html        # link to full-size original
    assert "Photo : équipe DécaFlop" in html              # neutral caption, FR typography


def test_text_only_posts_have_no_photo(shop):
    for slug in ("navettes-spectateurs", "magasins-ouverts-week-end"):
        html = shop.get(f"/actualites/{slug}").data.decode()
        assert "/medias/" not in html


def test_unknown_post_is_404(shop):
    assert shop.get("/actualites/pas-un-article").status_code == 404


def test_discoverability_links(shop):
    home = shop.get("/").data.decode()
    assert "/actualites" in home                      # home teaser + footer
    assert "/presse" in home                          # footer
    tri = shop.get("/triathlon").data.decode()
    assert "/presse" in tri                            # championship mentions press area


def test_french_typography_in_new_pages(shop):
    # non-breaking space before ! and : in the generated pages
    assert " !" in shop.get("/presse").data.decode()
    assert " :" in shop.get("/actualites/parc-a-velos-pret").data.decode()


def test_placeholder_when_not_built(shop, monkeypatch, tmp_path):
    monkeypatch.setattr(sys.modules["shop"], "HANDOUT_DIR", str(tmp_path))
    presse = shop.get("/presse").data.decode()
    assert "bientôt disponible" in presse
    assert 'src="/medias/decaflop_poster.png"' not in presse     # no broken <img>
    post = shop.get("/actualites/parc-a-velos-pret").data.decode()
    assert "bientôt disponible" in post
    assert 'src="/medias/transition_shot.jpg"' not in post
