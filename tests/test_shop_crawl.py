"""Crawl the storefront from '/': every internal link is reachable, the new
pages show up, and no HTML page leaks the staff portal."""
import re
from html import unescape

LINK_RE = re.compile(r'(?:href|action)="(/[^"#]*)', re.I)


def crawl(client):
    seen, queue, pages = {}, ["/"], {}
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        r = client.get(url)
        seen[url] = r.status_code
        if r.mimetype == "text/html":
            body = r.data.decode()
            pages[url] = body
            for href in LINK_RE.findall(body):
                href = unescape(href)
                if href not in seen:
                    queue.append(href)
    return seen, pages


def test_every_internal_link_200(shop):
    seen, _ = crawl(shop)
    broken = {u: s for u, s in seen.items() if s != 200}
    assert not broken, f"non-200 internal links: {broken}"


def test_new_pages_reachable_from_home(shop):
    seen, _ = crawl(shop)
    for url in ("/presse", "/actualites", "/actualites/parc-a-velos-pret",
                "/actualites/navettes-spectateurs", "/actualites/magasins-ouverts-week-end",
                "/medias/decaflop_poster.png", "/medias/transition_shot.jpg"):
        assert url in seen, f"{url} was not reachable by crawling from /"


def test_no_html_page_mentions_staff_portal(shop):
    _, pages = crawl(shop)
    leaks = [u for u, body in pages.items() if "staff-portal" in body.lower()]
    assert not leaks, f"pages mentioning the staff portal: {leaks}"
    # the portal is still only discoverable via robots.txt (text, not HTML)
    assert "staff-portal" in shop.get("/robots.txt").data.decode()
