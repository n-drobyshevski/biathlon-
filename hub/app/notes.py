"""
Bloc-notes: shared notepads on the hub (its own sheet tab).

The event runs offline, so players have no Google Docs. A player signs in on the
hub with a pseudo and a password (created the first time, same rules as the
team terminal), gets a private notepad ("Mes notes"), and can create shared
notepads with other players added by pseudo, whether the event is solo or team.
NOTES_SHARED=0 hides the shared ones and leaves only "Mes notes".

- Storage: SQLite at NOTES_DB (default /data/notes.db, the hub-data volume),
  one connection per request, WAL. The session secret lives in the same file,
  so sign-ins survive a restart.
- Session cookie "hub_session" (Flask's default name "session" would replace
  the intranet's login cookie: offline every service shares the same host).
- Every POST needs the session's CSRF token (form field "csrf" or header
  X-CSRF): lab subdomains are same-site online, so SameSite=Lax is not enough.
- Pages work without JavaScript; static/notes.js adds autosave, live updates
  and the conflict notice. Saving sends the revision the text was based on: a
  stale one gets 409 and the other version, nothing is overwritten silently.
- Organizer commands: notes_admin.py (list, reset a password, wipe).
"""
import hmac
import os
import re
import secrets
import sqlite3
import time
from html import escape

from flask import Blueprint, abort, g, jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("notes", __name__)

PSEUDO_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,23}$")
RESERVED = {"root", "admin", "administrateur", "nobody", "daemon", "bin", "sys", "www-data",
            "player", "ttyd", "organisation", "orga", "systeme"}
MIN_PASSWORD = 4
MAX_TEXT = 20_000
MAX_NAME = 60
MAX_MEMBERS = 24
PERSONAL = "Mes notes"
COLORS = ["#7b4fa8", "#1f7a5a", "#b4572d", "#2f62b8", "#8a6d1f", "#a03a6b", "#3f7f8c", "#5f6b2a"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS players (
  pseudo TEXT PRIMARY KEY, pw_hash TEXT, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pads (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, owner TEXT NOT NULL, shared INTEGER NOT NULL,
  created INTEGER NOT NULL, text TEXT NOT NULL DEFAULT '', rev INTEGER NOT NULL DEFAULT 0,
  by TEXT NOT NULL DEFAULT '', at INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS members (
  pad_id INTEGER NOT NULL REFERENCES pads(id) ON DELETE CASCADE, pseudo TEXT NOT NULL,
  added_by TEXT NOT NULL DEFAULT '', seen INTEGER NOT NULL DEFAULT 1, PRIMARY KEY (pad_id, pseudo));
CREATE INDEX IF NOT EXISTS members_pseudo ON members (pseudo);
"""

_render = {}        # layout() and html() from app.py, set by bind()
AVAILABLE = True    # False when the database cannot be opened (no volume): the tab says so


# ------------------------------------------------------------------ database
def db_path():
    return os.environ.get("NOTES_DB", "/data/notes.db")


def connect(path=None):
    con = sqlite3.connect(path or db_path(), timeout=5, isolation_level=None)   # autocommit
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init(path=None):
    con = connect(path)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
    finally:
        con.close()


def secret(path=None):
    """The session signing key, created once and kept in the database."""
    init(path)
    con = connect(path)
    try:
        con.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('secret', ?)", (secrets.token_hex(32),))
        return con.execute("SELECT value FROM meta WHERE key = 'secret'").fetchone()["value"]
    finally:
        con.close()


def db():
    if "notes_db" not in g:
        g.notes_db = connect()
    return g.notes_db


@bp.teardown_app_request
def _close(_exc):
    con = g.pop("notes_db", None)
    if con is not None:
        con.close()


def shared_on():
    return os.environ.get("NOTES_SHARED", "1").strip() != "0"


def now():
    return int(time.time())


# ------------------------------------------------------------------ accounts
def norm(pseudo):
    return (pseudo or "").strip().lower()


def pseudo_error(pseudo):
    if not PSEUDO_RE.match(pseudo):
        return "Pseudo : 2 à 24 caractères, lettres minuscules, chiffres, point, tiret ou soulignement."
    if pseudo in RESERVED:
        return "Ce pseudo est réservé. Choisissez-en un autre."
    return ""


def exists(pseudo):
    return db().execute("SELECT 1 FROM players WHERE pseudo = ?", (pseudo,)).fetchone() is not None


def ensure_personal(con, pseudo):
    row = con.execute("SELECT p.id FROM pads p JOIN members m ON m.pad_id = p.id "
                      "WHERE p.shared = 0 AND p.owner = ? AND m.pseudo = ?", (pseudo, pseudo)).fetchone()
    if row:
        return row["id"]
    cur = con.execute("INSERT INTO pads (name, owner, shared, created) VALUES (?, ?, 0, ?)",
                      (PERSONAL, pseudo, now()))
    con.execute("INSERT INTO members (pad_id, pseudo, added_by, seen) VALUES (?, ?, ?, 1)",
                (cur.lastrowid, pseudo, pseudo))
    return cur.lastrowid


def current():
    """The signed-in pseudo, or None (also when the account was deleted)."""
    if not AVAILABLE:
        return None
    p = session.get("p")
    if not p:
        return None
    try:
        return p if exists(p) else None
    except sqlite3.Error:
        return None


def csrf_token():
    tok = session.get("csrf")
    if not tok:
        tok = session["csrf"] = secrets.token_urlsafe(24)
    return tok


def csrf_field():
    return f'<input type="hidden" name="csrf" value="{escape(csrf_token())}">'


@bp.before_request
def _guard():
    if request.method == "POST":
        sent = request.form.get("csrf", "") or request.headers.get("X-CSRF", "")
        if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
            abort(400)


def avatar(pseudo):
    return COLORS[sum(pseudo.encode()) % len(COLORS)]


def unseen(pseudo):
    """How many shared notepads `pseudo` was added to and has not opened yet."""
    if not pseudo or not shared_on():
        return 0
    return db().execute("SELECT COUNT(*) FROM members m JOIN pads p ON p.id = m.pad_id "
                        "WHERE m.pseudo = ? AND m.seen = 0 AND p.shared = 1", (pseudo,)).fetchone()[0]


def new_label(n):
    return f"{n} nouveau{'x' if n > 1 else ''} bloc-notes partagé{'s' if n > 1 else ''}"


def header_chip():
    """The sign-in chip in the hub's title bar, with the count of new shares."""
    if not AVAILABLE:
        return ""
    p = current()
    if not p:
        return '<a class="who out" href="/bloc-notes">Se connecter</a>'
    n = unseen(p)
    badge = f'<span class="who-new">{n}</span>' if n else ""
    label = f"Bloc-notes de {p}" + (f", {new_label(n)}" if n else "")
    return (f'<a class="who" href="/bloc-notes" aria-label="{escape(label)}">'
            f'<span class="av" style="background:{avatar(p)}" aria-hidden="true">{escape(p[0].upper())}</span>'
            f'{escape(p)}{badge}</a>')


def tab_badge():
    """A dot on the Bloc-notes sheet tab while a share is waiting."""
    n = unseen(current()) if AVAILABLE else 0
    return f'<span class="tab-new" aria-label="{escape(new_label(n))}"></span>' if n else ""


# ------------------------------------------------------------------ pads
def pads_of(pseudo):
    sql = ("SELECT p.*, m.seen, m.added_by, (SELECT COUNT(*) FROM members x WHERE x.pad_id = p.id) AS n "
           "FROM pads p JOIN members m ON m.pad_id = p.id WHERE m.pseudo = ?")
    if not shared_on():
        sql += " AND p.shared = 0"
    return db().execute(sql + " ORDER BY p.shared, p.created, p.id", (pseudo,)).fetchall()


def pad_for(pad_id, pseudo):
    """The pad if `pseudo` is a member (and shared pads are on), else 404."""
    row = db().execute("SELECT p.*, m.seen, m.added_by FROM pads p JOIN members m ON m.pad_id = p.id "
                       "WHERE p.id = ? AND m.pseudo = ?", (pad_id, pseudo)).fetchone()
    if row is None or (row["shared"] and not shared_on()):
        abort(404)
    return row


def members_of(pad_id):
    return [r["pseudo"] for r in db().execute(
        "SELECT pseudo FROM members WHERE pad_id = ? ORDER BY rowid", (pad_id,))]


def need_player():
    p = current()
    if not p:
        abort(403)
    return p


def flash(kind, text):
    session["np_msg"] = [kind, text]


def back(pad_id=None):
    return redirect(f"/bloc-notes?n={pad_id}" if pad_id else "/bloc-notes")


# ------------------------------------------------------------------ rendering
def stamp(ts):
    """A time the browser rewrites in local time (static/notes.js); server time otherwise."""
    return (f'<time data-t="{int(ts)}" datetime="{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))}">'
            f'{time.strftime("%H:%M", time.localtime(ts))}</time>')


def who_text(by, me):
    return "vous" if by == me else escape(by)


def chip(pseudo, me, remove_form=""):
    you = " (vous)" if pseudo == me else ""
    return (f'<span class="pz{" me" if pseudo == me else ""}"><i style="background:{avatar(pseudo)}" '
            f'aria-hidden="true">{escape(pseudo[0].upper())}</i>{escape(pseudo)}{you}{remove_form}</span>')


def page(body, me=None, status=200):
    layout, html = _render["layout"], _render["html"]
    formula = f"Bloc-notes de {me}" if me else "Bloc-notes"
    return html(layout("Bloc-notes", body, "/bloc-notes", "A1", escape(formula),
                       scripts='<script src="/static/notes.js" defer></script>'), status)


def signin_page(error="", pseudo="", status=200):
    err = f'<p class="np-err" role="alert">{escape(error)}</p>' if error else ""
    body = (
        '<div class="lock"><h1>Bloc-notes</h1>'
        '<p>Gardez vos notes de l\'enquête sur tous vos appareils et partagez un bloc-notes avec '
        'd\'autres joueurs.</p>'
        '<p>La première fois, votre pseudo est créé avec ce mot de passe. Prenez le même pseudo que sur '
        'le tableau des scores et le terminal.</p>'
        f'<form method="post" action="/bloc-notes/connexion">{csrf_field()}{err}'
        '<label for="np-pseudo">Pseudo</label>'
        f'<input class="in" id="np-pseudo" name="pseudo" value="{escape(pseudo)}" maxlength="24" '
        'autocomplete="username" autocapitalize="none" spellcheck="false" required>'
        '<label for="np-mdp">Mot de passe</label>'
        f'<input class="in" id="np-mdp" name="motdepasse" type="password" minlength="{MIN_PASSWORD}" '
        'autocomplete="current-password" required>'
        '<button class="go" type="submit">Se connecter</button></form></div>')
    return page(body, status=status)


def unavailable_page():
    body = ('<div class="lock"><h1>Bloc-notes</h1><p>Le bloc-notes est indisponible pour le moment : '
            'prévenez l\'organisation.</p></div>')
    return page(body, status=503)


def form(action, label, cls="np-btn", confirm="", fields=""):
    conf = f' data-confirm="{escape(confirm)}"' if confirm else ""
    return (f'<form method="post" action="{escape(action)}" class="np-inline"{conf}>{csrf_field()}{fields}'
            f'<button class="{cls}" type="submit">{label}</button></form>')


def board_page(me, pad_id=None, conflict=None):
    pads = pads_of(me)
    by_id = {r["id"]: r for r in pads}
    if pad_id is None:
        last = session.get("np_last")
        pad_id = last if last in by_id else next((r["id"] for r in pads if not r["shared"]), None)
        if pad_id is None:                       # account without its private pad (old data)
            pad_id = ensure_personal(db(), me)
            pads = pads_of(me)
            by_id = {r["id"]: r for r in pads}
    pad = pad_for(pad_id, me)
    session["np_last"] = pad["id"]
    new = pad["shared"] and not pad["seen"]
    if new:
        db().execute("UPDATE members SET seen = 1 WHERE pad_id = ? AND pseudo = ?", (pad["id"], me))
    msg = session.pop("np_msg", None)

    items = []
    for r in pads:
        unseen = r["shared"] and not r["seen"] and r["id"] != pad["id"]
        meta = f'{r["n"]} membres' if r["shared"] else "Privé"
        if r["by"]:
            meta += f', modifié par {who_text(r["by"], me)} à {stamp(r["at"])}'
        dot = '<span class="np-dot" aria-label="Nouveau"></span>' if unseen else ""
        cur = ' aria-current="true"' if r["id"] == pad["id"] else ""
        items.append(f'<a href="/bloc-notes?n={r["id"]}"{cur}><b>{dot}{escape(r["name"])}</b><small>{meta}</small></a>')
    create = ""
    if shared_on():
        create = (
            '<details class="np-new"><summary class="np-btn pri">Nouveau bloc-notes partagé</summary>'
            f'<form method="post" action="/bloc-notes/nouveau" class="np-form">{csrf_field()}'
            '<label for="np-nom">Nom du bloc-notes</label>'
            f'<input class="np-in" id="np-nom" name="nom" maxlength="{MAX_NAME}" required>'
            '<label for="np-membres">Joueurs à ajouter</label>'
            '<input class="np-in" id="np-membres" name="membres" autocapitalize="none" spellcheck="false" '
            'placeholder="pseudos, séparés par des espaces">'
            '<p class="np-hint">Ils doivent s\'être connectés au hub au moins une fois. Vous pourrez en ajouter '
            'plus tard.</p>'
            '<button class="np-btn pri" type="submit">Créer</button></form></details>')
    # #np-incoming: notes.js announces shares that arrive while the page is open
    side = (f'<section class="np-card"><h2>Vos bloc-notes</h2>'
            '<div class="np-incoming" id="np-incoming" role="status" aria-live="polite"></div>'
            f'<nav class="np-list" id="np-list" aria-label="Vos bloc-notes" data-open="{pad["id"]}">'
            f'{"".join(items)}</nav>{create}'
            f'<div class="np-me"><span>Connecté : <b>{escape(me)}</b></span>'
            f'{form("/bloc-notes/deconnexion", "Se déconnecter", "np-link")}</div></section>')

    owner = pad["owner"] == me
    notice = ""
    if msg:
        notice = f'<p class="np-{"err" if msg[0] == "err" else "ok-msg"}" role="alert">{escape(msg[1])}</p>'
    banner = ""
    if new:
        banner = (f'<p class="np-banner"><b>{escape(pad["added_by"])}</b> vous a ajouté au bloc-notes '
                  f'<b>{escape(pad["name"])}</b>.</p>')
    if pad["shared"]:
        sh = f'Partagé, créé par {who_text(pad["owner"], me)}'
        act = (form(f'/bloc-notes/{pad["id"]}/supprimer', "Supprimer", "np-btn warn",
                    "Supprimer ce bloc-notes pour tous ses membres ?") if owner
               else form(f'/bloc-notes/{pad["id"]}/quitter', "Quitter", "np-btn warn",
                         "Quitter ce bloc-notes ?"))
    else:
        sh, act = "Privé, visible par vous seul", ""
    text, rev, conf = pad["text"], pad["rev"], ""
    if conflict is not None:                     # no-JS save on a stale revision: keep the player's text
        text = conflict
        conf = (f'<p class="np-conf" role="alert"><b>{escape(pad["by"])}</b> a enregistré une autre version à '
                f'{stamp(pad["at"])}. Votre texte est ci-dessous, pas encore enregistré : enregistrez-le pour '
                f'remplacer sa version, ou <a href="/bloc-notes?n={pad["id"]}">rechargez</a> pour voir la sienne.</p>')
    saved = (f'<span class="ok">Enregistré. Modifié par {who_text(pad["by"], me)} à {stamp(pad["at"])}.</span>'
             if pad["by"] else '<span>Rien d\'écrit pour l\'instant.</span>')
    editor = (
        f'<form method="post" action="/bloc-notes/{pad["id"]}/texte" class="np-edit" id="np-edit" '
        f'data-pad="{pad["id"]}" data-rev="{rev}" data-me="{escape(me)}" data-csrf="{escape(csrf_token())}">'
        f'{csrf_field()}<input type="hidden" name="base_rev" value="{rev}">'
        '<div class="np-conf" id="np-conf" role="alert" hidden></div>'
        f'<textarea class="paper" id="np-text" name="texte" maxlength="{MAX_TEXT}" aria-label="{escape(pad["name"])}" '
        f'placeholder="Écrivez ici : pistes, identifiants trouvés, qui fait quoi.">{escape(text)}</textarea>'
        f'<div class="np-saved"><span id="np-status">{saved}</span>'
        f'<span id="np-count">{len(text)} caractères</span></div>'
        '<button class="np-btn pri np-save" type="submit">Enregistrer</button></form>')
    members = ""
    if pad["shared"]:
        chips = []
        for p in members_of(pad["id"]):
            rm = ""
            if owner and p != me:
                rm = (f'<form method="post" action="/bloc-notes/{pad["id"]}/retirer" class="np-inline">{csrf_field()}'
                      f'<input type="hidden" name="pseudo" value="{escape(p)}">'
                      f'<button type="submit" aria-label="Retirer {escape(p)}" title="Retirer du bloc-notes">&times;</button>'
                      '</form>')
            chips.append(chip(p, me, rm))
        members = (
            f'<div class="np-members"><div class="np-chips">{"".join(chips)}</div>'
            f'<form method="post" action="/bloc-notes/{pad["id"]}/ajouter" class="np-add">{csrf_field()}'
            '<label class="sr" for="np-ajout">Ajouter un joueur par son pseudo</label>'
            '<input class="np-in" id="np-ajout" name="pseudo" maxlength="24" placeholder="Ajouter un joueur par son pseudo" '
            'autocapitalize="none" spellcheck="false" required>'
            '<button class="np-btn" type="submit">Ajouter</button></form></div>')
    main = (f'<section class="np-card np-ed">{banner}{notice}'
            f'<div class="np-top"><h2>{escape(pad["name"])}</h2><span class="np-sh">{sh}</span>'
            f'<span class="np-act">{act}</span></div>{conf}{editor}{members}</section>')
    return page(f'<div class="np">{side}{main}</div>', me)


# ------------------------------------------------------------------ routes
@bp.get("/bloc-notes")
def index():
    if not AVAILABLE:
        return unavailable_page()
    me = current()
    if not me:
        return signin_page()
    n = request.args.get("n", "")
    return board_page(me, int(n) if n.isdigit() else None)


@bp.post("/bloc-notes/connexion")
def signin():
    if not AVAILABLE:
        return unavailable_page()
    pseudo = norm(request.form.get("pseudo"))
    pw = request.form.get("motdepasse", "")
    err = pseudo_error(pseudo)
    if err:
        return signin_page(err, request.form.get("pseudo", "")[:24], 400)
    if len(pw) < MIN_PASSWORD:
        return signin_page(f"Mot de passe : au moins {MIN_PASSWORD} caractères.", pseudo, 400)
    con = db()
    row = con.execute("SELECT pw_hash FROM players WHERE pseudo = ?", (pseudo,)).fetchone()
    con.execute("BEGIN IMMEDIATE")
    try:
        if row is None:                                  # first time: create the account
            con.execute("INSERT INTO players (pseudo, pw_hash, created) VALUES (?, ?, ?)",
                        (pseudo, generate_password_hash(pw), now()))
        elif not row["pw_hash"]:                         # reset by the organizer: set a new one
            con.execute("UPDATE players SET pw_hash = ? WHERE pseudo = ?", (generate_password_hash(pw), pseudo))
        elif not check_password_hash(row["pw_hash"], pw):
            con.execute("ROLLBACK")
            return signin_page("Mot de passe incorrect pour ce pseudo. Oublié ? Demandez à l'organisation.",
                               pseudo, 401)
        ensure_personal(con, pseudo)
        con.execute("COMMIT")
    except sqlite3.IntegrityError:                       # created by a parallel request
        con.execute("ROLLBACK")
        return signin_page("Réessayez.", pseudo, 409)
    session.clear()
    session.permanent = True
    session["p"] = pseudo
    csrf_token()
    return back()


@bp.post("/bloc-notes/deconnexion")
def signout():
    session.clear()
    return back()


def _parse_pseudos(raw):
    out = []
    for p in re.split(r"[\s,;]+", (raw or "").lower()):
        if p and p not in out:
            out.append(p)
    return out


@bp.post("/bloc-notes/nouveau")
def create():
    me = need_player()
    if not shared_on():
        abort(404)
    name = " ".join(request.form.get("nom", "").split())[:MAX_NAME]
    if not name:
        flash("err", "Donnez un nom au bloc-notes.")
        return back()
    wanted = [p for p in _parse_pseudos(request.form.get("membres")) if p != me]
    unknown = [p for p in wanted if not exists(p)]
    if unknown:
        flash("err", "Pseudo inconnu : " + ", ".join(unknown) +
              ". Chaque joueur doit d'abord se connecter une fois au hub. Rien n'a été créé.")
        return back()
    if len(wanted) + 1 > MAX_MEMBERS:
        flash("err", f"{MAX_MEMBERS} membres au plus.")
        return back()
    con = db()
    con.execute("BEGIN IMMEDIATE")
    cur = con.execute("INSERT INTO pads (name, owner, shared, created) VALUES (?, ?, 1, ?)", (name, me, now()))
    pid = cur.lastrowid
    con.execute("INSERT INTO members (pad_id, pseudo, added_by, seen) VALUES (?, ?, ?, 1)", (pid, me, me))
    for p in wanted:
        con.execute("INSERT INTO members (pad_id, pseudo, added_by, seen) VALUES (?, ?, ?, 0)", (pid, p, me))
    con.execute("COMMIT")
    return back(pid)


def _shared_pad(pad_id, me):
    pad = pad_for(pad_id, me)
    if not pad["shared"]:
        abort(404)
    return pad


@bp.post("/bloc-notes/<int:pad_id>/ajouter")
def add_member(pad_id):
    me = need_player()
    pad = _shared_pad(pad_id, me)
    p = norm(request.form.get("pseudo"))
    members = members_of(pad_id)
    if not p:
        return back(pad_id)
    if p in members:
        flash("err", f"« {p} » est déjà dans ce bloc-notes.")
    elif pseudo_error(p) or not exists(p):
        flash("err", f"Pseudo inconnu : « {p[:24]} » doit d'abord se connecter une fois au hub.")
    elif len(members) >= MAX_MEMBERS:
        flash("err", f"{MAX_MEMBERS} membres au plus.")
    else:
        db().execute("INSERT OR IGNORE INTO members (pad_id, pseudo, added_by, seen) VALUES (?, ?, ?, 0)",
                     (pad["id"], p, me))
        flash("ok", f"{p} a été ajouté.")
    return back(pad_id)


@bp.post("/bloc-notes/<int:pad_id>/retirer")
def remove_member(pad_id):
    me = need_player()
    pad = _shared_pad(pad_id, me)
    p = norm(request.form.get("pseudo"))
    if pad["owner"] != me:
        abort(403)
    if p and p != me:
        db().execute("DELETE FROM members WHERE pad_id = ? AND pseudo = ?", (pad_id, p))
    return back(pad_id)


@bp.post("/bloc-notes/<int:pad_id>/quitter")
def leave(pad_id):
    me = need_player()
    pad = _shared_pad(pad_id, me)
    if pad["owner"] == me:
        abort(403)                               # the creator deletes instead
    db().execute("DELETE FROM members WHERE pad_id = ? AND pseudo = ?", (pad_id, me))
    flash("ok", f"Vous avez quitté « {pad['name']} ».")
    session.pop("np_last", None)
    return back()


@bp.post("/bloc-notes/<int:pad_id>/supprimer")
def delete(pad_id):
    me = need_player()
    pad = _shared_pad(pad_id, me)
    if pad["owner"] != me:
        abort(403)
    db().execute("DELETE FROM pads WHERE id = ?", (pad_id,))
    flash("ok", f"« {pad['name']} » a été supprimé.")
    session.pop("np_last", None)
    return back()


def list_item(r, me):
    return {"id": r["id"], "name": r["name"], "shared": bool(r["shared"]), "n": r["n"],
            "by": "vous" if r["by"] == me else r["by"], "at": r["at"],
            "new": bool(r["shared"] and not r["seen"]), "added_by": r["added_by"]}


@bp.get("/bloc-notes/liste")
def listing():
    """The player's notepads, for notes.js: new shares appear without a reload."""
    me = need_player()
    resp = jsonify({"pads": [list_item(r, me) for r in pads_of(me)]})
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _state(pad):
    return {"rev": pad["rev"], "text": pad["text"], "by": pad["by"], "at": pad["at"]}


@bp.get("/bloc-notes/<int:pad_id>/etat")
def state(pad_id):
    me = need_player()
    resp = jsonify(_state(pad_for(pad_id, me)))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.post("/bloc-notes/<int:pad_id>/texte")
def save(pad_id):
    me = need_player()
    as_json = request.is_json
    if as_json:
        data = request.get_json(silent=True) or {}
        text, base = data.get("text"), data.get("base_rev")
    else:
        text, base = request.form.get("texte"), request.form.get("base_rev", "")
        base = int(base) if str(base).isdigit() else None
    if not isinstance(text, str) or not isinstance(base, int):
        abort(400)
    text = text.replace("\r\n", "\n")
    if len(text) > MAX_TEXT:
        if as_json:
            return jsonify({"error": "trop long", "max": MAX_TEXT}), 413
        flash("err", f"Le bloc-notes est limité à {MAX_TEXT} caractères.")
        return back(pad_id)
    con = db()
    con.execute("BEGIN IMMEDIATE")
    pad = pad_for(pad_id, me)
    if pad["rev"] != base:                       # someone saved since this text was loaded
        con.execute("ROLLBACK")
        if as_json:
            return jsonify(_state(pad)), 409
        return board_page(me, pad_id, conflict=text)
    con.execute("UPDATE pads SET text = ?, rev = rev + 1, by = ?, at = ? WHERE id = ?", (text, me, now(), pad_id))
    con.execute("COMMIT")
    pad = pad_for(pad_id, me)
    return jsonify(_state(pad)) if as_json else back(pad_id)


def bind(app, layout, html):
    """Plug the notepads into the hub: signing key, cookie, page chrome."""
    global AVAILABLE
    _render.update(layout=layout, html=html)
    try:
        app.secret_key = secret()
    except (sqlite3.Error, OSError) as exc:      # no writable volume: the rest of the hub still works
        AVAILABLE = False
        app.secret_key = secrets.token_hex(32)
        app.logger.warning("Bloc-notes indisponible (%s): %s", db_path(), exc)
    app.config.update(SESSION_COOKIE_NAME="hub_session", SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_HTTPONLY=True, PERMANENT_SESSION_LIFETIME=7 * 24 * 3600)
    app.register_blueprint(bp)
