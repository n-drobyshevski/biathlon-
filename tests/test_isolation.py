"""Player isolation: one shared instance per service, so nothing a player does
may stick for the other teams (see handouts/HOSTING.md)."""
import importlib.util
import json
import pathlib
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLASK_APPS = ["hub", "staff", "share", "idor", "sqli", "jwt", "gitleak", "ssti", "sapgw"]


def _ssti(monkeypatch, flag="TRIATHLON{iso_real}"):
    monkeypatch.setenv("FLAG", flag)
    path = ROOT / "challenges" / "12-web-ssti" / "app" / "app.py"
    spec = importlib.util.spec_from_file_location("ssti_iso", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ssti_iso"] = mod
    spec.loader.exec_module(mod)
    return mod.app.test_client()


def _gen(c, name):
    return c.post("/generate", data={"name": name})


# ------------------------------------------------------------------ 12 SSTI
def test_ssti_payload_changes_do_not_reach_the_next_player(monkeypatch):
    c = _ssti(monkeypatch)
    assert "49" in _gen(c, "{{7*7}}").data.decode()                       # still SSTI
    _gen(c, "{{ config.update(FLAG='TRIATHLON{fake}') }}")
    _gen(c, "{{ cycler.__init__.__globals__.os.environ.update(FLAG='x') }}")
    page = _gen(c, "{{ config.FLAG }}").data.decode()
    assert "TRIATHLON{iso_real}" in page and "TRIATHLON{fake}" not in page


def test_ssti_busy_loop_is_cut_off(monkeypatch):
    c = _ssti(monkeypatch)
    t = time.monotonic()
    r = _gen(c, "{% for i in range(10**10) %}{% endfor %}")
    assert r.status_code == 500 and time.monotonic() - t < 6
    assert _gen(c, "Astrid").status_code == 200                           # still serving


def test_ssti_template_error_is_reported(monkeypatch):
    r = _gen(_ssti(monkeypatch), "{{ x")
    assert r.status_code == 500 and "TemplateSyntaxError" in r.data.decode()


# ------------------------------------------------------------------ share
def test_share_lockout_is_per_browser(share_module):
    share_module._FAILS.clear()
    a, b = share_module.app.test_client(), share_module.app.test_client()
    a.get("/login")
    b.get("/login")                                    # same IP, other browser
    codes = [a.post("/login", data={"identifiant": "x", "motdepasse": "y"}).status_code
             for _ in range(8)]
    assert 429 in codes
    ok = b.post("/login", data={"identifiant": "equipe-it",
                                "motdepasse": share_module.SHARE_PASSWORD})
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/")
    share_module._FAILS.clear()


def test_share_per_ip_ceiling_stops_cookie_rotation(share_module):
    share_module._FAILS.clear()
    codes = []
    for _ in range(share_module._IP_LIMIT + 5):
        c = share_module.app.test_client()             # fresh cookie every time
        c.get("/login")
        codes.append(c.post("/login", data={"identifiant": "x", "motdepasse": "y"}).status_code)
    assert codes[-1] == 429
    share_module._FAILS.clear()


# ------------------------------------------------------------------ compose
def test_offline_compose_locks_every_app(compose_offline):
    for name in FLASK_APPS:
        svc = compose_offline["services"][name]
        assert svc["user"] == "65534:65534", name
        assert svc["cap_drop"] == ["ALL"], name
        assert "no-new-privileges:true" in svc["security_opt"], name
        assert svc.get("read_only") is True, name
        assert svc.get("init") is True, name
        assert 0 < svc.get("pids_limit", 0) <= 128, name
        assert any(t.startswith("/tmp:") for t in svc["tmpfs"]), name
    env = compose_offline["services"]["gitleak"]["environment"]
    assert env["SITE_DIR"].startswith("/tmp/")                   # read-only image


def test_offline_toolbox_gives_each_tab_its_own_user(compose_offline):
    tb = compose_offline["services"]["toolbox"]
    assert tb["command"][0] == "ttyd" and "-O" in tb["command"] and "-m" in tb["command"]
    assert tb["cap_drop"] == ["ALL"]
    assert sorted(tb["cap_add"]) == ["CHOWN", "KILL", "SETGID", "SETUID"]
    assert tb.get("read_only") is True and tb.get("init") is True
    assert any(t.startswith("/work:") and "size=" in t for t in tb["tmpfs"])
    shell = (ROOT / "tools" / "toolbox" / "shell.sh").read_text()
    assert "exec setpriv --reuid" in shell and "--rcfile /etc/toolbox/bashrc" in shell
    assert "ulimit -H -u" in shell
    docker = (ROOT / "tools" / "toolbox" / "Dockerfile").read_text()
    assert "USER player" not in docker and "joueur" in docker


@pytest.fixture(scope="module")
def compose_offline():
    import shutil
    import subprocess
    if not shutil.which("docker"):
        pytest.skip("docker not installed")
    r = subprocess.run(["docker", "compose", "--project-directory", str(ROOT),
                        "--env-file", "/dev/null", "-f", str(ROOT / "docker-compose.yml"),
                        "config", "--format", "json"], capture_output=True, text=True)
    if r.returncode and "compose" in r.stderr:
        pytest.skip("docker compose plugin missing")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)
