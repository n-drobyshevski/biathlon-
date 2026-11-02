#!/usr/bin/env python3
"""
06 · Web · MEDIUM (SQL injection — auth bypass)
DécaFlop Results Admin. The login builds its SQL by string concatenation, so a
classic injection logs you in without a password.

Example:  username =  ' OR '1'='1' --        password = anything
Teaches: SQL injection, auth bypass, why you parameterize queries.
"""
import os, sqlite3
from html import escape
from flask import Flask, Response, request, redirect

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

def db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users(username TEXT, password TEXT, role TEXT)")
    con.executemany(
        "INSERT INTO users VALUES(?,?,?)",
        [("results_admin", "s3cr3t-do-not-share-9912", "admin"),
         ("v.lindqvist",   "Lane7Lane7!",             "results_operator")],
    )
    con.commit()
    return con

COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copié \u2713';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

def shell(title, body, right=""):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<div class="strip"><div class="in"><span>Admin résultats · réservé au staff autorisé</span>
<span>Finale — résultats figés à 16 h 00</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Admin résultats</small></a>
 <nav class="acct">{right}</nav>
</div></header>
{body}</body></html>"""

def FORM(msg="", username=""):
    # The typed username is kept (HTML-escaped) so players can tweak a payload
    # instead of retyping it. The SQL itself is still built from raw input.
    return shell("DécaFlop · Admin résultats", f"""<main class="page" style="max-width:460px">
<div class="panel">
 <h1 class="h">Connexion</h1>
 <p class="mute small" style="margin:0 0 18px">Gestion officielle des résultats. Réservé au staff autorisé.</p>
 {msg}
 <form method="post" action="/login">
  <div class="field"><label for="u">Nom d'utilisateur</label>
   <input id="u" name="username" value="{escape(username)}" autofocus
    autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"></div>
  <div class="field"><label for="p">Mot de passe</label>
   <input id="p" name="password" type="password" autocomplete="off"></div>
  <button class="btn blue wide">Se connecter</button>
 </form>
 <details class="forgot"><summary>Mot de passe oublié ?</summary>
  <p>Contactez le bureau de course (poste 214). Les mots de passe ne sont
   jamais envoyés par e-mail.</p></details>
</div>
<p class="small mute">Ne partagez jamais un compte staff.</p>
</main>""")

STANDINGS = [("1", "Astrid Bjornsen", "0", "38:12,4"),
             ("2", "Mikkel Haugen", "2", "38:40,9"),
             ("3", "—", "—", "en attente")]

def ok_page():
    rows = "".join(f"<tr><td>{r}</td><td>{n}</td><td>{m}</td><td>{t}</td></tr>"
                   for r, n, m, t in STANDINGS)
    return shell("Admin résultats", f"""<main class="page">
<div class="crumb">résultats / tableau de bord</div>
<div class="panel">
 <h1 class="h">Connecté·e</h1>
 <p class="mute" style="margin:0">Tableau de bord de l'admin résultats.</p>
 <div class="flag"><span>Flag</span><code id="flag">{FLAG}</code>
  <button type="button" onclick="copyFlag(this)">Copier</button></div>
 <div class="log"><pre>AVIS — SYSTÈME DE RÉSULTATS
---------------------------
Les résultats officiels sont stockés dans le SAP DFlop ERP (table ZRACE_RESULT).
Cette admin web n'est qu'une interface. Pour savoir QUI a modifié le classement
final, récupérez la table des utilisateurs SAP (USR02) sur le serveur ERP.</pre></div>
</div>
<div class="panel">
 <h2 class="h">Finale · classement provisoire</h2>
 <p class="small mute" style="margin:0 0 10px">Copie en lecture seule de la table SAP ZRACE_RESULT.</p>
 <table class="std"><thead><tr><th>Rang</th><th>Athlète</th><th>Fautes</th><th>Temps</th></tr></thead>
 <tbody>{rows}</tbody></table>
</div>
</main>{COPY_JS}""", right='<a href="/">Se déconnecter</a>')

@app.get("/")
def home():
    return Response(FORM(msg=""), mimetype="text/html")

@app.get("/login")
def login_get():
    return redirect("/")

@app.errorhandler(404)
def not_found(_e):
    return Response(shell("Page introuvable", """<main class="page" style="max-width:460px">
<div class="panel"><h1 class="h">Page introuvable</h1>
 <p class="mute">Cette page n'existe pas.</p>
 <a class="btn blue" href="/">Retour à la connexion</a></div></main>"""),
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
        return Response(FORM(msg=f'<div class="note db" role="alert"><b>Erreur de base de données</b>'
                             f'<pre>Erreur SQL : {escape(str(e))}</pre></div>',
                             username=u),
                        mimetype="text/html")
    if row:
        return Response(ok_page(), mimetype="text/html")
    return Response(FORM(msg='<div class="note err" role="alert">Identifiants incorrects.</div>',
                         username=u),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
