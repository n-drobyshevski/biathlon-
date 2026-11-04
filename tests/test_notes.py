"""Bloc-notes on the hub (hub/app/notes.py): pseudo sign-in, a private notepad
per player, shared notepads with members added by pseudo, saves that never
overwrite a teammate's version silently, CSRF, and the organizer commands."""
import re
from html import unescape

import pytest

PW = "secret-1"


@pytest.fixture()
def notes(hub_module, tmp_path, monkeypatch):
    """The notes module on a fresh, empty database for each test."""
    mod = hub_module.notes
    monkeypatch.setenv("NOTES_DB", str(tmp_path / "notes.db"))
    monkeypatch.delenv("NOTES_SHARED", raising=False)
    mod.init()
    return mod


@pytest.fixture()
def client(hub_module, notes):
    return hub_module.app.test_client()


def new_client(hub_module):
    return hub_module.app.test_client()


def csrf(c, path="/bloc-notes"):
    m = re.search(r'name="csrf" value="([^"]+)"', c.get(path).data.decode())
    assert m, "no CSRF field"
    return m.group(1)


def signin(c, pseudo, pw=PW):
    return c.post("/bloc-notes/connexion", data={"pseudo": pseudo, "motdepasse": pw, "csrf": csrf(c)})


def post(c, path, **data):
    data["csrf"] = csrf(c)
    return c.post(path, data=data)


def pad_ids(c):
    page = c.get("/bloc-notes").data.decode()
    return [int(x) for x in re.findall(r'href="/bloc-notes\?n=(\d+)"', page)]


def editor(c, pad_id):
    page = c.get(f"/bloc-notes?n={pad_id}").data.decode()
    m = re.search(r'data-rev="(\d+)"[^>]*data-csrf="([^"]+)"', page)
    return page, int(m.group(1)), m.group(2)


# ------------------------------------------------------------------ accounts
def test_signin_creates_pseudo_and_private_pad(client, hub_module):
    page = client.get("/bloc-notes").data.decode()
    assert 'action="/bloc-notes/connexion"' in page and "Se connecter" in page
    r = signin(client, "Lea")                                     # normalized to lower case
    assert r.status_code == 302
    cookie = r.headers.get("Set-Cookie", "")
    assert cookie.startswith("hub_session=") and "HttpOnly" in cookie   # not "session": the intranet's name
    page = client.get("/bloc-notes").data.decode()
    assert "Mes notes" in page and "Privé, visible par vous seul" in page and "Connecté : <b>lea</b>" in page
    assert 'class="who"' in client.get("/").data.decode()            # header chip on every sheet
    other = new_client(hub_module)
    assert signin(other, "lea", "wrong-pw").status_code == 401        # someone else's pseudo
    assert signin(other, "lea").status_code == 302


@pytest.mark.parametrize("pseudo", ["a", "x y", "root", "-lea", "é" * 3, "a" * 25])
def test_pseudo_rules(client, pseudo):
    assert signin(client, pseudo).status_code == 400


def test_short_password_refused(client):
    assert signin(client, "lea", "abc").status_code == 400


def test_post_needs_csrf(client):
    r = client.post("/bloc-notes/connexion", data={"pseudo": "lea", "motdepasse": PW})
    assert r.status_code == 400
    signin(client, "lea")
    (pid,) = pad_ids(client)
    r = client.post(f"/bloc-notes/{pid}/texte", json={"text": "x", "base_rev": 0})
    assert r.status_code == 400


def test_pages_need_signin(client):
    assert client.get("/bloc-notes/1/etat").status_code == 403
    signin(client, "lea")
    (pid,) = pad_ids(client)
    out = client.application.test_client()
    assert out.get(f"/bloc-notes/{pid}/etat").status_code == 403


# ------------------------------------------------------------------ shared pads
def make_pad(c, name, members):
    r = post(c, "/bloc-notes/nouveau", nom=name, membres=members)
    assert r.status_code == 302
    return int(r.headers["Location"].split("n=")[1]) if "n=" in r.headers["Location"] else None


def test_create_shared_pad_add_remove_leave(client, hub_module):
    max_, sam, zoe = new_client(hub_module), new_client(hub_module), new_client(hub_module)
    for c, p in ((client, "lea"), (max_, "max"), (sam, "sam"), (zoe, "zoe")):
        signin(c, p)
    assert make_pad(client, "Les Puces", "max, inconnu") is None      # unknown pseudo: nothing created
    assert "Pseudo inconnu : inconnu" in unescape(client.get("/bloc-notes").data.decode())
    pid = make_pad(client, "Les Puces", "max sam")
    assert pid
    # max sees it, marked new, with the one-time message
    assert pid in pad_ids(max_)
    assert 'class="np-dot"' in max_.get("/bloc-notes").data.decode()
    first = max_.get(f"/bloc-notes?n={pid}").data.decode()
    assert "vous a ajouté au bloc-notes" in first
    assert "vous a ajouté" not in max_.get(f"/bloc-notes?n={pid}").data.decode()   # once
    # zoe is not a member: 404 everywhere
    assert zoe.get(f"/bloc-notes?n={pid}").status_code == 404
    assert zoe.get(f"/bloc-notes/{pid}/etat").status_code == 404
    assert zoe.post(f"/bloc-notes/{pid}/texte", json={"text": "x", "base_rev": 0},
                    headers={"X-CSRF": csrf(zoe)}).status_code == 404
    # any member adds; only the creator removes or deletes; the creator cannot leave
    assert post(max_, f"/bloc-notes/{pid}/ajouter", pseudo="zoe").status_code == 302
    assert pid in pad_ids(zoe)
    assert post(max_, f"/bloc-notes/{pid}/retirer", pseudo="sam").status_code == 403
    assert post(max_, f"/bloc-notes/{pid}/supprimer").status_code == 403
    assert post(client, f"/bloc-notes/{pid}/quitter").status_code == 403
    assert post(client, f"/bloc-notes/{pid}/retirer", pseudo="sam").status_code == 302
    assert pid not in pad_ids(sam)
    assert post(zoe, f"/bloc-notes/{pid}/quitter").status_code == 302
    assert pid not in pad_ids(zoe)
    assert post(client, f"/bloc-notes/{pid}/supprimer").status_code == 302
    assert pid not in pad_ids(max_)


def test_private_pad_cannot_be_shared_or_deleted(client, hub_module):
    signin(client, "lea")
    signin(new_client(hub_module), "max")
    (pid,) = pad_ids(client)
    assert post(client, f"/bloc-notes/{pid}/ajouter", pseudo="max").status_code == 404
    assert post(client, f"/bloc-notes/{pid}/supprimer").status_code == 404


def test_shared_pads_can_be_turned_off(client, hub_module, monkeypatch):
    max_ = new_client(hub_module)
    signin(client, "lea")
    signin(max_, "max")
    pid = make_pad(client, "Les Puces", "max")
    monkeypatch.setenv("NOTES_SHARED", "0")
    page = max_.get("/bloc-notes").data.decode()
    assert "Les Puces" not in page and "Nouveau bloc-notes partagé" not in page
    assert max_.get(f"/bloc-notes?n={pid}").status_code == 404
    assert post(client, "/bloc-notes/nouveau", nom="X", membres="").status_code == 404


# ------------------------------------------------------------------ saving
def test_save_and_conflict(client, hub_module):
    max_ = new_client(hub_module)
    signin(client, "lea")
    signin(max_, "max")
    pid = make_pad(client, "Les Puces", "max")
    _, rev, tok = editor(client, pid)
    _, rev_m, tok_m = editor(max_, pid)
    assert rev == rev_m == 0
    r = client.post(f"/bloc-notes/{pid}/texte", json={"text": "piste robots", "base_rev": rev}, headers={"X-CSRF": tok})
    assert r.status_code == 200 and r.get_json()["rev"] == 1 and r.get_json()["by"] == "lea"
    # max saves on the old revision: refused with lea's version, nothing overwritten
    r = max_.post(f"/bloc-notes/{pid}/texte", json={"text": "autre", "base_rev": rev_m}, headers={"X-CSRF": tok_m})
    assert r.status_code == 409 and r.get_json()["text"] == "piste robots"
    assert max_.get(f"/bloc-notes/{pid}/etat").get_json()["text"] == "piste robots"
    # "Garder la mienne": resend on top of the new revision
    r = max_.post(f"/bloc-notes/{pid}/texte", json={"text": "autre", "base_rev": 1}, headers={"X-CSRF": tok_m})
    assert r.status_code == 200 and r.get_json()["rev"] == 2
    state = client.get(f"/bloc-notes/{pid}/etat")
    assert state.get_json() == {"rev": 2, "text": "autre", "by": "max", "at": state.get_json()["at"]}
    assert state.headers["Cache-Control"] == "no-store"


def test_form_save_without_js_and_stale_form(client):
    signin(client, "lea")
    (pid,) = pad_ids(client)
    r = post(client, f"/bloc-notes/{pid}/texte", texte="ligne 1\r\nligne 2", base_rev="0")
    assert r.status_code == 302
    assert client.get(f"/bloc-notes/{pid}/etat").get_json()["text"] == "ligne 1\nligne 2"
    page = post(client, f"/bloc-notes/{pid}/texte", texte="ma version", base_rev="0").data.decode()
    assert "a enregistré une autre version" in page and ">ma version</textarea>" in page   # text kept


def test_text_limit(client):
    signin(client, "lea")
    (pid,) = pad_ids(client)
    _, rev, tok = editor(client, pid)
    r = client.post(f"/bloc-notes/{pid}/texte", json={"text": "x" * 20_001, "base_rev": rev}, headers={"X-CSRF": tok})
    assert r.status_code == 413


def test_everything_is_escaped(client, hub_module):
    max_ = new_client(hub_module)
    signin(client, "lea")
    signin(max_, "max")
    evil = "<script>alert(1)</script>"
    pid = make_pad(client, evil, "max")
    _, rev, tok = editor(client, pid)
    client.post(f"/bloc-notes/{pid}/texte", json={"text": evil + "</textarea>", "base_rev": rev}, headers={"X-CSRF": tok})
    for c in (client, max_):
        page = c.get(f"/bloc-notes?n={pid}").data.decode()
        assert "<script>alert(1)" not in page and "</textarea></textarea>" not in page
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_bloc_notes_pages_use_plain_punctuation(client, hub_module):
    def text(page):
        return unescape(re.sub(r"<[^>]+>", " ", page))
    pages = [client.get("/bloc-notes").data.decode()]
    signin(client, "lea")
    pages.append(client.get("/bloc-notes").data.decode())
    for page in pages:
        for ch in ("—", "–", "…", "·", "↗", "→"):
            assert ch not in text(page), repr(ch)
    assert '<a href="/bloc-notes" aria-current="page">Bloc-notes</a>' in pages[1]


def test_static_script_stays_on_the_hub(hub_module):
    js = (hub_module.app.root_path + "/static/notes.js")
    src = open(js, encoding="utf-8").read()
    assert not re.search(r"https?://", src)
    assert "innerHTML" not in src                                    # text goes through textContent


# ------------------------------------------------------------------ organizer
def test_admin_reset_password_and_wipe(client, hub_module, notes, capsys):
    import notes_admin
    signin(client, "lea")
    assert notes_admin.main(["mdp", "lea"]) == 0
    other = new_client(hub_module)
    assert signin(other, "lea", "new-password").status_code == 302     # next sign-in sets a new one
    assert signin(new_client(hub_module), "lea", PW).status_code == 401
    assert notes_admin.main(["liste"]) == 0 and "lea" in capsys.readouterr().out
    assert notes_admin.main(["vider"]) == 2                            # needs --oui
    assert notes_admin.main(["vider", "--oui"]) == 0
    assert client.get("/bloc-notes").data.decode().count("Se connecter") >= 1   # account gone


def test_admin_delete_hands_shared_pad_over(client, hub_module, notes):
    import notes_admin
    max_ = new_client(hub_module)
    signin(client, "lea")
    signin(max_, "max")
    pid = make_pad(client, "Les Puces", "max")
    assert notes_admin.main(["supprimer", "lea"]) == 0
    page = max_.get(f"/bloc-notes?n={pid}").data.decode()
    assert "Partagé, créé par vous" in page                            # max owns it now
