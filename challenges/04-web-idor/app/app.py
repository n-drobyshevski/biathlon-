#!/usr/bin/env python3
"""
04 · Web · MEDIUM (IDOR)
DécaFlop Athlete Portal. You are logged in as bib #1042. The profile page is
/profile/<id> and does NOT check that the id belongs to you. Walk the ids
(crew/admin accounts have low numbers) to read someone else's profile.

Teaches: Insecure Direct Object Reference, horizontal privilege escalation.
"""
import os
from html import escape
from flask import Flask, Response, redirect, make_response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# id -> (name, role, note)
ATHLETES = {
    1000: ("Administration événement DécaFlop", "admin",
           "JOURNAL D'AUDIT — liste de départ officielle 'FINAL_RACE' :\n"
           "  last modified_by = compte staff 'v.lindqvist' "
           "(utilisateur SAP miroir : VLINDQVIST)\n"
           "  modification : puces de chronométrage échangées entre 3 athlètes.\n"
           "À remonter à l'équipe résultats SAP — voir le système DFlop ERP."),
    1001: ("Chef chronométreur", "crew",
           "La cabine de chronométrage est sur le Wi-Fi staff 'DECAFLOP-TIMING'. "
           "Arrêtez d'envoyer l'identifiant de la cabine en HTTP en clair !"),
    1042: ("Vous (dossard invité)", "athlete",
           "Bienvenue, concurrent·e. Vous ne pouvez voir que votre propre profil… n'est-ce pas ?"),
    1055: ("Astrid Bjornsen", "athlete", "Favorite pour le sprint."),
    1071: ("Mikkel Haugen", "athlete", "Excellent nageur, coureur moyen."),
}

ROLE_FR = {"admin": "admin", "crew": "staff", "athlete": "athlète"}

COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copié \u2713';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

def shell(title, body):
    signed_in = request.cookies.get("bib")
    me = (f'<a class="opt" href="/profile/{escape(signed_in)}">Mon profil</a>'
          f'<span><span class="mute">Connecté·e :</span> <b>dossard {escape(signed_in)}</b></span>'
          if signed_in else '<span class="mute">Non connecté·e</span>')
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<div class="strip"><div class="in"><span>Championnat régional de triathlon · Espace athlètes</span>
<span>Bureau de course ouvert dès 7 h 30</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Espace athlètes</small></a>
 <nav class="acct">{me}</nav>
</div></header>
<main class="page">{body}</main></body></html>"""

LOGIN = """<div class="panel">
 <h1 class="h">Bienvenue</h1>
 <p>Consultez votre vague de départ, votre place au parc à vélos et vos consignes avant la finale.</p>
 <p class="note db" style="margin:0 0 18px">Pour la démo, la connexion est désactivée.
  Continuez en tant que concurrent·e invité·e.</p>
 <a class="btn blue" href="/login">Continuer avec le dossard n° 1042</a>
</div>"""

def page(aid):
    if aid not in ATHLETES:
        return shell("Athlète introuvable", f"""<div class="crumb">profils / n° {aid}</div>
<div class="panel"><h1 class="h">Aucun athlète n° {aid}</h1>
 <p class="mute">Aucun profil ne correspond à ce numéro.</p>
 <a class="btn blue" href="/profile/1042">Retour à mon profil</a></div>"""), 404
    name, role, note = ATHLETES[aid]
    flag = (f"""<div class="flag"><span>Flag</span><code id="flag">{FLAG}</code>
 <button type="button" onclick="copyFlag(this)">Copier</button></div>{COPY_JS}"""
            if aid == 1000 else "")
    ink = " ink" if role != "athlete" else ""
    return shell(f"Profil n° {aid}", f"""<div class="crumb">profils / n° {aid}</div>
<div class="panel">
 <div class="who"><div class="bib{ink}">{aid}</div>
  <div><h1 class="h">{name}</h1><span class="tag {role}">{ROLE_FR[role]}</span></div></div>
 {flag}
 <div class="log"><pre>{note}</pre></div>
</div>
<p class="small mute">Vous consultez <code>/profile/{aid}</code>.
  Votre dossard est le <b>1042</b>. (Les comptes staff/admin ont des numéros plus bas.)</p>"""), 200

@app.get("/")
def home():
    return Response(shell("DécaFlop · Espace athlètes", LOGIN), mimetype="text/html")

@app.get("/login")
def login():
    r = make_response(redirect("/profile/1042"))
    r.set_cookie("bib", "1042")
    return r

@app.get("/profile/<int:aid>")
def profile(aid):
    # VULN: trusts the URL id, never compares to the signed-in bib cookie.
    body, status = page(aid)
    return Response(body, status=status, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
