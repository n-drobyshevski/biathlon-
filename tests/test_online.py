"""Optional online hosting (Cloudflare Tunnel + Access, see CLOUDFLARE.md).

Online mode only switches links from host:port to one subdomain per service.
Every test here also pins that the offline output is unchanged.
"""
import glob
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOMAIN = "ctf.example.com"
SUB = {"01": "site", "02": "site", "03": "site", "04": "idor", "05": "share", "06": "sqli",
       "07": "share", "08": "share", "09": "share", "10": "jwt", "11": "git", "12": "ssti", "13": "share",
       "14": "sapgw", "15": "share"}
# online: these each get their own internal network (shared with cloudflared
# only); everything else (challenges, share, toolbox) sits on `internal`
ONLINE_NET = {"ctfd": "scoreboard", "hub": "front", "cyberchef": "chef"}
SERVICES = ["hub", "staff", "share", "idor", "sqli", "jwt", "gitleak", "ssti", "sapgw",
            "ctfd", "cyberchef", "toolbox"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _readme(num):
    return glob.glob(str(ROOT / "challenges" / f"{num}-*" / "README.md"))[0]


# ------------------------------------------------------------ ctfd-setup.py
@pytest.fixture(scope="module")
def setup_mod():
    return _load("ctfd_setup_online", ROOT / "scripts" / "ctfd-setup.py")


def test_connect_mapping_covers_every_challenge(setup_mod):
    nums = sorted(pathlib.Path(p).parent.name[:2] for p in glob.glob(str(ROOT / "challenges" / "*" / "README.md")))
    assert sorted(setup_mod.CONNECT_SUB) == nums
    assert setup_mod.CONNECT_SUB == SUB


@pytest.mark.parametrize("num", sorted(SUB))
def test_online_connect_is_the_subdomain(setup_mod, num):
    online = setup_mod.parse_readme(_readme(num), "", DOMAIN)
    offline = setup_mod.parse_readme(_readme(num), "192.168.8.2")
    assert online["connection_info"] == f"https://{SUB[num]}.{DOMAIN}"
    assert f"**Connect:** `https://{SUB[num]}.{DOMAIN}`" in online["description"]
    assert f"https://hub.{DOMAIN}/#mission-{num}" in online["description"]
    assert "<CTF-HOST>" not in online["description"] and ":80" not in online["description"]
    # title line, points, category and hints are untouched
    for k in ("num", "name", "category", "value", "hints"):
        assert online[k] == offline[k], k
    # offline output is exactly what it was
    assert offline["connection_info"].startswith("http://192.168.8.2:80")
    assert f"http://192.168.8.2:8080/#mission-{num}" in offline["description"]


def _dry_run(*args, **env):
    e = {k: v for k, v in os.environ.items() if k not in ("HANDOUT_DIR", "CTF_DOMAIN")}
    e.update(env)
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "ctfd-setup.py"), "--dry-run",
                          "--env", str(ROOT / ".env.example"), *args],
                         capture_output=True, text=True, check=True, env=e).stdout
    return {ln[:2]: ln for ln in out.splitlines() if ln[:2].isdigit()}


def test_dry_run_base_domain(setup_mod):
    lines = _dry_run("--base-domain", DOMAIN)
    assert sorted(lines) == sorted(SUB)
    for num, sub in SUB.items():
        assert lines[num].endswith(f"connect=https://{sub}.{DOMAIN}"), lines[num]
        assert "flag ok" in lines[num]


def test_dry_run_domain_from_env_and_host_wins(setup_mod):
    assert _dry_run(CTF_DOMAIN=DOMAIN)["12"].endswith(f"connect=https://ssti.{DOMAIN}")
    # an explicit --host keeps the offline links even if CTF_DOMAIN is still set
    assert _dry_run("--host", "192.168.8.2", CTF_DOMAIN=DOMAIN)["12"].endswith(
        "connect=http://192.168.8.2:8012")


# -------------------------------------------------- intranet cross-links
def test_intranet_menu_follows_subdomains_online(monkeypatch):
    monkeypatch.setenv("FLAG", "TRIATHLON{idor_online}")
    c = _load("intra_idor_online", ROOT / "challenges" / "04-web-idor" / "app" / "app.py").app.test_client()
    online = c.get("/", base_url=f"http://idor.{DOMAIN}", headers={"X-Forwarded-Proto": "https"}).data.decode()
    for sub in ("share", "sqli", "jwt", "git", "ssti", "sapgw"):
        assert f'href="https://{sub}.{DOMAIN}/"' in online, sub
    assert not re.search(r'href="https?://[^"]*:\d+', online)
    offline = c.get("/", base_url="http://10.0.0.5:8004").data.decode()
    for port in (8020, 8006, 8010, 8011, 8012, 8014):
        assert f'href="http://10.0.0.5:{port}/"' in offline, port
    assert DOMAIN not in offline


def test_intranet_ignores_ips_and_unknown_hosts():
    from flask import Flask
    intranet = _load("intranet_online", ROOT / "share" / "app" / "intranet.py")
    app = Flask(__name__)
    for host, expect in (("10.0.0.5:8020", "http://10.0.0.5:8004/"),
                         ("192.168.8.2", "http://192.168.8.2:8004/"),
                         ("pi.local:8020", "http://pi.local:8004/"),
                         ("share.lan", "http://share.lan:8004/"),           # 2 labels: not a lab domain
                         (f"share.{DOMAIN}", f"http://idor.{DOMAIN}/"),     # scheme of the request
                         (f"SITE.{DOMAIN}", f"http://idor.{DOMAIN}/")):
        with app.test_request_context("/", base_url=f"http://{host}"):
            assert intranet.app_url("athletes") == expect, host


def test_staff_portal_share_link_online(dist, monkeypatch):
    staff_app = ROOT / "challenges" / "01-web-staff" / "app"
    monkeypatch.setenv("HANDOUT_DIR", str(dist))
    if str(staff_app) not in sys.path:
        sys.path.insert(0, str(staff_app))
    staff = _load("staff_online", staff_app / "app.py").app.test_client()
    page = staff.get("/staff-portal-7f3a9", base_url=f"http://site.{DOMAIN}",
                     headers={"X-Forwarded-Proto": "https"}).data.decode()
    assert f'href="https://share.{DOMAIN}"' in page
    page = staff.get("/staff-portal-7f3a9", base_url="http://10.0.0.5:8001").data.decode()
    assert 'href="http://10.0.0.5:8020"' in page


def test_gitleak_page_js_maps_ports_to_subdomains():
    ep = (ROOT / "challenges" / "11-web-gitleak" / "app" / "entrypoint.sh").read_text()
    js = ep.split("<script>", 1)[1].split("</script>", 1)[0]
    for port, sub in ((8020, "share"), (8004, "idor"), (8006, "sqli"), (8010, "jwt"),
                      (8012, "ssti"), (8014, "sapgw")):
        assert f"{port}:'{sub}'" in js
    assert "location.hostname+':'+a.dataset.port" in js          # offline rule kept


# ------------------------------------------------------------------ hub
def test_hub_labels_show_subdomain_when_url_set(hub, monkeypatch):
    monkeypatch.setenv("SHARE_URL", f"https://share.{DOMAIN}/")
    monkeypatch.setenv("SITE_URL", f"https://site.{DOMAIN}/")
    page = hub.get("/").data.decode()
    assert f'<span class="mute">(share.{DOMAIN})</span>' in page
    assert '<span class="mute">(:8020)</span>' not in page
    assert '<span class="mute">(:8004)</span>' in page            # not overridden: unchanged
    assert f"share.{DOMAIN}" in hub.get("/contexte").data.decode()


def test_hub_guide_online_git_step_matches(hub_module):
    assert any(hub_module.GUIDE_ONLINE_GIT[0] in s for s in hub_module.GUIDE["11"][2])


# --------------------------------------------------------------- banner
def test_terminal_banner_has_generic_online_note():
    banner = (ROOT / "tools" / "toolbox" / "shell.sh").read_text().split("BANNER", 2)[1]
    assert "wget http://<IP-du-Pi>:<port>/<chemin>" in banner     # offline wording kept
    assert "wget http://share:5000/<chemin>" in banner
    assert "gitleak" not in banner                                # no service-name spoiler


# -------------------------------------------------------------- compose
def test_base_compose_ports_follow_bind_addr():
    text = (ROOT / "docker-compose.yml").read_text()
    ports = re.findall(r"^\s*ports:\s*\[(.*)\]", text, re.M)
    assert len(ports) == len(SERVICES)
    for p in ports:
        assert re.fullmatch(r'"\$\{BIND_ADDR:-\}\$\{BIND_ADDR:\+:\}\d+:\d+"', p), p


def _compose_config(*files, **env):
    if not shutil.which("docker"):
        pytest.skip("docker not installed")
    e = {k: v for k, v in os.environ.items()
         if k not in ("BIND_ADDR", "TUNNEL_TOKEN", "CTF_DOMAIN")}
    e.update(env)
    args = ["docker", "compose", "--project-directory", str(ROOT), "--env-file", os.devnull]
    for f in files:
        args += ["-f", str(ROOT / f)]
    r = subprocess.run(args + ["config", "--format", "json"], capture_output=True, text=True, env=e)
    if r.returncode and "unknown" in r.stderr and "compose" in r.stderr:
        pytest.skip("docker compose plugin missing")
    return r


def test_offline_compose_publishes_on_every_interface():
    r = _compose_config("docker-compose.yml")
    assert r.returncode == 0, r.stderr
    cfg = json.loads(r.stdout)
    assert "cloudflared" not in cfg["services"]
    for name, svc in cfg["services"].items():
        assert all("host_ip" not in p for p in svc["ports"]), name    # = all interfaces, v4 + v6
        assert list(svc["networks"]) == ["default"], name


def test_online_overlay_isolates_every_service():
    files = ("docker-compose.yml", "docker-compose.cloudflare.yml")
    r = _compose_config(*files, TUNNEL_TOKEN="dummy", CTF_DOMAIN=DOMAIN)
    assert r.returncode == 0, r.stderr
    cfg = json.loads(r.stdout)
    for net in ONLINE_NET.values():
        assert cfg["networks"][net]["internal"] is True, net          # no egress anywhere
    assert not cfg["networks"]["edge"].get("internal")
    assert sorted(cfg["services"]) == sorted(SERVICES + ["cloudflared"])
    for name in SERVICES:
        svc = cfg["services"][name]
        assert list(svc["networks"]) == [ONLINE_NET.get(name, "internal")], name   # segmented
        assert all(p["host_ip"] == "127.0.0.1" for p in svc["ports"]), name
        assert "no-new-privileges:true" in svc["security_opt"], name
        assert svc["cap_drop"] == ["ALL"], name
        assert svc.get("read_only") is True, name                      # app cannot rewrite itself
        assert 0 < svc.get("pids_limit", 0) <= 256, name               # no fork bomb
        for v in svc.get("volumes", []):
            if v["type"] == "volume":                                # CTFd's own data volume
                assert (name, v["source"]) == ("ctfd", "ctfd-data"), name
                continue
            # the only host path mounted anywhere: the read-only player evidence
            assert v["type"] == "bind" and v["target"] == "/handouts" and v.get("read_only"), name
            assert v["source"] == str(ROOT / "handouts" / "dist"), name
    cf = cfg["services"]["cloudflared"]
    assert sorted(cf["networks"]) == sorted({"internal", "edge", *ONLINE_NET.values()})
    assert re.fullmatch(r"cloudflare/cloudflared:\d{4}\.\d+\.\d+@sha256:[0-9a-f]{64}", cf["image"])
    assert re.fullmatch(r"ctfd/ctfd:3\.8\.8@sha256:[0-9a-f]{64}", cfg["services"]["ctfd"]["image"])
    assert cf.get("read_only") is True and cf.get("pids_limit")
    tb = cfg["services"]["toolbox"]["command"]
    assert tb[0] == "ttyd" and "-O" in tb and "-W" in tb                # websocket origin check
    assert any(t.startswith("/work:") for t in cfg["services"]["toolbox"]["tmpfs"])
    # metrics/config/pprof on loopback only: never reachable from the challenges
    assert cf["command"] == ["tunnel", "--no-autoupdate", "--metrics", "127.0.0.1:20241", "run"]
    # fixed bridge name, matched by scripts/cloudflare-egress.sh
    assert cfg["networks"]["edge"]["driver_opts"]["com.docker.network.bridge.name"] == "ctf-edge"
    assert cf["environment"]["TUNNEL_TOKEN"] == "dummy" and "ports" not in cf
    env = cfg["services"]["hub"]["environment"]
    for key, sub in (("SITE_URL", "site"), ("IDOR_URL", "idor"), ("SQLI_URL", "sqli"),
                     ("JWT_URL", "jwt"), ("GIT_URL", "git"), ("SSTI_URL", "ssti"),
                     ("SAPGW_URL", "sapgw"), ("SHARE_URL", "share"), ("SCOREBOARD_URL", "ctfd"),
                     ("CYBERCHEF_URL", "cyberchef"), ("TERMINAL_URL", "terminal")):
        assert env[key] == f"https://{sub}.{DOMAIN}/", key
    assert env["CTFD_PORT"] == "" and cfg["services"]["ctfd"]["environment"]["REVERSE_PROXY"] == "true"


def test_online_overlay_refuses_without_token_or_domain():
    files = ("docker-compose.yml", "docker-compose.cloudflare.yml")
    assert _compose_config(*files, CTF_DOMAIN=DOMAIN).returncode != 0
    assert _compose_config(*files, TUNNEL_TOKEN="dummy").returncode != 0
