#!/usr/bin/env python3
"""
04 · Web · MEDIUM (IDOR)
DécaFlop Athlete Portal. You are logged in as bib #1042. The profile page is
/profile/<id> and does NOT check that the id belongs to you. Walk the ids
(crew/admin accounts have low numbers) to read someone else's profile.

Teaches: Insecure Direct Object Reference, horizontal privilege escalation.
"""
import os
import sys
from html import escape

from flask import Flask, Response, redirect, make_response, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# id -> (name, role, note)
ATHLETES = {
    1000: ("Administration événement DécaFlop", "admin",
           "Modification hors procédure de la liste de départ officielle FINAL_RACE par le compte "
           "staff v.lindqvist, répliqué dans SAP DFlop ERP sous l'utilisateur VLINDQVIST. "
           "À remonter à l'équipe résultats SAP."),
    1001: ("Chef chronométreur", "crew",
           "La cabine de chronométrage est sur le Wi-Fi staff 'DECAFLOP-TIMING'. "
           "Arrêtez d'envoyer l'identifiant de la cabine en HTTP en clair !"),
    1042: ("Compte invité de l'équipe IT", "athlete", ""),
    1055: ("Astrid Bjornsen", "athlete", "Favorite pour le sprint."),
    1071: ("Mikkel Haugen", "athlete", "Excellent nageur, coureur moyen."),
}

# Audit trail shown on the admin account (1000). The last line is the sabotage;
# its time follows VLINDQVIST's last SAP logon in the USR02 export (01/11 18:42:30).
AUDIT = [("31/10/2026 17:02:11", "c.dumont", "Liste de départ FINAL_RACE", "Publication de la version 3"),
         ("01/11/2026 09:14:38", "l.eriksen", "Puces de chronométrage", "Attribution des puces aux finalistes"),
         ("01/11/2026 18:47:52", "v.lindqvist", "Liste de départ FINAL_RACE",
          "Puces de chronométrage échangées entre 3 athlètes")]

# Race record shown on athlete profiles: (category, start wave, bike rack, licence)
RACE = {
    1042: ("Invité (hors classement)", "Vague 3, départ à 8 h 40", "Rack C, emplacement 12", "Pass compétition"),
    1055: ("Senior F", "Vague 1, départ à 8 h 00", "Rack A, emplacement 03", "Licence FFTRI"),
    1071: ("Senior H", "Vague 2, départ à 8 h 20", "Rack B, emplacement 07", "Licence FFTRI"),
}

ROLE_FR = {"admin": "admin", "crew": "staff", "athlete": "athlète"}
PRODUCT = "Espace athlètes 5.4.2"


def shell(title, body, section="home"):
    signed_in = request.cookies.get("bib")
    topnav = [("/", "Accueil", section == "home")]
    if signed_in:
        topnav.append((f"/profile/{signed_in}", "Mon dossier", section == "profile"))   # escaped by intranet
    topnav.append(("/infos", "Infos pratiques", section == "infos"))
    user = f"Dossard {signed_in}" if signed_in else None
    return intranet.page(f"{title} - Espace athlètes", body, app="athletes",
                         site_title="Espace athlètes", site_href="/", logo="EA", topnav=topnav,
                         user=user, logout="/logout" if signed_in else None,
                         product=PRODUCT, foot_extra="Championnat régional de triathlon, finale 2026",
                         scripts=intranet.COPY_JS)


LOGIN = """<h1 class="h1">Connexion à l'espace athlètes</h1>
<p class="status ok">Lien de connexion valide pour le dossard n°&#160;1042 (finale régionale 2026).</p>
<div class="cols"><div>
 <section class="wp"><h2>Continuer</h2>
  <p>Ce lien vous a été envoyé par SMS au numéro enregistré lors de votre inscription.
   Il reste valable 24 h après son envoi.</p>
  <p><a class="btn" href="/login">Continuer avec le dossard n°&#160;1042</a></p>
  <p class="mute" style="font-size:12px">Ce n'est pas votre dossard&#160;? Présentez-vous au bureau de course.</p>
 </section>
</div><div>
 <section class="wp"><h2>Dans votre dossier</h2><ul class="links">
  <li>Vague et heure de départ</li><li>Emplacement au parc à vélos</li>
  <li>Documents (certificat, licence)</li><li>Consignes de course</li></ul></section>
</div></div>"""

INFOS = """<h1 class="h1">Infos pratiques</h1>
<table class="list data"><tbody>
<tr><td style="width:220px">Bureau de course</td><td class="wrap">Ouvert dès 7 h 30 en mairie, salle B, poste 214</td></tr>
<tr><td>Retrait des dossards</td><td class="wrap">Samedi de 14 h à 19 h, dimanche de 6 h 30 à 7 h 30</td></tr>
<tr><td>Parc à vélos</td><td class="wrap">Ouverture 6 h 30, fermeture 7 h 50. Casque attaché pour entrer.</td></tr>
<tr><td>Briefing</td><td class="wrap">Dimanche 7 h 45, ponton du port</td></tr>
<tr><td>Résultats</td><td class="wrap">Figés à 16 h 00, publiés sur le site de chronométrage</td></tr>
</tbody></table>"""


def page(aid):
    if aid not in ATHLETES:
        return shell("Dossier introuvable", f"""<p class="crumbs">Dossiers<span class="sep">›</span>n°&#160;{aid}</p>
<h1 class="h1">Aucun dossier n°&#160;{aid}</h1>
<p class="lead">Aucun concurrent ni compte ne correspond à ce numéro.</p>
<p><a href="/profile/1042">Retour à mon dossier</a></p>""", "profile"), 404
    name, role, note = ATHLETES[aid]
    crumbs = f'<p class="crumbs">Dossiers<span class="sep">›</span>n°&#160;{aid}</p>'
    title = f'<h1 class="h1">{escape(name)} <span class="tag {role}">{ROLE_FR[role]}</span></h1>'
    if role == "athlete":
        cat, wave, rack, lic = RACE[aid]
        rows = [("Dossard", f"n°&#160;{aid}"), ("Catégorie", cat), ("Départ", wave),
                ("Parc à vélos", rack), ("Justificatif", lic), ("Statut", "Inscription validée")]
        trs = "".join(f'<tr><td style="width:180px" class="mute">{k}</td><td class="wrap">{v}</td></tr>'
                      for k, v in rows)
        extra = (f'<section class="wp"><h2>Note de l\'organisation</h2><p>{escape(note)}</p></section>'
                 if note else "")
        body = (crumbs + title +
                '<div class="cols"><div>'
                f'<section class="wp"><h2>Dossier de course</h2><table class="list data"><tbody>{trs}</tbody></table></section>'
                + extra +
                '</div><div><section class="wp"><h2>Documents</h2><ul class="links">'
                '<li>Certificat médical reçu</li><li>Autorisation parentale non requise</li>'
                '<li>Décharge de responsabilité signée</li></ul></section></div></div>')
        return shell(f"Dossier n° {aid}", body, "profile"), 200
    flag = ""
    if aid == 1000:
        flag = ('<section class="wp"><h2>Jeton d\'audit</h2>'
                '<p class="mute">Empreinte de la dernière exportation du journal.</p>' +
                intranet.codebox(FLAG) + '</section>')
    if role == "admin":
        trs = "".join(f'<tr><td class="num">{d}</td><td><code>{u}</code></td><td class="wrap">{o}</td>'
                      f'<td class="wrap">{a}</td></tr>' for d, u, o, a in AUDIT)
        notes = (f'<section class="wp"><h2>Journal d\'audit</h2><div class="scroll"><table class="list data">'
                 f'<thead><tr><th style="width:160px">Date</th><th style="width:110px">Compte</th><th>Objet</th>'
                 f'<th>Action</th></tr></thead><tbody>{trs}</tbody></table></div>'
                 f'<p class="status" style="margin:12px 0 0">{escape(note)}</p></section>')
    else:
        notes = f'<section class="wp"><h2>Note interne</h2><div class="log"><pre>{escape(note)}</pre></div></section>'
    body = (crumbs + title +
            f'<table class="list data" style="max-width:620px;margin-bottom:16px"><tbody>'
            f'<tr><td style="width:180px" class="mute">Compte</td><td>n°&#160;{aid}</td></tr>'
            f'<tr><td class="mute">Type</td><td>Compte {ROLE_FR[role]} (organisation)</td></tr></tbody></table>'
            + notes + flag)
    return shell(f"Compte n° {aid}", body, "profile"), 200


@app.errorhandler(404)
def not_found(_e):
    return Response(shell("Page introuvable", '<h1 class="h1">Page introuvable</h1>'
                          '<p class="lead">Cette page n\'existe pas ou a été déplacée.</p>'
                          '<p><a href="/">Retour à l\'accueil</a></p>'), status=404, mimetype="text/html")


@app.get("/")
def home():
    signed_in = request.cookies.get("bib")
    if signed_in:
        return redirect(f"/profile/{signed_in}") if signed_in.isdigit() else redirect("/logout")
    return Response(shell("Connexion", LOGIN), mimetype="text/html")


@app.get("/infos")
def infos():
    return Response(shell("Infos pratiques", INFOS, "infos"), mimetype="text/html")


@app.get("/login")
def login():
    r = make_response(redirect("/profile/1042"))
    r.set_cookie("bib", "1042")
    return r


@app.get("/logout")
def logout():
    r = make_response(redirect("/"))
    r.delete_cookie("bib")
    return r


@app.get("/profile/<int:aid>")
def profile(aid):
    # VULN: trusts the URL id, never compares to the signed-in bib cookie.
    body, status = page(aid)
    return Response(body, status=status, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
