"""Floating shortcuts (fab.py): hub, DécaFlop site and Intranet DécaFlop link to
each other, plus Outils; the intranet button shows on the hub and the site only
after a first successful login to the share."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHALLENGES = {"04": "04-web-idor", "06": "06-web-sqli", "10": "10-web-jwt", "11": "11-web-gitleak",
              "12": "12-web-ssti", "14": "14-sap-gateway"}
COPIES = [ROOT / "hub" / "app", ROOT / "challenges" / "01-web-staff" / "app", ROOT / "share" / "app"] + \
    [ROOT / "challenges" / d / "app" for d in CHALLENGES.values()]
DOMAIN = "ctf.example.com"
PASSWORD = "transition2026"


def fab_html(page):
    m = re.search(r'<nav class="dfab".*?</nav>', page, re.S)
    assert m, "no shortcuts on the page"
    return m.group(0)


def hrefs(nav):
    return re.findall(r'href="([^"]+)"', nav)


def unlock(client, domain="localhost"):
    client.set_cookie("dflop_intranet", "1", domain=domain)


# ---------------------------------------------------------------- shared copies
def test_fab_copies_identical():
    for rel in ("fab.py", "static/fab.css"):
        copies = {str(p): (p / rel).read_bytes() for p in COPIES}
        assert len(set(copies.values())) == 1, (rel, copies.keys())


# ---------------------------------------------------------------- hub
def test_hub_links_site_and_tools_not_intranet(hub, hub_module, monkeypatch):
    monkeypatch.setattr(hub_module, "CYBERCHEF_PORT", "8090")
    monkeypatch.setattr(hub_module, "TERMINAL_PORT", "8091")
    monkeypatch.setattr(hub_module, "CTFD_PORT", "8000")
    for path, code in (("/", 200), ("/outils", 200), ("/nope", 404)):
        r = hub.get(path)
        assert r.status_code == code
        nav = fab_html(r.data.decode())
        links = hrefs(nav)
        assert "http://localhost:8001/" in links                 # main button: the site
        assert "/outils" in links                                # Outils, and its menu's last entry
        assert "http://localhost:8090/" in links and "http://localhost:8091/" in links
        assert "http://localhost:8000/" in links and "Tableau des scores" in nav
        assert "8020" not in nav and "Intranet" not in nav       # locked before the first login
    assert '/static/fab.css' in hub.get("/").data.decode()


def test_hub_shows_intranet_once_unlocked(hub, monkeypatch):
    unlock(hub)
    nav = fab_html(hub.get("/").data.decode())
    assert 'href="http://localhost:8020/"' in nav and "data-dfab-new" in nav
    monkeypatch.setenv("SHARE_URL", f"https://share.{DOMAIN}/")
    assert f'href="https://share.{DOMAIN}/"' in fab_html(hub.get("/").data.decode())


def test_hub_shortcuts_skip_unconfigured_tools(hub, hub_module, monkeypatch):
    monkeypatch.setattr(hub_module, "CYBERCHEF_PORT", "")
    monkeypatch.setattr(hub_module, "TERMINAL_PORT", "")
    monkeypatch.setattr(hub_module, "CTFD_PORT", "")
    monkeypatch.setattr(hub_module, "SCOREBOARD_URL", "")
    nav = fab_html(hub.get("/").data.decode())
    assert "CyberChef" not in nav and "Terminal" not in nav and "Tableau des scores" not in nav
    assert 'href="/outils"' in nav                               # still reaches the Outils tab


# ---------------------------------------------------------------- site
def test_site_links_hub_and_tools(shop):
    for path, code in (("/", 200), ("/presse", 200), ("/nope", 404)):
        r = shop.get(path, base_url="http://10.0.0.5:8001")
        assert r.status_code == code
        nav = fab_html(r.data.decode())
        links = hrefs(nav)
        assert "http://10.0.0.5:8080/" in links                  # main button: the hub
        assert "http://10.0.0.5:8080/outils" in links
        assert "http://10.0.0.5:8090/" in links and "http://10.0.0.5:8091/" in links
        assert "http://10.0.0.5:8000/" in links                  # scoreboard (CTFd)
        assert "8020" not in nav


def test_site_intranet_after_login_and_online(shop, monkeypatch):
    unlock(shop, "10.0.0.5")
    nav = fab_html(shop.get("/", base_url="http://10.0.0.5:8001").data.decode())
    assert 'href="http://10.0.0.5:8020/"' in nav
    unlock(shop, f"site.{DOMAIN}")      # browsers send the share's Domain= cookie here
    online = fab_html(shop.get("/", base_url=f"http://site.{DOMAIN}",
                               headers={"X-Forwarded-Proto": "https"}).data.decode())
    for sub in ("hub", "share", "cyberchef", "terminal", "ctfd"):
        assert f'href="https://{sub}.{DOMAIN}/' in online, sub
    monkeypatch.setenv("HUB_URL", "http://pi.lan:9000")
    assert 'href="http://pi.lan:9000/"' in fab_html(shop.get("/").data.decode())


def test_staff_portal_has_no_shortcuts(shop):
    assert "dfab" not in shop.get("/staff-portal-7f3a9").data.decode()


# ---------------------------------------------------------------- share
def _set_cookies(resp):
    return [h for h in resp.headers.getlist("Set-Cookie") if h.startswith("dflop_intranet=")]


def test_share_login_unlocks_and_logout_keeps_it(share_module):
    c = share_module.app.test_client()
    bad = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": "nope"})
    assert bad.status_code == 401 and not _set_cookies(bad)
    assert c.get_cookie("dflop_intranet") is None
    ok = c.post("/login", data={"identifiant": "equipe-it", "motdepasse": PASSWORD})
    assert ok.status_code == 302
    (cookie,) = _set_cookies(ok)
    assert "Max-Age=2592000" in cookie and "SameSite=Lax" in cookie and "Domain" not in cookie
    c.get("/logout")
    assert c.get_cookie("dflop_intranet").value == "1"


def test_share_online_cookie_covers_lab_domain(share_module):
    c = share_module.app.test_client()
    ok = c.post("/login", base_url=f"http://share.{DOMAIN}",
                data={"identifiant": "equipe-it", "motdepasse": PASSWORD})
    (cookie,) = _set_cookies(ok)
    assert f"Domain={DOMAIN}" in cookie


def test_share_pages_link_hub_site_and_tools(share, share_anon):
    for client, path in ((share_anon, "/login"), (share, "/"), (share, "/documents")):
        page = client.get(path).data.decode()
        nav = fab_html(page)
        links = hrefs(nav)
        assert "http://localhost:8080/" in links and "http://localhost:8001/" in links
        assert "http://localhost:8080/outils" in links
        assert "data-dfab-new" not in nav                        # nothing to unlock here
        assert page.index("/static/fab.css") < page.index("</head>")
    assert share_anon.get("/static/fab.css").status_code == 200  # styled on the login page too


def test_hub_buttons_sit_in_the_tabs_bar_corner():
    css = (ROOT / "hub" / "app" / "static" / "crise.css").read_text()
    assert "--dfab-gap:8px; --dfab-lift:0px;" in css                 # desktop: bottom-right corner
    assert ":root{--dfab-lift:35px;--dfab-gap:8px}" in css            # phone: just above the tabs
    assert "padding:0 184px 0 12px" in css                           # tabs never run under them


# ---------------------------------------------------------------- challenges
def _challenge(num, monkeypatch, **env):
    import importlib.util
    import sys
    for k, v in {"FLAG": "TRIATHLON{fab}", **env}.items():
        monkeypatch.setenv(k, v)
    path = ROOT / "challenges" / CHALLENGES[num] / "app" / "app.py"
    spec = importlib.util.spec_from_file_location(f"fab_ch_{num}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.app.test_client()


def test_every_challenge_page_links_hub_and_tools(monkeypatch):
    for num in ("04", "06", "10", "12", "14"):
        c = _challenge(num, monkeypatch)
        path = "/sap/logon" if num == "14" else "/"                  # 14: "/" redirects to the SAP logon
        page = c.get(path, base_url="http://10.0.0.5:8004").data.decode()
        nav = fab_html(page)
        assert "http://10.0.0.5:8080/" in hrefs(nav), num            # main button: cellule de crise
        assert "http://10.0.0.5:8080/outils" in hrefs(nav), num      # Outils
        assert "8020" not in nav, num                                # intranet locked before login
        assert "/static/fab.css" in page and c.get("/static/fab.css").status_code == 200, num
        c.set_cookie("dflop_intranet", "1", domain="10.0.0.5")
        nav = fab_html(c.get(path, base_url="http://10.0.0.5:8004").data.decode())
        assert "http://10.0.0.5:8020/" in hrefs(nav), num            # unlocked after the share login


def test_challenge_shortcuts_leave_api_and_text_alone(monkeypatch):
    c10 = _challenge("10", monkeypatch)
    r = c10.get("/api/token")
    assert r.mimetype == "application/json" and "dfab" not in r.data.decode()
    c14 = _challenge("14", monkeypatch)
    c14.post("/sap/logon", data={"user": "basis_dflop", "pass": "Trans1tion!2026"})   # Level 3 logon
    r = c14.get("/sap/gw/reginfo")
    assert r.mimetype == "text/plain" and "dfab" not in r.data.decode()
    r = _challenge("12", monkeypatch).post("/generate", data={"name": "{{7*7}}"})
    assert "49" in r.data.decode() and "dfab" in r.data.decode()  # SSTI still works, page decorated


def test_gitleak_shortcuts_on_home_page_only(monkeypatch, tmp_path):
    site = tmp_path / "site"
    (site / ".git").mkdir(parents=True)
    (site / ".git" / "HEAD").write_text("ref: refs/heads/master\n")
    (site / "index.html").write_text("<html><head></head><body><h1>Chronométrage</h1></body></html>")
    c = _challenge("11", monkeypatch, SITE_DIR=str(site))
    for path in ("/", "/index.html"):
        assert "http://localhost:8080/" in hrefs(fab_html(c.get(path).data.decode()))
    # what git-dumper crawls is served exactly as on disk, no extra links
    assert "dfab" not in c.get("/.git/").data.decode()
    assert c.get("/.git/HEAD").data == b"ref: refs/heads/master\n"
