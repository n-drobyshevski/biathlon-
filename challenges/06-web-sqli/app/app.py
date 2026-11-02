#!/usr/bin/env python3
"""
06 · Web · MEDIUM (SQL injection — auth bypass)
DécaFlop Results Admin. The login builds its SQL by string concatenation, so a
classic injection logs you in without a password.

Example:  username =  ' OR '1'='1' --        password = anything
Teaches: SQL injection, auth bypass, why you parameterize queries.
"""
import os
import sqlite3
import sys
from html import escape

from flask import Flask, Response, request, redirect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

def db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users(username TEXT, password TEXT, role TEXT)")
    con.executemany(
        "INSERT INTO users VALUES(?,?,?)",
        [("results_admin", "s3cr3t-do-not-share-9912", "admin"),
         ("v.lindqvist",   "Chip7Chip7!",             "results_operator")],
    )
    con.commit()
    return con

PRODUCT = "ChronoRésultats 2.8.1, module admin"


def shell(title, body, user=None):
    return intranet.page(f"{title} - Admin résultats", body, app="resultats",
                         site_title="Admin résultats", site_href="/", logo="AR",
                         topnav=[("/", "Tableau de bord", True)], user=user,
                         logout="/" if user else None, product=PRODUCT,
                         foot_extra="Résultats de la finale figés à 16 h 00",
                         scripts=intranet.COPY_JS)


def FORM(msg="", username=""):
    # The typed username is kept (HTML-escaped) so players can tweak a payload
    # instead of retyping it. The SQL itself is still built from raw input.
    return shell("Connexion", f"""<h1 class="h1">Connexion</h1>
<p class="lead">Gestion officielle des résultats. Réservé au staff autorisé.</p>
{msg}
<form class="form" method="post" action="/login">
 <div class="field"><label for="u">Nom d'utilisateur</label>
  <input class="in" id="u" name="username" value="{escape(username)}" autofocus
   autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"></div>
 <div class="field"><label for="p">Mot de passe</label>
  <input class="in" id="p" name="password" type="password" autocomplete="off"></div>
 <div class="btns"><button class="btn" type="submit">Se connecter</button></div>
</form>
<p class="mute" style="margin-top:18px;font-size:12px">Mot de passe oublié&#160;? Contactez le bureau de course
 (poste 214). Les mots de passe ne sont jamais envoyés par e-mail.<br>Ne partagez jamais un compte staff.</p>""")

STANDINGS = [("1", "Astrid Bjornsen", "0", "1:02:14"),
             ("2", "Mikkel Haugen", "1", "1:02:51"),
             ("3", "En attente de validation", "", "")]

def ok_page():
    rows = "".join(f'<tr><td class="num">{r}</td><td>{n}</td><td class="num">{m}</td><td class="num">{t}</td></tr>'
                   for r, n, m, t in STANDINGS)
    return shell("Tableau de bord", f"""<h1 class="h1">Tableau de bord</h1>
<p class="status">Session administrateur ouverte. Toute modification du classement est journalisée.</p>
<div class="cols"><div>
 <section class="wp"><h2>Classement provisoire de la finale</h2>
  <p class="mute" style="font-size:12px">Copie en lecture seule de la table SAP ZRACE_RESULT.</p>
  <table class="list data"><thead><tr><th style="width:60px">Rang</th><th>Athlète</th>
   <th style="width:90px">Pénalités</th><th style="width:100px">Temps</th></tr></thead>
  <tbody>{rows}</tbody></table>
 </section>
 <section class="wp"><h2>Avis</h2><div class="log"><pre>AVIS SYSTÈME DE RÉSULTATS
-------------------------
Les résultats officiels sont stockés dans le SAP DFlop ERP (table ZRACE_RESULT).
Cette admin web n'est qu'une interface. Pour savoir QUI a modifié le classement
final, récupérez la table des utilisateurs SAP (USR02) sur le serveur ERP.

Migration en cours. Cette admin web est remplacée par une nouvelle API de
résultats en JSON (jetons JWT). Merci de basculer vos intégrations.</pre></div></section>
</div><div>
 <section class="wp"><h2>Code de validation du classement</h2>
  <p class="mute" style="font-size:12px">À saisir dans SAP lors de la publication des résultats officiels.</p>
  {intranet.codebox(FLAG)}
 </section>
 <section class="wp"><h2>Système</h2><dl class="kv">
  <dt>Base</dt><dd>resultats_finale (lecture seule)</dd><dt>Source</dt><dd>SAP DFL, mandant 001</dd>
  <dt>Gel</dt><dd>16 h 00</dd></dl></section>
</div></div>""", user="Administrateur")


@app.get("/")
def home():
    return Response(FORM(msg=""), mimetype="text/html")

@app.get("/login")
def login_get():
    return redirect("/")

@app.errorhandler(404)
def not_found(_e):
    return Response(shell("Page introuvable", """<h1 class="h1">Page introuvable</h1>
<p class="lead">Cette page n'existe pas.</p><p><a href="/">Retour à la connexion</a></p>"""),
        status=404, mimetype="text/html")

@app.post("/login")
def login():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    # VULN: raw string interpolation -> SQL injection
    q = f"SELECT role FROM users WHERE username = '{u}' AND password = '{p}'"
    try:
        row = db().execute(q).fetchone()
    except sqlite3.Error as e:
        return Response(FORM(msg=f'<div class="status err" role="alert"><b>Erreur de base de données</b>'
                             f'<pre>Erreur SQL : {escape(str(e))}</pre></div>',
                             username=u),
                        mimetype="text/html")
    if row:
        return Response(ok_page(), mimetype="text/html")
    return Response(FORM(msg='<div class="status err" role="alert">Identifiants incorrects.</div>',
                         username=u),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
