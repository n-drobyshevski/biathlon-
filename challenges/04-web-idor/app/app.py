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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling vitrine.py, fab.py
import vitrine  # noqa: E402  (public DécaFlop site look: athletes are not staff)
import fab  # noqa: E402

app = Flask(__name__)


# Out of the story: the game's floating shortcuts (fab.py) on every HTML page
# (cellule de crise, Outils, and the intranet once the player has logged in to it).
@app.after_request
def shortcuts(resp):
    return fab.add(resp, "challenge")
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
# its time matches the case file (18:42) and VLINDQVIST's last SAP logon in USR02 (18:42:30).
AUDIT = [("31/10/2026 17:02:11", "c.dumont", "Liste de départ FINAL_RACE", "Publication de la version 3"),
         ("01/11/2026 09:14:38", "l.eriksen", "Puces de chronométrage", "Attribution des puces aux finalistes"),
         ("01/11/2026 18:42:47", "v.lindqvist", "Liste de départ FINAL_RACE",
          "Puces de chronométrage échangées entre 3 athlètes")]

# Race record shown on athlete profiles: (category, start wave, bike rack, licence)
RACE = {
    1042: ("Invité (hors classement)", "Vague 3, départ à 8 h 40", "Rack C, emplacement 12", "Pass compétition"),
    1055: ("Senior F", "Vague 1, départ à 8 h 00", "Rack A, emplacement 03", "Licence FFTRI"),
    1071: ("Senior H", "Vague 2, départ à 8 h 20", "Rack B, emplacement 07", "Licence FFTRI"),
}

ROLE_FR = {"admin": "admin", "crew": "staff", "athlete": "athlète"}


def shell(title, body, section="home"):
    signed_in = request.cookies.get("bib")
    tabs = [("/", "Accueil", section == "home")]
    if signed_in:
        tabs.append((f"/profile/{signed_in}", "Mon dossier", section == "profile"))   # escaped by vitrine
    tabs.append(("/infos", "Infos pratiques", section == "infos"))
    user = f"Dossard {signed_in}" if signed_in else None
    return vitrine.page(f"{title} - Espace athlètes - DécaFlop", body, portal="Espace athlètes",
                        tabs=tabs, user=user, logout="/logout" if signed_in else None,
                        scripts=vitrine.COPY_JS)


def account(head, inner):
    """The page header (breadcrumb from the DécaFlop site) then the content."""
    return head + f'<section class="acc"><div class="in">{inner}</div></section>'


ESPACE = ("/", "Espace athlètes")
def login_body():   # per request: links follow the player's host
    return account(vitrine.page_head("Connexion à l'espace athlètes",
                                  "Championnat régional de triathlon, finale 2026.", (ESPACE,)), """
<p class="notice ok" role="status">Lien de connexion valide pour le dossard n°&#160;1042 (finale régionale 2026).</p>
<div class="cols2">
 <div class="panel"><h2>Continuer</h2>
  <p>Ce lien vous a été envoyé par SMS au numéro enregistré lors de votre inscription.
   Il reste valable 24 h après son envoi.</p>
  <div class="btns"><a class="btn" href="/login">Continuer avec le dossard n°&#160;1042</a></div>
  <p class="small mute" style="margin-top:12px">Ce n'est pas votre dossard&#160;? Présentez-vous au bureau de course.</p>
 </div>
 <div class="panel"><h2>Dans votre dossier</h2><ul class="ticks">
  <li>Vague et heure de départ</li><li>Emplacement au parc à vélos</li>
  <li>Documents (certificat, licence)</li><li>Consignes de course</li></ul></div>
</div>""")

def infos_body():
    return account(vitrine.page_head("Infos pratiques", "", (ESPACE,)), """
<div class="panel narrow"><table class="std"><tbody>
<tr><td class="k">Bureau de course</td><td>Ouvert dès 7 h 30 en mairie, salle B, poste 214</td></tr>
<tr><td class="k">Retrait des dossards</td><td>Samedi de 14 h à 19 h, dimanche de 6 h 30 à 7 h 30</td></tr>
<tr><td class="k">Parc à vélos</td><td>Ouverture 6 h 30, fermeture 7 h 50. Casque attaché pour entrer.</td></tr>
<tr><td class="k">Briefing</td><td>Dimanche 7 h 45, ponton du port</td></tr>
<tr><td class="k">Résultats</td><td>Figés à 16 h 00, publiés sur le site de chronométrage</td></tr>
</tbody></table></div>""")


def page(aid):
    trail = (ESPACE, (None, f"Dossier n°&#160;{aid}"))
    if aid not in ATHLETES:
        return shell("Dossier introuvable", account(
            vitrine.page_head(f"Aucun dossier n°&#160;{aid}",
                              "Aucun concurrent ni compte ne correspond à ce numéro.", trail[:1]),
            '<p><a class="txt" href="/profile/1042">Retour à mon dossier</a></p>'), "profile"), 404
    name, role, note = ATHLETES[aid]
    title = f'{escape(name)} <span class="tag {role}">{ROLE_FR[role]}</span>'
    head = vitrine.page_head(title, "", trail[:1], crumb=escape(name))
    if role == "athlete":
        cat, wave, rack, lic = RACE[aid]
        rows = [("Dossard", f"n°&#160;{aid}"), ("Catégorie", cat), ("Départ", wave),
                ("Parc à vélos", rack), ("Justificatif", lic), ("Statut", "Inscription validée")]
        trs = "".join(f'<tr><td class="k">{k}</td><td>{v}</td></tr>' for k, v in rows)
        extra = (f'<div class="panel"><h2>Note de l\'organisation</h2><p>{escape(note)}</p></div>'
                 if note else "")
        inner = ('<div class="cols2"><div>'
                 f'<div class="panel"><h2>Dossier de course</h2><table class="std"><tbody>{trs}</tbody></table></div>'
                 + extra +
                 '</div><div><div class="panel"><h2>Documents</h2><ul class="ticks">'
                 '<li>Certificat médical reçu</li><li>Autorisation parentale non requise</li>'
                 '<li>Décharge de responsabilité signée</li></ul></div></div></div>')
        return shell(f"Dossier n° {aid}", account(head, inner), "profile"), 200
    flag = ""
    if aid == 1000:
        flag = ('<div class="panel"><h2>Jeton d\'audit</h2>'
                '<p class="mute">Empreinte de la dernière exportation du journal.</p>' +
                vitrine.codebox(FLAG) + '</div>')
    if role == "admin":
        trs = "".join(f'<tr><td>{d}</td><td><code>{u}</code></td><td>{o}</td>'
                      f'<td>{a}</td></tr>' for d, u, o, a in AUDIT)
        notes = (f'<div class="panel"><h2>Journal d\'audit</h2><div class="scroll"><table class="std">'
                 f'<thead><tr><th style="width:160px">Date</th><th style="width:110px">Compte</th><th>Objet</th>'
                 f'<th>Action</th></tr></thead><tbody>{trs}</tbody></table></div>'
                 f'<p class="notice warn" style="margin:16px 0 0">{escape(note)}</p></div>')
    else:
        notes = f'<div class="panel"><h2>Note interne</h2><pre class="log">{escape(note)}</pre></div>'
    inner = (f'<div class="panel narrow"><table class="std"><tbody>'
             f'<tr><td class="k">Compte</td><td>n°&#160;{aid}</td></tr>'
             f'<tr><td class="k">Type</td><td>Compte {ROLE_FR[role]} (organisation)</td></tr></tbody></table></div>'
             + notes + flag)
    return shell(f"Compte n° {aid}", account(head, inner), "profile"), 200


@app.errorhandler(404)
def not_found(_e):
    return Response(shell("Page introuvable", account(
        vitrine.page_head("Page introuvable", "Cette page n'existe pas ou a été déplacée.", (ESPACE,)),
        '<p><a class="txt" href="/">Retour à l\'accueil</a></p>')), status=404, mimetype="text/html")


@app.get("/")
def home():
    signed_in = request.cookies.get("bib")
    if signed_in:
        return redirect(f"/profile/{signed_in}") if signed_in.isdigit() else redirect("/logout")
    return Response(shell("Connexion", login_body()), mimetype="text/html")


@app.get("/infos")
def infos():
    return Response(shell("Infos pratiques", infos_body(), "infos"), mimetype="text/html")


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
