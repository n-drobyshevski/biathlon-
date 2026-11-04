"""Hub accounts: every sheet behind the sign-in, per-player mission statuses
saved on the Pi, and sign-in with the scoreboard (CTFd) account.

CTFd itself isn't run here: a small fake reproduces the login flow of CTFd
3.8.8 as read in its source (CTFd/auth.py login(), the CSRF nonce check of
CTFd/utils/initialization): GET /login sets a session nonce, POST /login needs
it, redirects on success and re-renders on a wrong password."""
import re
import secrets
import socket
import threading

import pytest
from flask import Flask, abort, jsonify, redirect, request, session
from werkzeug.serving import make_server

from conftest import hub_signin

USERS = [{"name": "Léa Dupont", "email": "lea@example.org", "password": "chrono-42"},
         {"name": "max", "email": "max@example.org", "password": "velo-2026"}]


def fake_ctfd():
    app = Flask("fake_ctfd")
    app.secret_key = "fake"
    app.config.update(SETUP=False, BUSY=False, LOGINS=0)

    @app.get("/login")
    def login_form():
        if app.config["SETUP"]:
            return redirect("/setup")
        session["nonce"] = secrets.token_hex(8)
        return (f'<form method="post"><input id="name" name="name"><input id="password" name="password">'
                f'<input id="nonce" name="nonce" type="hidden" value="{session["nonce"]}"></form>')

    @app.post("/login")
    def login():
        if app.config["BUSY"]:
            return "Too many requests", 429
        if not session.get("nonce") or request.form.get("nonce") != session["nonce"]:
            abort(403)
        name = request.form["name"]
        user = next((u for u in USERS if name in (u["name"], u["email"])), None)
        if user and user["password"] == request.form["password"]:
            session["user"] = user["name"]
            app.config["LOGINS"] += 1
            return redirect("/challenges")
        return "<p>Your username or password is incorrect</p>", 200

    @app.get("/api/v1/users/me")
    def me():
        if not session.get("user"):
            abort(403)
        return jsonify({"success": True, "data": {"name": session["user"], "id": 1}})

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect("/")

    return app


@pytest.fixture(scope="module")
def ctfd():
    app = fake_ctfd()
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield app, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture()
def fresh(hub_module, tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_DB", str(tmp_path / "notes.db"))
    monkeypatch.delenv("CTFD_INTERNAL_URL", raising=False)
    monkeypatch.delenv("HUB_LOGIN", raising=False)
    hub_module.notes.init()
    return hub_module


@pytest.fixture()
def with_ctfd(fresh, ctfd, monkeypatch):
    app, url = ctfd
    app.config.update(SETUP=False, BUSY=False)
    monkeypatch.setenv("CTFD_INTERNAL_URL", url)
    return app


def client(hub_module):
    return hub_module.app.test_client()


def csrf(c):
    for path in ("/connexion", "/bloc-notes"):
        m = re.search(r'name="csrf" value="([^"]+)"', c.get(path).data.decode())
        if m:
            return m.group(1)
    raise AssertionError("no CSRF field")


def signin(c, name, pw, suite="/"):
    return c.post("/connexion", data={"pseudo": name, "motdepasse": pw, "suite": suite, "csrf": csrf(c)})


# ------------------------------------------------------------------ sign-in first
@pytest.mark.parametrize("path, suite", [("/", "/"), ("/contexte", "/contexte"), ("/outils", "/outils"),
                                         ("/guide", "/guide"), ("/bloc-notes?n=3", "/bloc-notes%3Fn%3D3")])
def test_every_sheet_waits_for_the_signin(fresh, path, suite):
    r = client(fresh).get(path)
    assert r.status_code == 302 and r.headers["Location"] == "/connexion?suite=" + suite


def test_signin_page_and_assets_stay_open(fresh):
    c = client(fresh)
    page = c.get("/connexion").data.decode()
    assert "<h1>Connexion</h1>" in page and "location.hash" in page       # /#mission-05 survives sign-in
    assert c.get("/static/crise.css").status_code == 200
    assert c.get("/bloc-notes/liste").status_code == 403                    # JSON: no redirect
    assert c.post("/statut", json={"mission": "01", "state": "Résolu"}).status_code == 403


def test_signin_goes_back_where_the_player_was_going(fresh):
    c = client(fresh)
    r = signin(c, "lea", "motdepasse", "/contexte")
    assert r.status_code == 302 and r.headers["Location"] == "/contexte"
    assert c.get("/contexte").status_code == 200
    assert c.get("/connexion?suite=/outils").headers["Location"] == "/outils"      # already signed in


@pytest.mark.parametrize("evil", ["//evil.example/", "https://evil.example/", "/\\evil.example", "javascript:x"])
def test_no_redirect_to_another_site(fresh, evil):
    r = signin(client(fresh), "lea", "motdepasse", evil)
    assert r.headers["Location"] == "/"


def test_signout_returns_to_signin(fresh):
    c = hub_signin(client(fresh), "lea", "motdepasse")
    r = c.post("/deconnexion", data={"csrf": csrf(c)})
    assert r.headers["Location"] == "/connexion" and c.get("/").status_code == 302


def test_gate_can_be_turned_off(fresh, monkeypatch):
    monkeypatch.setenv("HUB_LOGIN", "0")
    page = client(fresh).get("/").data.decode()
    assert "Le secret du sponsor" in page and "window.HUB_STATUT=" not in page   # statuses stay in the browser


# ------------------------------------------------------------------ statuses per player
def status(c, mission, state):
    return c.post("/statut", json={"mission": mission, "state": state}, headers={"X-CSRF": csrf(c)})


def test_statuses_are_saved_per_player(fresh):
    lea = hub_signin(client(fresh), "lea", "motdepasse")
    max_ = hub_signin(client(fresh), "max", "motdepasse")
    page = lea.get("/").data.decode()
    assert '"empty": true' in page and 'window.HUB_STATUT' in page        # first visit: may import the browser's
    assert status(lea, "05", "En cours").status_code == 200
    assert status(lea, "01", "Résolu").status_code == 200
    page = lea.get("/").data.decode()
    assert 'id="mission-05" data-statut="En cours"' in page and 'id="mission-01" data-statut="Résolu"' in page
    assert re.search(r'data-k="05"[^>]*><option>À faire</option><option selected>En cours</option>', page)
    assert '"empty": false' in page
    assert lea.get("/statut").get_json() == {"05": "En cours", "01": "Résolu"}
    # isolated: max sees nothing of lea's
    assert max_.get("/statut").get_json() == {}
    assert 'id="mission-05" data-statut="À faire"' in max_.get("/").data.decode()
    # back to "À faire" removes the row
    status(lea, "05", "À faire")
    assert lea.get("/statut").get_json() == {"01": "Résolu"}


@pytest.mark.parametrize("body", [{"mission": "05", "state": "Fini"}, {"mission": "5", "state": "Résolu"},
                                  {"mission": "../x", "state": "Résolu"}, {"state": "Résolu"}, {}])
def test_status_input_is_checked(fresh, body):
    c = hub_signin(client(fresh), "lea", "motdepasse")
    assert c.post("/statut", json=body, headers={"X-CSRF": csrf(c)}).status_code == 400


def test_status_needs_csrf(fresh):
    c = hub_signin(client(fresh), "lea", "motdepasse")
    assert c.post("/statut", json={"mission": "01", "state": "Résolu"}).status_code == 400


# ------------------------------------------------------------------ scoreboard (CTFd) accounts
def test_ctfd_account_signs_in_with_its_exact_name(with_ctfd, fresh):
    c = client(fresh)
    page = c.get("/connexion").data.decode()
    assert "compte du <b>tableau des scores</b>" in page and "Pseudo ou e-mail du tableau des scores" in page
    r = signin(c, "lea@example.org", "chrono-42", "/bloc-notes")       # by e-mail
    assert r.status_code == 302 and r.headers["Location"] == "/bloc-notes"
    assert "Connecté : <b>Léa Dupont</b>" in c.get("/bloc-notes").data.decode()


def test_ctfd_wrong_password_and_unknown_user(with_ctfd, fresh):
    for name, pw in (("max", "nope"), ("nobody", "velo-2026")):
        r = signin(client(fresh), name, pw)
        assert r.status_code == 401 and "Pseudo ou mot de passe incorrect" in r.data.decode()
    assert not fresh.notes.connect().execute("SELECT * FROM players").fetchall()   # nothing stored


def test_ctfd_down_uses_the_last_good_password(with_ctfd, fresh, monkeypatch):
    assert signin(client(fresh), "max", "velo-2026").status_code == 302       # CTFd checks, hub remembers
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    dead = f"http://127.0.0.1:{s.getsockname()[1]}"
    s.close()
    monkeypatch.setenv("CTFD_INTERNAL_URL", dead)                              # CTFd stopped
    assert signin(client(fresh), "max", "velo-2026").status_code == 302
    assert signin(client(fresh), "max", "wrong").status_code == 503            # never accepts a new password
    r = signin(client(fresh), "lea@example.org", "chrono-42")                  # never signed in before
    assert r.status_code == 503 and "ne répond pas" in r.data.decode()


def test_ctfd_busy_or_not_set_up(with_ctfd, fresh):
    with_ctfd.config["BUSY"] = True
    r = signin(client(fresh), "max", "velo-2026")
    assert r.status_code == 503 and "Trop de connexions" in r.data.decode()
    with_ctfd.config.update(BUSY=False, SETUP=True)
    assert signin(client(fresh), "max", "velo-2026").status_code == 503


def test_ctfd_names_with_spaces_and_capitals_can_share(with_ctfd, fresh):
    lea = client(fresh)
    signin(lea, "Léa Dupont", "chrono-42")
    max_ = client(fresh)
    signin(max_, "max", "velo-2026")
    r = max_.post("/bloc-notes/nouveau", data={"nom": "Les Puces", "membres": "léa dupont", "csrf": csrf(max_)})
    pid = r.headers["Location"].split("n=")[1]
    assert "Les Puces" in lea.get(f"/bloc-notes?n={pid}").data.decode()


def test_nonce_is_read_in_either_attribute_order(fresh):
    auth = fresh.notes.ctfd_auth
    for html in ('<input id="nonce" name="nonce" type="hidden" value="abc123">',
                 '<input value="abc123" type="hidden" name="nonce">'):
        m = auth.NONCE_RE.search(html)
        assert (m.group(1) or m.group(2)) == "abc123"


def test_signin_page_uses_plain_punctuation(fresh, ctfd, monkeypatch):
    from html import unescape

    def text(page):
        return unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", page, flags=re.S)))
    pages = [client(fresh).get("/connexion").data.decode()]
    monkeypatch.setenv("CTFD_INTERNAL_URL", ctfd[1])
    pages.append(client(fresh).get("/connexion").data.decode())
    for page in pages:
        for ch in ("—", "–", "…", "·", "↗", "→"):
            assert ch not in text(page), repr(ch)


def test_compose_signs_in_with_ctfd_locally():
    import pathlib
    import yaml
    root = pathlib.Path(__file__).resolve().parents[1]
    env = yaml.safe_load((root / "docker-compose.yml").read_text())["services"]["hub"]["environment"]
    assert env["CTFD_INTERNAL_URL"] == "${CTFD_INTERNAL_URL:-http://ctfd:8000}"
    assert env["HUB_LOGIN"] == "${HUB_LOGIN:-1}"
