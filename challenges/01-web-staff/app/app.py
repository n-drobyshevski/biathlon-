#!/usr/bin/env python3
"""
01 · Web · EASY
DécaFlop sponsor microsite. There is a 'hidden' staff portal — but it is
listed in robots.txt, which anyone can read.

Teaches: robots.txt recon, that "hidden" != "secret".
"""
import os
from html import escape

from flask import Flask, Response, request

from shop import shop, layout, html

app = Flask(__name__)
app.register_blueprint(shop)   # public storefront pages (decor)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# Crew login for the internal file share "Partage DFlop" (:8020). The staff
# portal hands it out, so solving 01 is how players learn how to log in. Read
# from the SAME env the share reads, with the share's defaults, so the two stay
# in sync (docker-compose feeds both services from one value).
SHARE_PORT = 8020
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

HEAD = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>"""

STAFF = HEAD.replace("{title}", "DécaFlop — Portail staff") + """
<div class="strip"><div class="in"><span>INTERNE · Réseau staff DécaFlop</span>
<span>Ne partagez pas les liens de cet espace</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Portail staff</small></a>
 <nav class="acct"><span class="mute">Équipe événement</span></nav>
</div></header>
<main class="page">
 <div class="crumb"><a href="/">decaflop</a> / staff-portal (interne)</div>
 <div class="panel">
  <h1 class="h">Portail staff</h1>
  <p>Vous avez trouvé l'espace « caché ». Il était dans <code>/robots.txt</code> depuis le début.</p>
  <div class="flag"><span>Flag</span><code id="flag">{flag}</code>
   <button type="button" onclick="copyFlag(this)">Copier</button></div>
 </div>
 <div class="panel grey">
  <h2 class="h">Outils de l'équipe</h2>
  <p style="margin:0 0 12px">Les pièces de l'enquête sont déposées sur le partage
   documentaire interne <b>Partage DFlop</b>. Connectez-vous avec le compte de
   l'équipe&#160;:</p>
  <dl class="facts">
   <dt>Adresse</dt><dd><a href="{share_url}">{share_url}</a></dd>
   <dt>Identifiant</dt><dd><code>{share_user}</code></dd>
   <dt>Mot de passe</dt><dd><code>{share_pass}</code></dd>
  </dl>
 </div>
 <div class="panel grey">
  <h2 class="h">Note de l'équipe</h2>
  <p style="margin:0">Tous les comptes staff suivent la convention
   <code>initiale du prénom + nom</code> et sont répliqués dans notre système
   <b>SAP DFlop ERP</b> sous l'utilisateur SAP correspondant. Retenez-le —
   c'est important pour le système de résultats.</p>
 </div>
</main>{copyjs}</body></html>"""

# Copy button: falls back to execCommand because the Pi is served over plain
# HTTP on a LAN IP, where navigator.clipboard is unavailable.
COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copié \u2713';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

ROBOTS = """User-agent: *
Disallow: /staff-portal-7f3a9
# interne uniquement — ne pas indexer les outils de résultats
Disallow: /sap/
"""

@app.errorhandler(404)
def not_found(_e):
    body = """<div class="page"><div class="panel">
 <h1 class="h">Page introuvable</h1>
 <p class="mute">Cette page n'existe pas ou a été déplacée.</p>
 <a class="btn blue" href="/">Retour à l'accueil</a></div></div>"""
    return html(layout("Page introuvable · DécaFlop", body), 404)

@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")

@app.get("/staff-portal-7f3a9")
def staff():
    # The share runs on the same host the player reached us on, port 8020.
    host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
    share_url = f"http://{host}:{SHARE_PORT}"
    page = (STAFF.replace("{copyjs}", COPY_JS)
                 .replace("{share_url}", escape(share_url))
                 .replace("{share_user}", escape(SHARE_USER))
                 .replace("{share_pass}", escape(SHARE_PASSWORD))
                 .replace("{flag}", FLAG))
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
