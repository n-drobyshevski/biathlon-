"""Challenge 01 hides the Intranet DécaFlop login in the public site (soft gate).

The share's own authentication is unchanged. The staff portal only gives the
share's ADDRESS and a hint; the login itself ships base64-encoded ("user:pass")
in /assets/site.config.js, which every public DécaFlop page loads. docker-compose
feeds the SAME env to both the staff (01) and share containers, so the login
hidden in the front-end is exactly the one the share accepts.
"""
import base64
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAFF_APP = ROOT / "challenges" / "01-web-staff" / "app"
SHARE_APP = ROOT / "share" / "app"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_site_front_end_hides_the_login_the_share_accepts(dist, monkeypatch):
    user, pw = "crew-test-07", "gate-pw-test-4821"
    monkeypatch.setenv("SHARE_USER", user)
    monkeypatch.setenv("SHARE_PASSWORD", pw)
    monkeypatch.setenv("FLAG", "TRIATHLON{staff_gate}")
    monkeypatch.setenv("SHARE_SECRET_KEY", "gate-secret")
    monkeypatch.setenv("HANDOUT_DIR", str(dist))
    if str(STAFF_APP) not in sys.path:
        sys.path.insert(0, str(STAFF_APP))
    staff = _load("staff_gate", STAFF_APP / "app.py")
    c = staff.app.test_client()

    # 01 staff portal (reached via robots.txt): share address + hint, NO login
    page = c.get("/staff-portal-7f3a9", base_url="http://10.0.0.5:8001").data.decode()
    assert "http://10.0.0.5:8020" in page                       # host-relative share URL
    assert "TRIATHLON{staff_gate}" in page                      # 01's own flag kept
    assert "SAP DFlop ERP" in page                              # SAP-user note kept
    assert "ressources front" in page                           # the hint
    assert pw not in page and user not in page

    # every public page loads the front config, which leaks user:pass in base64
    assert "/assets/site.config.js" in c.get("/").data.decode()
    js = c.get("/assets/site.config.js").data.decode()
    assert pw not in js                                         # not in clear text
    b64 = re.search(r'svc:\s*"([A-Za-z0-9+/=]+)"', js).group(1)
    shown_user, shown_pass = base64.b64decode(b64).decode().split(":", 1)
    assert (shown_user, shown_pass) == (user, pw)

    # the share, from the SAME env, accepts exactly those creds and rejects others
    share = _load("share_gate", SHARE_APP / "app.py")
    assert share.app.test_client().post(
        "/login", data={"identifiant": shown_user, "motdepasse": shown_pass}).status_code == 302
    assert share.app.test_client().post(
        "/login", data={"identifiant": shown_user, "motdepasse": "not-the-password"}).status_code == 401

    # both containers read the same env var, so they cannot drift
    assert staff.SHARE_USER == share.SHARE_USER == user
    assert staff.SHARE_PASSWORD == share.SHARE_PASSWORD == pw


def test_staff_and_share_defaults_match():
    # with no override, both default to the same literals
    staff_src = (STAFF_APP / "app.py").read_text()
    share_src = (SHARE_APP / "app.py").read_text()
    assert '"SHARE_USER", "equipe-it"' in staff_src
    assert '"SHARE_USER", "equipe-it"' in share_src
    assert '"SHARE_PASSWORD", "transition2026"' in staff_src
    assert '"SHARE_PASSWORD", "transition2026"' in share_src
