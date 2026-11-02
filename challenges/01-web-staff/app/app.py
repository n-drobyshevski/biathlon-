#!/usr/bin/env python3
"""
01 · Web · EASY
DécaFlop sponsor microsite. There is a 'hidden' staff portal — but it is
listed in robots.txt, which anyone can read.

Teaches: robots.txt recon, that "hidden" != "secret".
"""
import os
from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

HEAD = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>"""

# Simple line pictograms for the product grid (no external assets: the Pi
# has no internet).
ICON = {
    "ski": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"><path d="M18 80 74 14M30 84 84 22M70 12c6-4 10 0 8 4M80 20c6-4 10 0 8 4"/></svg>',
    "goggle": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><path d="M14 38h68v18c0 8-6 12-14 12-6 0-10-6-20-6s-14 6-20 6c-8 0-14-4-14-12z"/><path d="M8 46h6M82 46h6"/></svg>',
    "flask": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><rect x="34" y="12" width="28" height="10" rx="2"/><path d="M36 22h24v62H36z"/><path d="M36 44h24"/></svg>',
    "bib": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><path d="M26 16h44l6 66H20z"/><circle cx="36" cy="26" r="2"/><circle cx="60" cy="26" r="2"/><path d="M38 52h20M38 62h12"/></svg>',
}

PRODUCTS = [
    ("ski", "Skiflop", "Skis skating Race 900, presque carbone", "349", "399", "4,1 · 212 avis"),
    ("goggle", "Nordik'O", "Masque anti-buée (buée vendue séparément)", "24", "", "3,2 · 1 048 avis"),
    ("flask", "Bofbof", "Gourde isotherme 0,5 L, garde le thé à peu près chaud", "9", "12", "3,9 · 87 avis"),
    ("bib", "DécaFlop", "Dossard officiel 2026, réplique", "15", "", "4,6 · 33 avis"),
]

def product(icon, brand, title, price, was, rate):
    old = f"<s>{was} €</s>" if was else ""
    return f"""<a class="prod" href="#shop"><div class="ph">{ICON[icon]}</div>
<div class="b"><div class="brand">{brand}</div><div class="t">{title}</div>
<span class="price">{price} €{old}</span><div class="rate">★ {rate}</div></div></a>"""

PAGE = HEAD.replace("{title}", "DécaFlop · Sponsor officiel du Championnat régional de biathlon") + """
<div class="strip"><div class="in"><span>Retrait gratuit dans nos 3 magasins</span>
<span>Retours sous 30 jours*  ·  *voir conditions, en gros</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>sport pour (presque) tous</small></a>
 <form class="search" action="/" role="search"><input name="q" aria-label="Rechercher"
   placeholder="Rechercher parmi 40 000 produits et 3 sports"><button>Rechercher</button></form>
 <nav class="acct"><a class="opt" href="#help">Aide</a><a href="#help">Magasins</a></nav>
</div></header>
<nav class="cats" aria-label="Rayons"><ul>
 <li><a href="#race" aria-current="page">Biathlon</a></li>
 <li><a href="#shop">Ski de fond</a></li><li><a href="#shop">Tir</a></li>
 <li><a href="#shop">Vêtements</a></li><li><a href="#shop">Déstockage</a></li>
 <li><a href="#careers">Recrutement</a></li></ul></nav>
<!--notice-->

<section class="banner" id="race"><div class="in">
 <div>
  <span class="tagline">Sponsor titre · Championnat régional de biathlon</span>
  <h1 class="h">La finale,<br>c'est <em>demain</em></h1>
  <p>Bienvenue sur le site officiel de <b>DécaFlop</b>, fier sponsor titre du
     Championnat régional de biathlon. Skis, carabines, politique de retour discutable.</p>
  <a class="btn" href="#shop">L'équipement course</a><a class="btn line" href="#race">Infos course</a>
 </div>
 <div class="sched">
  <h2 class="h">Programme du jour J</h2>
  <table><tr><td>8 h 30</td><td>Réglage des carabines</td><td>Pas de tir</td></tr>
   <tr><td>10 h 00</td><td>Finale femmes</td><td>Stade</td></tr>
   <tr><td>12 h 30</td><td>Finale hommes</td><td>Stade</td></tr>
   <tr><td>15 h 00</td><td>Podium</td><td>Grand chapiteau</td></tr></table>
  <p class="small mute" style="margin:10px 0 0">Listes de départ, chronométrage et résultats
   sont gérés par notre équipe événement. Le programme public arrive bientôt.</p>
 </div>
</div></section>

<section class="sec" id="shop"><div class="in">
 <div class="row"><h2 class="h">Les bons plans de la semaine</h2><a href="#shop">Tout voir</a></div>
 <div class="grid">""" + "".join(product(*p) for p in PRODUCTS) + """</div>
</div></section>

<section class="sec grey"><div class="in two">
 <div class="tile"><h3 class="h">Location de skis</h3>
  <p>Skis skating préparés course pour le week-end. Fart inclus, dignité non.</p>
  <a class="btn blue" href="#help">Trouver un magasin</a></div>
 <div class="tile dark" id="careers"><h3 class="h">Recrutement</h3>
  <p>DécaFlop recrute toujours. Nous n'avons absolument pas d'espace réservé
     au personnel sur ce site. Merci de ne pas le chercher.</p>
  <a href="#careers">Offres d'emploi (0)</a></div>
</div></section>

<footer class="foot" id="help"><div class="in">
 <div><b>Aide</b><ul><li><a href="#help">Suivi de commande</a></li><li><a href="#help">Retours</a></li><li><a href="#help">Garantie</a></li></ul></div>
 <div><b>Magasins</b><ul><li>DécaFlop Stade</li><li>DécaFlop Centre-ville</li><li>DécaFlop Déstockage (sur le parking)</li></ul></div>
 <div><b>Entreprise</b><ul><li><a href="#careers">Recrutement</a></li><li><a href="#race">Sponsoring</a></li></ul></div>
 <div><b>Service client</b>0 800 FLOP FLOP<br><span class="small">Du lundi au vendredi, quand quelqu'un décroche</span></div>
</div>
<div class="legal"><div class="in"><span>© DécaFlop. Tous flops réservés.</span>
<span>Robots d'indexation bienvenus — voir <a href="/robots.txt">/robots.txt</a></span></div></div>
</footer></body></html>"""

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

SEARCH_NOTICE = """<div class="in" style="padding-top:12px"><p class="note db" role="status"
 style="margin:0">La recherche en ligne est indisponible pendant la compétition.
 Nos vendeurs vous attendent en magasin.</p></div>"""

NOT_FOUND = HEAD.replace("{title}", "Page introuvable · DécaFlop") + """
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>sport pour (presque) tous</small></a>
</div></header>
<main class="page"><div class="panel">
 <h1 class="h">Page introuvable</h1>
 <p class="mute">Cette page n'existe pas ou a été déplacée.</p>
 <a class="btn blue" href="/">Retour à l'accueil</a>
</div></main></body></html>"""

@app.get("/")
def home():
    notice = SEARCH_NOTICE if "q" in request.args else ""
    return Response(PAGE.replace("<!--notice-->", notice), mimetype="text/html")

@app.errorhandler(404)
def not_found(_e):
    return Response(NOT_FOUND, status=404, mimetype="text/html")

@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")

@app.get("/staff-portal-7f3a9")
def staff():
    return Response(STAFF.replace("{copyjs}", COPY_JS).replace("{flag}", FLAG), mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
