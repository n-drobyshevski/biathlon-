"""The hub no longer serves/links the two files; missions 02/03 point at the
site; and ctfd-setup gives 02/03 a connection link with no download links."""
import glob
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest
import re
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_hub_serves_no_files(hub):
    # the /fichiers route and the FILES whitelist are gone entirely
    for name in ("decaflop_poster.png", "transition_shot.jpg", "timing_booth.pcap",
                 "referee_usb.img", "case_file.zip"):
        assert hub.get("/fichiers/" + name).status_code == 404


def test_hub_has_no_files_whitelist(hub_module):
    assert not hasattr(hub_module, "FILES")


def test_missions_02_03_are_live_site(hub_module):
    missions = {m[0]: m for m in hub_module.MISSIONS}
    for num in ("02", "03"):
        _, _, _, _, _, _, live, files = missions[num]
        assert live == "site"
        assert files == []


def test_missions_evidence_are_live_share(hub_module):
    missions = {m[0]: m for m in hub_module.MISSIONS}
    for num in ("05", "07", "09", "13", "15"):
        _, _, _, _, _, _, live, files = missions[num]
        assert live == "share", num
        assert files == []


def test_every_mission_has_a_live_service(hub_module):
    # the hub serves no files, so every mission must be reached through a service
    for m in hub_module.MISSIONS:
        assert m[6], f"mission {m[0]} has no live service"


def test_hub_home_links_missions_to_service(hub):
    home = hub.get("/").data.decode()
    expect = {"02": ":8001", "03": ":8001", "05": ":8020", "07": ":8020",
              "09": ":8020", "13": ":8020", "15": ":8020"}
    for num, port in expect.items():
        start = home.find(f'id="mission-{num}"')
        end = home.find("mission-", start + 10)
        row = home[start:end if end != -1 else None]
        assert port in row, num
        assert "/fichiers/" not in row


def test_hub_contexte_links_share_without_creds(hub):
    ctx = hub.get("/contexte").data.decode()
    assert ":8020" in ctx                       # still names/links the share
    assert "mission 01" in ctx                  # points players at challenge 01
    assert "ressources du site" in ctx          # ...and where the login hides
    assert "transition2026" not in ctx          # no longer prints the credentials
    assert "equipe-it" not in ctx


def _load_ctfd_setup():
    spec = importlib.util.spec_from_file_location("ctfd_setup", ROOT / "scripts" / "ctfd-setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CONNECT_PORT = {"02": "8001", "03": "8001",
                "05": "8020", "07": "8020", "09": "8020", "13": "8020", "15": "8020"}


@pytest.mark.parametrize("num,port", sorted(CONNECT_PORT.items()))
def test_readme_connect_and_no_hub_links(num, port):
    mod = _load_ctfd_setup()
    path = glob.glob(str(ROOT / "challenges" / f"{num}-*" / "README.md"))[0]
    ch = mod.parse_readme(path, "192.168.8.2")
    assert ch["connection_info"] == f"http://192.168.8.2:{port}"
    assert "/fichiers/" not in ch["description"]
    assert "**Download:**" not in ch["description"]


def test_ctfd_setup_dry_run_links_share_not_hub():
    env = dict(os.environ)
    env.pop("HANDOUT_DIR", None)
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ctfd-setup.py"),
         "--dry-run", "--env", str(ROOT / ".env.example")],
        capture_output=True, text=True, check=True, env=env).stdout
    lines = {ln[:2]: ln for ln in out.splitlines() if ln[:2].isdigit()}
    for num in ("02", "03"):
        assert "connect=http://<CTF-HOST>:8001" in lines[num]
    for num in ("05", "07", "09", "13", "15"):
        assert "connect=http://<CTF-HOST>:8020" in lines[num], num
    assert "Download" not in out            # dry-run prints no download links at all
    assert "/fichiers/" not in out


# ---------------------------------------------------------------- Outils tab
HUB_HOST = "http://10.0.0.7:8080"


def _outils(hub, hub_module, monkeypatch, **conf):
    for k in ("CYBERCHEF_PORT", "TERMINAL_PORT", "CYBERCHEF_URL", "TERMINAL_URL", "CTFD_PORT", "SCOREBOARD_URL"):
        monkeypatch.setattr(hub_module, k, conf.get(k, ""))
    return hub.get("/outils", base_url=HUB_HOST).data.decode()


def test_outils_links_tools_on_the_players_host(hub, hub_module, monkeypatch):
    page = _outils(hub, hub_module, monkeypatch, CYBERCHEF_PORT="8090", TERMINAL_PORT="8091", CTFD_PORT="8000")
    for port in ("8090", "8091", "8000"):
        url = f"http://10.0.0.7:{port}/"
        assert f'class="open" href="{url}" target="_blank"' in page, port
        assert f'data-copy="{url}"' in page and f'data-check="{url}"' in page, port
    assert page.count('<article class="tile') == 3 and "Non configuré" not in page


def test_outils_without_addresses_says_not_configured(hub, hub_module, monkeypatch):
    page = _outils(hub, hub_module, monkeypatch)
    assert page.count("Non configuré") == 3 and 'data-check="' not in page
    assert 'class="open off"' in page and 'class="open" href' not in page


def test_outils_url_override(hub, hub_module, monkeypatch):
    page = _outils(hub, hub_module, monkeypatch, CYBERCHEF_URL="http://outils.local/chef", CYBERCHEF_PORT="8090")
    assert 'href="http://outils.local/chef/"' in page and ":8090" not in page


def test_outils_never_maps_tools_to_missions(hub, hub_module, monkeypatch):
    # no spoilers: the tools say what they can do, never which mission they solve
    page = _outils(hub, hub_module, monkeypatch, CYBERCHEF_PORT="8090", TERMINAL_PORT="8091", CTFD_PORT="8000")
    main = page.split('<main', 1)[1].split('</main>', 1)[0]     # the sheet, not the tab labels
    text = re.sub(r"<[^>]+>", " ", main)
    assert not re.search(r"\bmission", text, re.I) and "#mission-" not in page
    assert ".git" not in text


def test_hub_pages_use_plain_punctuation(hub, hub_module, monkeypatch):
    monkeypatch.setattr(hub_module, "CTFD_PORT", "8000")
    for path, code in (("/", 200), ("/contexte", 200), ("/outils", 200), ("/guide", 200),
                       ("/contacts", 200), ("/nope", 404)):
        r = hub.get(path)
        assert r.status_code == code, path
        text = unescape(re.sub(r"<[^>]+>", " ", r.data.decode()))
        for ch in ("—", "–", "…", "·", "↗", "→"):
            assert ch not in text, (path, repr(ch))
    banner = (ROOT / "tools" / "toolbox" / "shell.sh").read_text()
    for ch in ("—", "–", "→"):
        assert ch not in banner, repr(ch)


def test_terminal_banner_gives_no_mission_technique():
    # the banner's example is generic: no challenge port, no .git, no dump recipe
    banner = (ROOT / "tools" / "toolbox" / "shell.sh").read_text().split("BANNER", 2)[1]
    for bad in (".git", ":8011", "git-dumper http", " dump"):
        assert bad not in banner, bad
    # ttyd shows about 48 columns on a 390 px phone: keep every line within 46
    for line in banner.strip("'\n").splitlines():
        assert len(line) <= 46, line
    assert len(" Espace de travail : /work/session-XXXXXX") <= 46


# ----------------------------------------------------------- Mode guidé
GUIDE_PW = "debutant"


def _guide_conf(hub_module, monkeypatch, pw=GUIDE_PW):
    import hashlib
    monkeypatch.setattr(hub_module, "GUIDE_PASSWORD", pw)
    monkeypatch.setattr(hub_module, "GUIDE_TOKEN",
                        hashlib.sha256(("decaflop-guide:" + pw).encode()).hexdigest())


def test_guide_locked_without_cookie(hub, hub_module, monkeypatch):
    _guide_conf(hub_module, monkeypatch)
    page = hub.get("/guide").data.decode()
    assert 'name="motdepasse"' in page and "Déverrouiller" in page
    # no walkthrough leaks before unlocking
    assert "gcard" not in page and "Étape suivante" not in page


def test_guide_wrong_password_stays_locked(hub, hub_module, monkeypatch):
    _guide_conf(hub_module, monkeypatch)
    r = hub.post("/guide", data={"motdepasse": "nope"})
    assert r.status_code == 401
    assert 'name="motdepasse"' in r.data.decode() and "gcard" not in r.data.decode()


def test_guide_unlock_sets_cookie_and_shows_all_missions(hub, hub_module, monkeypatch):
    _guide_conf(hub_module, monkeypatch)
    r = hub.post("/guide", data={"motdepasse": GUIDE_PW})
    assert r.status_code == 302
    assert "guide=" in r.headers.get("Set-Cookie", "")
    page = hub.get("/guide").data.decode()        # test client keeps the cookie
    assert "gcard" in page and "Étape suivante" in page
    for num, *_ in hub_module.MISSIONS:
        assert f'id="guide-{num}"' in page, num
    assert page.count('<article class="gcard"') == len(hub_module.MISSIONS)


def test_guide_bogus_cookie_does_not_unlock(hub, hub_module, monkeypatch):
    _guide_conf(hub_module, monkeypatch)
    hub.set_cookie("guide", "1")
    page = hub.get("/guide").data.decode()
    assert 'name="motdepasse"' in page and "gcard" not in page


def test_guide_never_prints_a_flag_or_the_saboteur(hub, hub_module, monkeypatch):
    _guide_conf(hub_module, monkeypatch)
    hub.post("/guide", data={"motdepasse": GUIDE_PW})
    page = hub.get("/guide").data.decode()
    assert "TRIATHLON{" not in page
    for bad in ("lindqvist", "viktor", "CHIP7", "DecaFlop2026"):
        assert bad.lower() not in page.lower(), bad


def test_guide_covers_every_mission(hub_module):
    assert set(hub_module.GUIDE) == {m[0] for m in hub_module.MISSIONS}
    for num, (concept, tool, steps) in hub_module.GUIDE.items():
        assert concept and tool and 2 <= len(steps) <= 5, num


# ---------------------------------------------------------------- challenge 08 wiring
def test_08_hub_mission_points_at_the_share_not_the_file(hub, hub_module):
    m = {x[0]: x for x in hub_module.MISSIONS}["08"]
    assert m[1] == "Le Signal Fantôme" and m[2] == "Forensics" and m[3] == "Moyen" and m[4] == 125
    assert m[6] == "share" and m[7] == []                                # the share, no direct file link
    assert "adresse MAC" in m[5] and "IP" in m[5] and "Réseau / Captures terrain" in m[5]
    home = hub.get("/").data.decode()
    assert 'id="mission-08"' in home and "phantom_signal" not in home


def test_08_is_registered_for_ctfd(monkeypatch):
    """ctfd-setup builds challenges from the READMEs and the single FLAG_NN_* key in .env."""
    spec = importlib.util.spec_from_file_location("ctfd_setup", ROOT / "scripts" / "ctfd-setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ch = mod.parse_readme(str(ROOT / "challenges" / "08-forensics-phantom" / "README.md"), "192.168.8.2")
    assert (ch["num"], ch["name"], ch["category"], ch["value"]) == ("08", "Le Signal Fantôme", "Forensics", 125)
    assert len(ch["hints"]) == 1 and ch["hints"][0]["cost"] == 25
    assert ch["hints"][0]["content"].startswith("Filtrez le trafic HTTP. Cherchez un POST vers /sap/gw/register.")
    assert ch["connection_info"] == "http://192.168.8.2:8020" and "infected" in ch["description"]
    online = mod.parse_readme(str(ROOT / "challenges" / "08-forensics-phantom" / "README.md"), "", "ctf.example.com")
    assert online["connection_info"] == "https://share.ctf.example.com"      # online mode needs CONNECT_SUB["08"]
    env = mod.read_env(str(ROOT / ".env.example"))
    assert [k for k in env if k.startswith("FLAG_08_")] == ["FLAG_08_PHANTOM"]


# ---------------------------------------------------------------- CTFd hints for stuck points
def test_stuck_point_hints_and_costs():
    spec = importlib.util.spec_from_file_location("ctfd_hints", ROOT / "scripts" / "ctfd-setup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    def hints(num):
        path = next((ROOT / "challenges").glob(f"{num}-*/README.md"))
        return [(h["cost"], h["content"]) for h in mod.parse_readme(str(path), "x")["hints"]]
    h01 = hints("01")
    assert [c for c, _ in h01] == [0, 10, 20, 50]                     # free nudge first, credentials last
    assert "robots.txt" in h01[0][1] and "{{SHARE_USER}} / {{SHARE_PASSWORD}}" in h01[3][1]
    assert (75, "Le hash BCODE utilise MD5(MOT_DE_PASSE_EN_MAJUSCULES). Utilisez la wordlist courte "
                "/usr/share/wordlists/sap_default.txt dans le terminal. Ne lancez PAS rockyou.txt.") in hints("09")
    assert any(c == 50 and "jwt_secrets.txt" in t and "-m 16500" in t for c, t in hints("10"))
    assert any(c == 25 and "pas l'ordre des affectations" in t for c, t in hints("15"))
    for num in ("01", "09", "10", "15"):                              # titles stay Indice 1..n in order
        path = next((ROOT / "challenges").glob(f"{num}-*/README.md"))
        assert [h["title"] for h in mod.parse_readme(str(path), "x")["hints"]] == \
               [f"Indice {i}" for i in range(1, len(hints(num)) + 1)]
