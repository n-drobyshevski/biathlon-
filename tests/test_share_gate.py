"""Challenge 01's staff portal hands out the Intranet DFlop login (soft gate).

The intranet's own authentication is unchanged; only the source of the
credentials moves (hub -> staff portal). The portal no longer prints the login:
it links the intranet and ships the credentials in its client-side script
(/static/tools.js), username in clear and password Base64-encoded. docker-compose
feeds the SAME env to both the staff (01) and intranet containers, so what the
script carries is exactly what the intranet accepts.
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


def test_staff_portal_hides_password_and_ships_it_base64_in_script(dist, monkeypatch):
    user, pw = "crew-test-07", "gate-pw-test-4821"
    monkeypatch.setenv("SHARE_USER", user)
    monkeypatch.setenv("SHARE_PASSWORD", pw)
    monkeypatch.setenv("FLAG", "TRIATHLON{staff_gate}")
    monkeypatch.setenv("SHARE_SECRET_KEY", "gate-secret")
    monkeypatch.setenv("HANDOUT_DIR", str(dist))
    if str(STAFF_APP) not in sys.path:
        sys.path.insert(0, str(STAFF_APP))

    staff = _load("staff_gate", STAFF_APP / "app.py")
    client = staff.app.test_client()

    # robots.txt lists only the staff portal (the dead /sap/ line is gone)
    robots = client.get("/robots.txt").data.decode()
    assert "staff-portal-7f3a9" in robots
    assert "/sap/" not in robots

    # the portal links the intranet + a button, keeps the flag and SAP note,
    # loads the tools script — and does NOT print the password anywhere in HTML
    page = client.get("/staff-portal-7f3a9", base_url="http://10.0.0.5:8001").data.decode()
    assert "http://10.0.0.5:8020" in page
    assert "TRIATHLON{staff_gate}" in page
    assert "SAP DFlop ERP" in page
    assert 'src="/static/tools.js"' in page
    assert pw not in page                                        # no plaintext password
    assert base64.b64encode(pw.encode()).decode() not in page   # nor its base64, in the HTML

    # the script carries the username in clear and the password Base64-encoded
    js = client.get("/static/tools.js")
    assert js.status_code == 200 and "javascript" in js.mimetype
    body = js.data.decode()
    assert '"' + user + '"' in body                             # username in clear
    assert pw not in body                                       # password is NOT in clear
    pass_b64 = re.search(r'pass_b64:\s*"([^"]+)"', body).group(1)
    recovered = base64.b64decode(pass_b64).decode()
    assert recovered == pw

    # and the intranet, from the same env, accepts exactly those recovered creds
    share = _load("share_gate", SHARE_APP / "app.py")
    share._FAILS.clear()
    assert share.app.test_client().post(
        "/login", data={"identifiant": user, "motdepasse": recovered}).status_code == 302
    share._FAILS.clear()
    assert share.app.test_client().post(
        "/login", data={"identifiant": user, "motdepasse": "not-the-password"}).status_code == 401

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
