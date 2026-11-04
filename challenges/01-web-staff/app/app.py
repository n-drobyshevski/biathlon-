#!/usr/bin/env python3
"""
01 · Web · EASY
DécaFlop sponsor microsite. There is a 'hidden' staff portal — but it is
listed in robots.txt, which anyone can read.

Teaches: robots.txt recon, that "hidden" != "secret".
"""
import base64
import os
import sys
from html import escape

from flask import Flask, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling shop.py / intranet.py
import intranet  # noqa: E402
from shop import shop, layout, html, not_found_body  # noqa: E402

app = Flask(__name__)
app.register_blueprint(shop)   # public storefront pages (decor)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# Crew login for the internal file share "Intranet DécaFlop" (:8020). The staff
# portal hands it out, so solving 01 is how players learn how to log in. Read
# from the SAME env the share reads, with the share's defaults, so the two stay
# in sync (docker-compose feeds both services from one value).
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

# The team service account is no longer printed on the staff portal. Instead it
# ships (base64) in a front-end config asset the public site loads, so players
# recover it from the site's own static resources: view-source -> the
# /assets/site.config.js reference -> base64-decode the svc value. Built from the
# SAME env the share reads, so the two can never drift.
_SVC_B64 = base64.b64encode(f"{SHARE_USER}:{SHARE_PASSWORD}".encode()).decode()
FRONT_CONFIG_JS = (
    "/* DÉCAFLOP front · configuration générée au déploiement (ne pas éditer à la main) */\n"
    "/* FIXME(ops): le compte de service de l'équipe ne devrait pas être livré avec les\n"
    "   assets front du site public. À sortir du bundle avant la prod. */\n"
    "window.DFLOP = window.DFLOP || {};\n"
    "window.DFLOP.intranet = {\n"
    "  host: location.hostname,\n"
    "  port: 8020,\n"
    "  /* compte de service partagé — identifiants encodés base64 (\"user:pass\") */\n"
    f'  svc: "{_SVC_B64}"\n'
    "};\n"
)

# The portal page, in the shared intranet look. {share_url}, {share_user},
# {share_pass} and {flag} are filled in by staff() below (all escaped).
STAFF_BODY = """<h1 class="h1">Équipe événement de la finale 2026</h1>
<p class="status">Espace réservé au réseau staff. Ne transférez pas l'adresse de cette page en dehors de l'équipe.</p>
<div class="cols"><div>
 <section class="wp"><h2>Jeton d'accès de l'équipe événement</h2>
  <p>Jeton attribué à l'équipe pour la finale. Communiquez-le uniquement à l'astreinte IT lors de la vérification de votre accès.</p>
  {codebox}
 </section>
 <section class="wp"><h2>Intranet DécaFlop</h2>
  <p>Les pièces de l'enquête sont déposées sur le partage documentaire interne Intranet DécaFlop.</p>
  <dl class="kv">
   <dt>Adresse</dt><dd><a href="{share_url}">{share_url}</a></dd>
  </dl>
  <p class="status">Le compte de service de l'équipe n'est plus affiché ici&#160;: il a fuité une fois de trop.
   Il reste hélas chargé par les pages publiques du site DécaFlop, à sortir des ressources front.</p>
 </section>
 <section class="wp"><h2>Comptes et identifiants</h2>
  <p>Tous les comptes staff suivent la convention <code>initiale du prénom + nom</code> et sont répliqués
   dans notre système <b>SAP DFlop ERP</b> sous l'utilisateur SAP correspondant (par exemple Marie Durand,
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
# interne uniquement, ne pas indexer les outils de résultats
Disallow: /sap/
"""

@app.errorhandler(404)
def not_found(_e):
    return html(layout("Page introuvable - DécaFlop", not_found_body()), 404)

@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")

@app.get("/assets/site.config.js")
def site_config():
    # Deliberately leaks the team service account (base64) with the front config:
    # the recon path to the Intranet DécaFlop login (the gate for 05/07/09/13/15).
    return Response(FRONT_CONFIG_JS, mimetype="application/javascript")

@app.get("/staff-portal-7f3a9")
def staff():
    # The share runs on the same host the player reached us on, port 8020
    # (or its own share.<domain> subdomain when hosted online).
    share_url = intranet.app_url("intranet", "")      # http://host:8020 offline, share.<domain> online
    body = (STAFF_BODY.replace("{share_url}", escape(share_url))
                      .replace("{codebox}", intranet.codebox(FLAG)))
    page = intranet.page("Portail staff - DécaFlop", body, app="staff",
                         site_title="Portail staff", site_href="/staff-portal-7f3a9", logo="PS",
                         topnav=[("/staff-portal-7f3a9", "Accueil", True)],
                         product="Portail staff 3.2", foot_extra="Équipe événement de la finale 2026",
                         scripts=intranet.COPY_JS)
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
