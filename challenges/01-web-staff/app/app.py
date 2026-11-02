#!/usr/bin/env python3
"""
01 · Web · EASY
DécaFlop sponsor microsite. There is a 'hidden' staff portal — but it is
listed in robots.txt, which anyone can read.

Teaches: robots.txt recon, that "hidden" != "secret".
"""
import os
import sys
from html import escape

from flask import Flask, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling shop.py / intranet.py
import intranet  # noqa: E402
from shop import shop, layout, html  # noqa: E402

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

# The portal page, in the shared intranet look. {share_url}, {share_user},
# {share_pass} and {flag} are filled in by staff() below (all escaped).
STAFF_BODY = """<h1 class="h1">Équipe événement · finale 2026</h1>
<p class="status">Espace réservé au réseau staff. Ne transférez pas l'adresse de cette page en dehors de l'équipe.</p>
<div class="cols"><div>
 <section class="wp"><h2>Jeton d'accès de l'équipe événement</h2>
  <p>Jeton attribué à l'équipe pour la finale. Communiquez-le uniquement à l'astreinte IT lors de la vérification de votre accès.</p>
  {codebox}
 </section>
 <section class="wp"><h2>Partage DFlop</h2>
  <p>Les pièces de l'enquête sont déposées sur le partage documentaire interne Partage DFlop. Compte de l'équipe&#160;:</p>
  <dl class="kv">
   <dt>Adresse</dt><dd><a href="{share_url}">{share_url}</a></dd>
   <dt>Identifiant</dt><dd><code>{share_user}</code></dd>
   <dt>Mot de passe</dt><dd><code>{share_pass}</code></dd>
  </dl>
 </section>
 <section class="wp"><h2>Comptes et identifiants</h2>
  <p>Tous les comptes staff suivent la convention <code>initiale du prénom + nom</code> et sont répliqués
   dans notre système <b>SAP DFlop ERP</b> sous l'utilisateur SAP correspondant (exemple&#160;: Marie Durand,
   compte <code>m.durand</code>, utilisateur SAP <code>MDURAND</code>). Le système de résultats utilise le même identifiant.</p>
 </section>
</div><div>
 <section class="wp"><h2>Contacts</h2><dl class="kv">
  <dt>Astreinte IT</dt><dd>Poste 300</dd><dt>Bureau de course</dt><dd>Poste 214</dd><dt>Logistique</dt><dd>Poste 118</dd></dl>
 </section>
 <section class="wp"><h2>Rappels</h2><ul class="links">
  <li>Briefing général samedi à 18 h 00, salle B.</li>
  <li>Badge obligatoire sur le parking staff P3.</li>
  <li>Résultats figés à 16 h 00 le jour de la finale.</li></ul>
 </section>
</div></div>"""

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
    share_url = f"http://{intranet.host()}:{SHARE_PORT}"
    body = (STAFF_BODY.replace("{share_url}", escape(share_url))
                      .replace("{share_user}", escape(SHARE_USER))
                      .replace("{share_pass}", escape(SHARE_PASSWORD))
                      .replace("{codebox}", intranet.codebox(FLAG)))
    page = intranet.page("Portail staff - DécaFlop", body, app="staff",
                         site_title="Portail staff", site_href="/staff-portal-7f3a9", logo="PS",
                         topnav=[("/staff-portal-7f3a9", "Accueil", True)],
                         product="Portail staff 3.2", foot_extra="Équipe événement · Finale 2026",
                         scripts=intranet.COPY_JS)
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
