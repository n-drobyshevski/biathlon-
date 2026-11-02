"""Challenge 01's staff portal hands out the Intranet DFlop login (soft gate).

The intranet's own authentication is unchanged; only the source of the
credentials moves (hub -> staff portal). docker-compose feeds the SAME env to
both the staff (01) and intranet containers, so the login shown on the portal is
exactly the one the intranet accepts.
"""
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


def test_staff_portal_reveals_login_the_share_accepts(dist, monkeypatch):
    user, pw = "crew-test-07", "gate-pw-test-4821"
    monkeypatch.setenv("SHARE_USER", user)
    monkeypatch.setenv("SHARE_PASSWORD", pw)
    monkeypatch.setenv("FLAG", "TRIATHLON{staff_gate}")
    monkeypatch.setenv("SHARE_SECRET_KEY", "gate-secret")
    monkeypatch.setenv("HANDOUT_DIR", str(dist))
    if str(STAFF_APP) not in sys.path:
        sys.path.insert(0, str(STAFF_APP))

    # 01 staff portal (reached via robots.txt): shows the share URL + login
    staff = _load("staff_gate", STAFF_APP / "app.py")
    page = staff.app.test_client().get("/staff-portal-7f3a9",
                                       base_url="http://10.0.0.5:8001").data.decode()
    assert "http://10.0.0.5:8020" in page                       # host-relative share URL
    assert "TRIATHLON{staff_gate}" in page                      # 01's own flag kept
    assert "SAP DFlop ERP" in page                              # SAP-user note kept
    shown_user = re.search(r"<dt>Identifiant</dt><dd><code>([^<]+)</code>", page).group(1)
    shown_pass = re.search(r"<dt>Mot de passe</dt><dd><code>([^<]+)</code>", page).group(1)
    assert (shown_user, shown_pass) == (user, pw)

    # the share, from the SAME env, accepts exactly those creds and rejects others
    share = _load("share_gate", SHARE_APP / "app.py")
    share._FAILS.clear()
    assert share.app.test_client().post(
        "/login", data={"identifiant": shown_user, "motdepasse": shown_pass}).status_code == 302
    share._FAILS.clear()
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
