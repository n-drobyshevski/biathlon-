#!/usr/bin/env python3
"""
Partage DFlop — DécaFlop's intranet site with the internal document library.
Its own container, not a challenge: players log in with the crew account the
staff portal (challenge 01) hands out, then browse department folders to find
the evidence files instead of downloading them from the hub.

Pages: home (internal news + recent activity), Documents (the library), file
search, staff directory (annuaire), recent activity, help. The look comes from
the shared intranet chrome (intranet.py + static/intranet.css).

- Files are read from HANDOUT_DIR (docker-compose mounts handouts/dist there,
  read-only) and served byte-for-byte through an explicit path -> filename map.
  Nothing outside that map is downloadable; there is no path traversal.
- Mundane text files are generated inline as decoys; they hold no clues.
- The search is a plain, case- and accent-insensitive substring match over the
  names in that map (no database, no templates). The query is only ever shown
  html-escaped, inside the search field. Sort and filter parameters are
  whitelisted and never echoed.
"""
import hmac
import os
import sys
import time
import unicodedata
import uuid
from html import escape as esc
from urllib.parse import quote, urlencode

from flask import Flask, Response, abort, redirect, request, send_from_directory, session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402
from intranet import icon  # noqa: E402

HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

app = Flask(__name__)
app.secret_key = os.environ.get("SHARE_SECRET_KEY") or os.urandom(32)

PRODUCT = "Partage DFlop 16.0.4351"
SITE = "Partage DFlop"
LAST_LOGIN = "01/11/2026 à 22:41 depuis 10.20.0.14"


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")


def fr_size(n):
    size = float(n)
    for unit in ("o", "Ko", "Mo"):
        if size < 1024 or unit == "Mo":
            return f"{size:.0f} {unit}" if unit == "o" else (f"{size:.1f} {unit}").replace(".", ",")
        size /= 1024


def fr_dt(when, sep=" "):
    """'2026-11-01 09:12' -> '01/11/2026 09:12'."""
    d, t = when.split()
    y, m, day = d.split("-")
    return f"{day}/{m}/{y}{sep}{t}"


# --------------------------------------------------------------------------
# Content model. Each file: path (segments, last = filename), kind (icon),
# type, author, when ('YYYY-MM-DD HH:MM'), version, description, and either a
# handout 'source' (served from HANDOUT_DIR) or decoy 'text' (generated).
# --------------------------------------------------------------------------
DEPT_ORDER = ["Direction de course", "Chronométrage", "Arbitrage", "Basis SAP", "IT",
              "Logistique", "Communication"]
DEPT_DESC = {
    "Direction de course": "Organisation de la finale, réunions, dossier incident",
    "Chronométrage": "Captures et documents de la cabine de chronométrage",
    "Arbitrage": "Jury, consignes et pièces remises par les arbitres",
    "Basis SAP": "Administration du système SAP DFlop ERP (DFL)",
    "IT": "Outils, procédures et sauvegardes de l'équipe IT",
    "Logistique": "Bénévoles, matériel, plans d'accès",
    "Communication": "Presse et visuels de l'événement",
}


def ev(path, kind, typ, who, when, ver, desc=""):
    return {"path": path, "name": path[-1], "source": path[-1], "kind": kind, "type": typ,
            "who": who, "when": when, "ver": ver, "desc": desc, "decoy": False}


def decoy(path, kind, typ, who, when, ver, text, desc=""):
    return {"path": path, "name": path[-1], "source": None, "kind": kind, "type": typ,
            "who": who, "when": when, "ver": ver, "desc": desc, "decoy": True, "text": text}


_LISEZMOI = ("Dossier d'outils de l'equipe IT d'urgence.\n\n"
             "- wordlist.txt : petite liste de mots utilisee pour les tests.\n\n"
             "Merci de ne rien supprimer sans prevenir l'astreinte IT (poste 300).\n"
             "Ce dossier est partage avec toute l'equipe evenement.\n")
_PLANNING = ("Planning des benevoles - week-end de la finale\n"
             "=============================================\n\n"
             "Samedi\n"
             "  07h00-12h00  Accueil / dossards      8 benevoles\n"
             "  09h00-15h00  Ravitaillement velo     6 benevoles\n"
             "  10h00-16h00  Point d'eau course      5 benevoles\n\n"
             "Dimanche\n"
             "  06h30-13h00  Parc a velos            6 benevoles\n"
             "  08h00-17h00  Village partenaires     4 benevoles\n\n"
             "Contact logistique : poste 118. Pensez a emporter de l'eau.\n")
_NOTE_PARCOURS = ("Note parcours - rappel organisation\n"
                  "-----------------------------------\n\n"
                  "Les trois boucles course longent le port. Balisage pose la veille,\n"
                  "retire le dimanche soir. Navettes spectateurs toutes les 15 minutes\n"
                  "depuis le centre-ville.\n\n"
                  "Rien a signaler cote parcours. Document de travail, non contractuel.\n")
_CONSIGNES = ("Consignes jury - rappel\n"
              "-----------------------\n\n"
              "- Casque attache avant de toucher le velo.\n"
              "- Drafting interdit : 1 minute de penalite.\n"
              "- Combinaison autorisee si l'eau est sous 22 C.\n\n"
              "Pour toute reclamation, voir la direction de course (bureau de course).\n")
_NOTES_BASIS = ("Notes Basis - SAP DFlop ERP (DFL / mandant 001)\n"
                "===============================================\n\n"
                "Rappels pour l'equipe, a trier apres la finale :\n\n"
                "- Moniteur du gateway SAP accessible sur le reseau staff (port 8014).\n"
                "  A verifier : les ACL reginfo/secinfo sont restees sur les valeurs\n"
                "  par defaut depuis l'installation.\n"
                "- Les rapports maison (dont l'export des resultats) sont dans le\n"
                "  dossier 'Basis SAP / Developpements'. Rappel : ne pas laisser de\n"
                "  jeton en dur dans le code.\n"
                "- L'export de la table USR02 est archive dans 'Basis SAP / Exports'.\n\n"
                "Document de travail interne, sans valeur officielle. Ne pas diffuser.\n")
_CR_SECU = ("Compte rendu - reunion securite du 27/10/2026\n"
            "=============================================\n\n"
            "Presents : C. Dumont (direction de course), H. Martin, S. Lambert (arbitrage),\n"
            "E. Roux (logistique), N. Petit (DSI), poste de secours (Croix-Blanche).\n\n"
            "1. Natation : 2 bateaux + 4 kayaks. Bouee de rappel a 750 m.\n"
            "   Report possible de 30 min si brouillard sur le port.\n"
            "2. Velo : fermeture des routes 7h30-12h30, arretes prefectoraux recus.\n"
            "3. Course : 3 points d'eau, 1 poste de secours mobile.\n"
            "4. Radios : 24 postes, canal 3 pour la direction, canal 5 pour la logistique.\n"
            "5. Meteo : 14 C prevus, eau a 17 C (combinaison autorisee).\n\n"
            "Prochaine reunion : briefing general samedi 18h00, salle B.\n")
_RADIOS = ("id;modele;canal;affecte_a;etat\n"
           "R01;TK-3401;3;Direction de course;OK\n"
           "R02;TK-3401;3;Direction de course;OK\n"
           "R03;TK-3401;3;Bureau de course;OK\n"
           "R04;TK-3401;4;Arbitrage - natation;OK\n"
           "R05;TK-3401;4;Arbitrage - velo;batterie faible\n"
           "R06;TK-3401;4;Arbitrage - course;OK\n"
           "R07;TK-3401;5;Logistique - parc a velos;OK\n"
           "R08;TK-3401;5;Logistique - ravitaillement;OK\n"
           "R09;TK-3401;5;Logistique - village;antenne a remplacer\n"
           "R10;TK-3401;6;Cabine de chronometrage;OK\n"
           "R11;TK-3401;6;Poste de secours;OK\n"
           "R12;TK-3401;6;IT - astreinte;OK\n")
_POLITIQUE = ("Politique de mots de passe - rappel DSI (oct. 2026)\n"
              "==================================================\n\n"
              "- 12 caracteres minimum, dont une majuscule et un chiffre.\n"
              "- Renouvellement tous les 90 jours, pas de reutilisation des 5 derniers.\n"
              "- Un compte = une personne. Les comptes d'equipe sont temporaires et\n"
              "  desactives apres l'evenement.\n"
              "- Ne pas cocher \"memoriser\" dans les outils installes sur les portables\n"
              "  partages.\n"
              "- Verrouillez votre poste (Windows + L) des que vous le quittez.\n\n"
              "Questions : astreinte IT, poste 300.\n")
_POINTS = ("Points de chronometrage - finale 2026\n"
           "=====================================\n\n"
           "P0  Depart natation (ponton du port)           km  0,0\n"
           "P1  Sortie de l'eau / entree parc              km  1,5\n"
           "P2  Sortie T1                                  km  1,6\n"
           "P3  Velo - mi-parcours (rond-point des Iles)   km 21,6\n"
           "P4  Entree T2                                  km 41,6\n"
           "P5  Course - fin de boucle 2                   km 48,3\n"
           "P6  Arrivee (quai d'honneur)                   km 51,6\n\n"
           "Tapis poses le samedi a 16h00. Verification croisee avec les puces le\n"
           "dimanche a 6h30.\n")
_COMMUNIQUE = ("COMMUNIQUE DE PRESSE - projet v3 (ne pas diffuser avant validation)\n\n"
               "DecaFlop, partenaire titre du Championnat regional de triathlon\n\n"
               "Dimanche, 412 athletes sont attendus sur le port pour la finale du\n"
               "championnat regional. DecaFlop equipe les benevoles et tient un village\n"
               "partenaires de 8h a 17h, avec un atelier de reglage velo gratuit.\n\n"
               "Contact presse : service marketing, poste 120.\n")
_BADGES = ("Commande de badges - finale 2026\n"
           "================================\n\n"
           "Benevoles ............ 46\n"
           "Arbitres ............. 12\n"
           "Chronometrage ........  6\n"
           "Secours .............. 14\n"
           "Presse ...............  9\n"
           "Partenaires .......... 20\n"
           "IT ...................  4\n\n"
           "Livraison prevue vendredi au bureau de course. Pochettes et tours de cou\n"
           "en stock (carton 3, local logistique).\n")

FILES = [
    ev(("Chronométrage", "Captures", "timing_booth.pcap"), "pcap", "Capture réseau (PCAP)",
       "Équipe IT d'urgence", "2026-11-01 22:14", "1.0", "Capture du Wi-Fi staff, cabine de chronométrage"),
    ev(("Arbitrage", "Pièces", "referee_usb.img"), "img", "Image disque brute",
       "Arbitrage", "2026-11-01 20:03", "1.0", "Image de la clé USB retrouvée en cabine"),
    ev(("Basis SAP", "Exports", "SAP_USR02_export.csv"), "csv", "Feuille CSV",
       "Basis SAP", "2026-11-01 09:12", "1.0", "Export de la table USR02 (mandant 001)"),
    ev(("Basis SAP", "Exports", "sap_hint.txt"), "txt", "Document texte",
       "Basis SAP", "2026-11-01 09:15", "1.2", "Note d'accompagnement de l'export"),
    ev(("IT", "Outils", "wordlist.txt"), "txt", "Document texte",
       "Équipe IT d'urgence", "2026-10-31 17:40", "2.1", "Liste de mots"),
    ev(("Direction de course", "Dossier incident", "case_file.zip"), "zip", "Archive ZIP (chiffrée)",
       "Direction de course", "2026-11-02 08:05", "1.0", "Pièces du dossier incident"),
    ev(("IT", "Sauvegardes postes", "portable-equipe-03", "dflop_erp.sap"), "sap", "Raccourci SAP GUI",
       "Équipe IT d'urgence", "2026-10-30 11:20", "1.0", "Sauvegarde du bureau du portable 03"),
    ev(("Basis SAP", "Développements", "ZDFLOP_RESULT_EXPORT.abap"), "abap", "Source ABAP",
       "Basis SAP", "2026-10-28 16:48", "3.4", "Rapport d'export des résultats (RFC)"),
    # --- mundane decoys (generated text, no clues) ---
    # A Basis working note that casually names the SAP gateway monitor (:8014,
    # challenge 14) and the ABAP dev folder — service names only, no secrets.
    decoy(("Basis SAP", "notes_basis.txt"), "txt", "Note interne", "Basis SAP",
          "2026-10-29 15:12", "1.3", _NOTES_BASIS, "Notes de l'équipe Basis"),
    decoy(("IT", "Outils", "LISEZ-MOI.txt"), "txt", "Note interne", "Équipe IT d'urgence",
          "2026-10-31 17:41", "1.0", _LISEZMOI),
    decoy(("IT", "Procédures", "politique_mots_de_passe.txt"), "txt", "Note interne", "Nicolas Petit",
          "2026-10-20 10:02", "4.0", _POLITIQUE, "Rappel de la DSI"),
    decoy(("Logistique", "Bénévoles", "planning_benevoles.txt"), "txt", "Note interne", "Élodie Roux",
          "2026-10-28 14:05", "1.6", _PLANNING),
    decoy(("Logistique", "Bénévoles", "commande_badges.txt"), "txt", "Note interne", "Élodie Roux",
          "2026-10-23 11:47", "1.1", _BADGES),
    decoy(("Logistique", "Matériel", "inventaire_radios.csv"), "csv", "Feuille CSV", "Logistique",
          "2026-10-29 18:30", "2.0", _RADIOS, "Affectation des radios"),
    decoy(("Direction de course", "Dossier incident", "note_parcours.txt"), "txt", "Note interne",
          "Direction de course", "2026-10-30 10:22", "1.0", _NOTE_PARCOURS),
    decoy(("Direction de course", "Réunions", "CR_reunion_securite_2026-10-27.txt"), "txt",
          "Compte rendu", "Hugo Martin", "2026-10-27 19:10", "1.0", _CR_SECU),
    decoy(("Chronométrage", "Parcours", "points_chronometrage.txt"), "txt", "Note interne",
          "Lars Eriksen", "2026-10-26 09:44", "1.2", _POINTS),
    decoy(("Arbitrage", "Pièces", "consignes_jury.txt"), "txt", "Note interne", "Sophie Lambert",
          "2026-10-29 09:30", "1.0", _CONSIGNES),
    decoy(("Communication", "Presse", "communique_finale_2026_v3.txt"), "txt", "Communiqué (projet)",
          "Camille Fontaine", "2026-10-30 16:25", "0.3", _COMMUNIQUE),
]
FILES_BY_PATH = {f["path"]: f for f in FILES}
# Folders that exist but hold nothing yet.
EMPTY_FOLDERS = [("Direction de course", "Archives 2025"), ("Communication", "Visuels"),
                 ("IT", "Sauvegardes postes", "portable-equipe-01")]


def build_tree():
    root = {"name": "Documents", "path": (), "children": {}, "files": []}

    def ensure(segs):
        node = root
        for i, s in enumerate(segs):
            node = node["children"].setdefault(
                s, {"name": s, "path": tuple(segs[:i + 1]), "children": {}, "files": []})
        return node
    for f in FILES:
        ensure(f["path"][:-1])["files"].append(f)
    for p in EMPTY_FOLDERS:
        ensure(p)
    return root


TREE = build_tree()


def child_folders(node):
    kids = list(node["children"].values())
    if node["path"] == ():
        kids.sort(key=lambda n: DEPT_ORDER.index(n["name"]) if n["name"] in DEPT_ORDER else 99)
    else:
        kids.sort(key=lambda n: n["name"].lower())
    return kids


def get_node(segs):
    node = TREE
    for s in segs:
        node = node["children"].get(s)
        if node is None:
            return None
    return node


def descendant_files(node):
    out = list(node["files"])
    for c in node["children"].values():
        out += descendant_files(c)
    return out


def latest(node):
    fs = descendant_files(node)
    return max(fs, key=lambda f: f["when"]) if fs else None


def folder_href(path):
    return "/documents" if not path else "/d/" + "/".join(quote(s) for s in path)


def download_href(f):
    return "/telecharger/" + "/".join(quote(s) for s in f["path"])


def is_available(f):
    if f["decoy"]:
        return True
    return os.path.isfile(os.path.join(HANDOUT_DIR, f["source"]))


def size_bytes(f):
    if f["decoy"]:
        return len(f["text"].encode("utf-8"))
    p = os.path.join(HANDOUT_DIR, f["source"])
    return os.path.getsize(p) if os.path.isfile(p) else None


def file_size(f):
    n = size_bytes(f)
    return fr_size(n) if n is not None else None


def elements_label(n):
    return str(n) + (" élément" if n == 1 else " éléments")


def fold(s):
    """Lower-case, accent-free form used for matching."""
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
# Chrome
# --------------------------------------------------------------------------
def display_user():
    u = session.get("user", SHARE_USER)
    return "Équipe IT d'urgence" if u == "equipe-it" else u


TOPNAV = [("/", "Accueil"), ("/documents", "Documents"), ("/annuaire", "Annuaire"),
          ("/activite", "Activité récente")]


def quick_launch(current_section, current_path=()):
    def a(href, label, on):
        return f'<a href="{href}"{intranet.CUR if on else ""}>{esc(label)}</a>'
    depts = "".join(
        f'<li>{a(folder_href(d["path"]), d["name"], current_path[:1] == d["path"])}</li>'
        for d in child_folders(TREE))
    return ('<ul>'
            f'<li>{a("/", "Accueil", current_section == "home")}</li>'
            f'<li>{a("/documents", "Documents", current_section == "docs" and not current_path)}'
            f'<ul>{depts}</ul></li>'
            f'<li>{a("/annuaire", "Annuaire", current_section == "dir")}</li>'
            f'<li>{a("/activite", "Activité récente", current_section == "activity")}</li>'
            f'<li>{a("/aide", "Aide", current_section == "help")}</li>'
            '</ul>')


def page(title, section, body, current_path=(), q=""):
    suite_on = {"home": "news", "docs": "docs", "dir": "dir"}.get(section)
    top_on = {"home": "/", "docs": "/documents", "dir": "/annuaire", "activity": "/activite"}.get(section)
    topnav = [(h, lbl, h == top_on) for h, lbl in TOPNAV]
    return intranet.page(
        title + " - " + SITE, body, app="intranet", site_title=SITE, site_href="/", logo="DF",
        topnav=topnav, quick=quick_launch(section, current_path),
        tabs=("Parcourir", "Page"), tabs_right=("Partager", "Suivre"),
        search=intranet.search_box("/recherche", "Rechercher sur ce site", q),
        user=display_user(), logout="/logout", suite_on=suite_on, product=PRODUCT,
        foot_extra="Dernière connexion le " + LAST_LOGIN)


# --------------------------------------------------------------------------
# Auth (the login is not a puzzle — the staff portal hands out the account)
# --------------------------------------------------------------------------
_FAILS = {}
_WINDOW = 60.0
_LIMIT = 6


def _too_many(ip):
    now = time.time()
    xs = [t for t in _FAILS.get(ip, []) if now - t < _WINDOW]
    _FAILS[ip] = xs
    return len(xs) >= _LIMIT


def _record_fail(ip):
    _FAILS.setdefault(ip, []).append(time.time())


def _bare_login(u):
    """Accept DECAFLOP\\user and user@decaflop.local as well as user."""
    u = u.strip()
    if "\\" in u and u.split("\\", 1)[0].lower() == "decaflop":
        u = u.split("\\", 1)[1]
    if u.lower().endswith("@decaflop.local"):
        u = u[: -len("@decaflop.local")]
    return u


@app.before_request
def require_login():
    if request.endpoint in ("login", "logout", "static"):
        return None
    if not session.get("ok"):
        return redirect("/login")
    return None


def login_page(error="", status=200, user=""):
    err = f'<p class="status err" role="alert">{esc(error)}</p>' if error else ""
    body = (intranet.head("Connexion - Intranet DécaFlop") +
            '<div class="signin"><div class="art" aria-hidden="true"><b>DÉCA<i>FLOP</i></b>'
            '<span>Intranet du réseau staff</span></div>'
            '<div class="pane"><div class="wordmark">DÉCA<i>FLOP</i></div>'
            '<h1>Connexion</h1><p>Connectez-vous avec votre compte DécaFlop.</p>'
            '<form method="post" action="/login">' + err +
            '<label for="u">Identifiant</label>'
            f'<input class="in" id="u" name="identifiant" value="{esc(user)}" placeholder="DECAFLOP\\identifiant" '
            'autocomplete="username" autocapitalize="none" spellcheck="false">'
            '<label for="p">Mot de passe</label>'
            '<input class="in" id="p" name="motdepasse" type="password" autocomplete="current-password">'
            '<button class="btn" type="submit">Connexion</button></form>'
            '<small>Accès réservé au personnel DécaFlop et aux prestataires autorisés. Les connexions '
            'sont journalisées conformément à la charte informatique.</small>'
            '<small>Mot de passe oublié ? Appelez l\'assistance au poste 300.</small>'
            '<div class="ft">© 2026 DécaFlop, Direction des Systèmes d\'Information</div>'
            '</div></div></body></html>')
    return html(body, status)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("ok"):
            return redirect("/")
        return login_page()
    ip = request.remote_addr or "?"
    raw = request.form.get("identifiant", "")
    if _too_many(ip):
        return login_page("Trop de tentatives. Patientez quelques instants avant de réessayer.", 429, raw)
    u = _bare_login(raw)
    p = request.form.get("motdepasse", "")
    if hmac.compare_digest(u, SHARE_USER) and hmac.compare_digest(p, SHARE_PASSWORD):
        session.clear()
        session["ok"] = True
        session["user"] = SHARE_USER
        _FAILS.pop(ip, None)
        return redirect("/")
    _record_fail(ip)
    return login_page("Identifiant ou mot de passe incorrect.", 401, raw)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


# --------------------------------------------------------------------------
# Home, activity, help
# --------------------------------------------------------------------------
NEWS = [
    ("Cellule de crise activée après un incident sur la liste de départ", "Direction de course",
     "2026-11-02 07:40",
     "Une anomalie a été détectée sur la liste de départ de la finale. L'équipe IT d'urgence a accès "
     "au partage pour l'enquête. Merci de ne rien supprimer ni déplacer dans "
     "<a href=\"/d/Direction%20de%20course/Dossier%20incident\">Direction de course / Dossier incident</a>."),
    ("Maintenance du système SAP DFL samedi 7 novembre de 22 h à 2 h", "Basis SAP", "2026-10-29 15:30",
     "Le système DFL (mandant 001) sera indisponible pendant l'application du support package de "
     "novembre. Les saisies de résultats doivent être terminées avant 21 h 30."),
    ("Plan de circulation et navettes pour la finale", "Logistique", "2026-10-28 12:10",
     "Navettes depuis le centre-ville toutes les 15 minutes à partir de 6 h. Parking staff P3, badge "
     "obligatoire. Le planning des bénévoles est dans "
     "<a href=\"/d/Logistique/B%C3%A9n%C3%A9voles\">Logistique / Bénévoles</a>."),
    ("Rappel sur la politique de mots de passe", "Direction des Systèmes d'Information", "2026-10-20 10:05",
     "Les comptes d'équipe créés pour l'événement seront désactivés le lundi suivant la finale. "
     "Le rappel complet est dans <a href=\"/d/IT/Proc%C3%A9dures\">IT / Procédures</a>."),
]


def activity_items(limit=None):
    fs = sorted(FILES, key=lambda f: f["when"], reverse=True)
    if limit:
        fs = fs[:limit]
    out = []
    for f in fs:
        verb = "a ajouté" if f["ver"] in ("1.0", "0.1") else "a modifié"
        folder = f["path"][:-1]
        out.append(f'<li>{icon(f["kind"])}<div><a href="{folder_href(folder)}?f={quote(f["name"])}">'
                   f'{esc(f["name"])}</a><small>{esc(f["who"])} {verb} ce fichier le {fr_dt(f["when"], " à ")}, '
                   f'dans {esc(" / ".join(folder))}</small></div></li>')
    return '<ul class="feed">' + "".join(out) + '</ul>'


@app.get("/")
def root():
    news = "".join(
        f'<li><h3>{esc(t)}</h3><p class="by">{esc(who)}, le {fr_dt(when, " à ")}</p><p>{text}</p></li>'
        for t, who, when, text in NEWS)
    apps = "".join(
        f'<li><a href="{esc(intranet.app_url(k))}">{esc(intranet.APPS[k][1])}</a></li>'
        for k in intranet.ORDER if k != "intranet")
    body = ('<h1 class="h1">Accueil</h1>'
            '<div class="cols"><div>'
            f'<section class="wp"><h2>Annonces</h2><ul class="news">{news}</ul></section>'
            f'<section class="wp"><h2>Activité récente</h2>{activity_items(6)}'
            '<p style="margin-top:8px"><a href="/activite">Toute l\'activité</a></p></section>'
            '</div><div>'
            '<section class="wp"><h2>Liens rapides</h2><ul class="links">'
            '<li><a href="/documents">Documents</a></li><li><a href="/annuaire">Annuaire</a></li>'
            f'<li><a href="/aide">Aide et assistance</a></li>{apps}</ul></section>'
            '<section class="wp"><h2>Ma session</h2><dl class="kv">'
            f'<dt>Compte</dt><dd>{esc(session.get("user", SHARE_USER))}</dd>'
            '<dt>Droits</dt><dd>Lecture (bibliothèque Documents)</dd>'
            f'<dt>Dernière connexion</dt><dd>{LAST_LOGIN}</dd>'
            '<dt>Session</dt><dd>Expire après 30 min d\'inactivité</dd></dl></section>'
            '</div></div>')
    return html(page("Accueil", "home", body))


@app.get("/activite")
def activity():
    body = ('<h1 class="h1">Activité récente</h1>'
            '<p class="lead mute">Fichiers ajoutés ou modifiés dans la bibliothèque Documents.</p>' +
            activity_items())
    return html(page("Activité récente", "activity", body))


@app.get("/aide")
def help_page():
    body = ('<h1 class="h1">Aide et assistance</h1>'
            '<div class="cols"><div>'
            '<section class="wp"><h2>Charte informatique (extrait)</h2><ul>'
            '<li>Les documents du partage sont internes. Ne les copiez pas sur un support personnel.</li>'
            '<li>Un compte est attribué à une personne ou à une équipe nommée ; ne le prêtez pas.</li>'
            '<li>Les accès sont journalisés et peuvent être contrôlés par la DSI.</li>'
            '<li>Signalez toute anomalie à l\'astreinte IT.</li></ul></section>'
            '<section class="wp"><h2>Navigateurs pris en charge</h2>'
            '<p>Microsoft Edge, Firefox ESR et Chrome (versions maintenues). Une résolution de 1280 x 1024 '
            'ou plus est conseillée.</p></section>'
            '</div><div>'
            '<section class="wp"><h2>Contacts</h2><dl class="kv">'
            '<dt>Astreinte IT</dt><dd>Poste 300 (24 h/24 pendant l\'événement)</dd>'
            '<dt>DSI</dt><dd>Poste 301</dd>'
            '<dt>Bureau de course</dt><dd>Poste 214</dd>'
            '<dt>Logistique</dt><dd>Poste 118</dd></dl>'
            '<p style="margin-top:10px"><a href="/annuaire">Voir l\'annuaire complet</a></p></section>'
            '</div></div>')
    return html(page("Aide", "help", body))


# --------------------------------------------------------------------------
# Directory (annuaire): static, no logins shown.
# --------------------------------------------------------------------------
PEOPLE = [
    ("Claire Dumont", "Directrice de course", "Direction de course", "201", "PC course"),
    ("Hugo Martin", "Adjoint à la direction de course", "Direction de course", "202", "PC course"),
    ("Bureau de course", "Accueil des concurrents", "Direction de course", "214", "Mairie, salle B"),
    ("Lars Eriksen", "Chef chronométreur", "Chronométrage", "230", "Cabine de chronométrage"),
    ("Jan Kowalski", "Opérateur chronométrage", "Chronométrage", "231", "Cabine de chronométrage"),
    ("Sophie Lambert", "Arbitre principale", "Arbitrage", "240", "Tente jury"),
    ("Karim Benali", "Juge arbitre", "Arbitrage", "241", "Tente jury"),
    ("Astreinte IT", "Support pendant l'événement", "DSI", "300", "PC course"),
    ("Nicolas Petit", "Responsable DSI", "DSI", "301", "Siège, bât. A"),
    ("Équipe IT d'urgence", "Cellule de crise", "DSI", "305", "PC course"),
    ("Mette Sorensen", "Administratrice SAP Basis", "Basis SAP", "310", "Siège, bât. A"),
    ("Thomas Girard", "Développeur ABAP", "Basis SAP", "311", "Siège, bât. A"),
    ("Logistique", "Standard logistique", "Logistique", "118", "Village"),
    ("Élodie Roux", "Responsable bénévoles", "Logistique", "119", "Village"),
    ("Service marketing", "Presse et partenariats", "Marketing", "120", "Siège, bât. C"),
    ("Camille Fontaine", "Chargée de communication", "Marketing", "121", "Siège, bât. C"),
    ("Julien Moreau", "Responsable partenariat triathlon", "Marketing", "130", "Siège, bât. C"),
]
SERVICES = sorted({p[2] for p in PEOPLE}, key=fold)


@app.get("/annuaire")
def directory():
    svc = request.args.get("service", "")
    if svc not in SERVICES:
        svc = ""
    rows = [p for p in PEOPLE if not svc or p[2] == svc]
    opts = '<option value="">Tous les services</option>' + "".join(
        f'<option{" selected" if s == svc else ""}>{esc(s)}</option>' for s in SERVICES)
    trs = "".join(
        f'<tr><td class="ty">{icon("user")}</td><td><b style="font-weight:600">{esc(n)}</b>'
        f'<span class="meta">{esc(fn)}, {esc(s)}, poste {esc(ph)}</span></td>'
        f'<td class="hide-sm">{esc(fn)}</td><td class="hide-sm">{esc(s)}</td>'
        f'<td class="num">{esc(ph)}</td><td class="hide-sm">{esc(b)}</td></tr>'
        for n, fn, s, ph, b in rows)
    body = ('<h1 class="h1">Annuaire</h1>'
            '<form class="views" method="get" action="/annuaire">'
            '<label for="svc">Service</label><select id="svc" name="service" class="in" '
            'style="width:auto;height:24px;padding:0 4px">' + opts + '</select>'
            '<button class="btn sec" type="submit" style="min-width:0;padding:2px 10px">Filtrer</button>'
            f'<span class="mute" style="margin-left:auto">{len(rows)} contact(s)</span></form>'
            '<table class="list"><thead><tr><th class="ty"></th><th>Nom</th><th class="hide-sm">Fonction</th>'
            '<th class="hide-sm">Service</th><th style="width:70px">Poste</th><th class="hide-sm">Bureau</th></tr>'
            '</thead><tbody>' + trs + '</tbody></table>'
            '<p class="mute" style="margin-top:10px;font-size:12px">Pour joindre un poste interne, composez le '
            'numéro à 3 chiffres depuis un téléphone du réseau staff.</p>')
    return html(page("Annuaire", "dir", body))


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
SORTS = {"nom": lambda f: fold(f["name"]), "date": lambda f: f["when"],
         "taille": lambda f: size_bytes(f) or 0}


def sort_args():
    tri = request.args.get("tri", "nom")
    ordre = request.args.get("ordre", "asc")
    if tri not in SORTS:
        tri = "nom"
    if ordre not in ("asc", "desc"):
        ordre = "asc"
    return tri, ordre


def qs(**kw):
    kw = {k: v for k, v in kw.items() if v}
    return ("?" + urlencode(kw)) if kw else ""


def sort_link(label, key, tri, ordre):
    if key == tri:
        nxt = "desc" if ordre == "asc" else "asc"
        arrow = " ↑" if ordre == "asc" else " ↓"
    else:
        nxt, arrow = "asc", ""
    href = qs(tri=None if key == "nom" and nxt == "asc" else key, ordre=None if nxt == "asc" else nxt)
    return f'<a href="{href or "?"}">{label}{arrow}</a>'


def folder_row(sub):
    cnt = len(sub["children"]) + len(sub["files"])
    last = latest(sub)
    when = fr_dt(last["when"]) if last else ""
    who = esc(last["who"]) if last else ""
    return (f'<tr><td class="ck"></td><td class="ty">{icon("folder")}</td>'
            f'<td><a href="{folder_href(sub["path"])}">{esc(sub["name"])}</a>'
            f'<span class="meta">{elements_label(cnt)}{", modifié le " + when if when else ""}</span></td>'
            f'<td class="c-date num">{when}</td><td class="c-who">{who}</td>'
            f'<td class="c-size">{elements_label(cnt)}</td><td class="c-ver"></td></tr>')


SEL = ' class="sel"'


def file_row(f, selected, tri, ordre):
    sel = f["name"] == selected
    size = file_size(f)
    sizecell = (f'<td class="c-size num">{size}</td>' if size is not None
                else '<td class="c-size na">pas encore disponible</td>')
    meta = (f'{size}, {esc(f["who"])}, le {fr_dt(f["when"], " à ")}' if size is not None
            else f'pas encore disponible, {esc(f["who"])}')
    href = qs(f=f["name"], tri=tri if tri != "nom" else None, ordre=ordre if ordre != "asc" else None)
    return (f'<tr{SEL if sel else ""}><td class="ck">{"✓" if sel else "○"}</td>'
            f'<td class="ty">{icon(f["kind"], f["type"])}</td>'
            f'<td><a href="{href}">{esc(f["name"])}</a>'
            f'<span class="meta">{meta}</span></td>'
            f'<td class="c-date num">{fr_dt(f["when"])}</td><td class="c-who">{esc(f["who"])}</td>'
            f'{sizecell}<td class="c-ver num">{esc(f["ver"])}</td></tr>')


def callout(f, row):
    avail = is_available(f)
    size = file_size(f) or "Non disponible"
    link = request.host_url.rstrip("/") + download_href(f)
    acts = (f'<a href="{download_href(f)}">Télécharger</a>' if avail
            else '<span class="off">Pas encore disponible</span>')
    meta = [("Type", esc(f["type"])), ("Taille", size), ("Version", esc(f["ver"]))]
    if f["desc"]:
        meta.append(("Description", esc(f["desc"])))
    meta.append(("Emplacement", esc("Documents / " + " / ".join(f["path"][:-1]))))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in meta)
    return (f'<aside class="callout" id="details" style="--row:{row}" aria-label="Détails du fichier">'
            f'<h2>{esc(f["name"])}</h2>'
            f'<p>Modifié le {fr_dt(f["when"], " à ")} par {esc(f["who"])}</p>'
            f'<dl>{dl}</dl><div class="link" title="{esc(link)}">{esc(link)}</div>'
            f'<div class="acts">{acts}</div></aside>')


@app.get("/documents")
def documents():
    rows = "".join(
        f'<tr><td class="ty">{icon("folder")}</td><td><a href="{folder_href(d["path"])}">{esc(d["name"])}</a>'
        f'<span class="meta">{esc(DEPT_DESC.get(d["name"], ""))}</span></td>'
        f'<td class="hide-sm">{esc(DEPT_DESC.get(d["name"], ""))}</td>'
        f'<td class="c-date num">{fr_dt(latest(d)["when"]) if latest(d) else ""}</td>'
        f'<td class="c-items">{elements_label(len(d["children"]) + len(d["files"]))}</td></tr>'
        for d in child_folders(TREE))
    body = ('<h1 class="h1">Documents</h1>'
            + views_bar() +
            '<table class="list"><thead><tr><th class="ty"></th><th>Nom</th><th class="hide-sm">Description</th>'
            '<th class="c-date">Modifié</th><th class="c-items">Contenu</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<div class="pager">Éléments 1 à {len(child_folders(TREE))}</div>')
    return html(page("Documents", "docs", body))


def views_bar():
    return ('<div class="views"><a href="/documents" aria-current="page">Tous les documents</a>'
            '<a href="/activite">Modifiés récemment</a>' +
            intranet.search_box("/recherche", "Rechercher un fichier", cls="find") + '</div>')


@app.get("/d/<path:subpath>")
def folder(subpath):
    segs = tuple(s for s in subpath.split("/") if s)
    node = get_node(segs)
    if node is None or node["path"] == ():
        abort(404)
    selected = request.args.get("f", "")
    tri, ordre = sort_args()
    files = sorted(node["files"], key=SORTS[tri], reverse=(ordre == "desc"))
    subs = child_folders(node)
    rows = [folder_row(s) for s in subs] + [file_row(f, selected, tri, ordre) for f in files]
    head_row = ('<tr><th class="ck">✓</th><th class="ty"></th>'
                f'<th>{sort_link("Nom", "nom", tri, ordre)}</th>'
                f'<th class="c-date">{sort_link("Modifié", "date", tri, ordre)}</th>'
                '<th class="c-who">Modifié par</th>'
                f'<th class="c-size">{sort_link("Taille du fichier", "taille", tri, ordre)}</th>'
                '<th class="c-ver">Version</th></tr>')
    table = ('<table class="list"><thead>' + head_row + '</thead><tbody>' + "".join(rows) +
             '</tbody></table>')
    if not rows:
        table = '<p class="empty">Ce dossier est vide.</p>'
    else:
        table += f'<div class="pager">Éléments 1 à {len(rows)}</div>'
    sel = next((f for f in files if f["name"] == selected), None)
    if sel is not None:
        work = ('<div class="work"><div style="min-width:0">' + table + '</div>' +
                callout(sel, len(subs) + files.index(sel)) + '</div>')
    else:
        work = table
    crumbs = ['<a href="/documents">Documents</a>']
    for i, s in enumerate(segs):
        crumbs.append(esc(s) if i == len(segs) - 1 else f'<a href="{folder_href(segs[:i + 1])}">{esc(s)}</a>')
    body = ('<h1 class="h1">' + '<span class="sep">›</span>'.join(crumbs) + '</h1>' + views_bar() + work)
    return html(page(node["name"], "docs", body, current_path=node["path"]))


@app.get("/recherche")
def search():
    q = request.args.get("q", "")[:100].strip()
    hits = []
    if q:
        needle = fold(q)
        for f in FILES:
            hay = fold(" ".join(f["path"]) + " " + f["desc"] + " " + f["type"])
            if needle in hay:
                hits.append(f)
        hits.sort(key=lambda f: f["when"], reverse=True)
    if not q:
        result = '<p class="empty">Saisissez un nom de fichier, de dossier ou un type de document.</p>'
    elif not hits:
        result = '<p class="empty">Aucun résultat. Vérifiez l\'orthographe ou essayez un autre terme.</p>'
    else:
        trs = "".join(
            f'<tr><td class="ty">{icon(f["kind"], f["type"])}</td>'
            f'<td><a href="{folder_href(f["path"][:-1])}?f={quote(f["name"])}">{esc(f["name"])}</a>'
            f'<span class="meta">{esc(" / ".join(f["path"][:-1]))}, le {fr_dt(f["when"], " à ")}</span></td>'
            f'<td class="hide-sm"><a href="{folder_href(f["path"][:-1])}">'
            f'{esc(" / ".join(f["path"][:-1]))}</a></td>'
            f'<td class="c-date num">{fr_dt(f["when"])}</td>'
            f'<td class="c-size num">{file_size(f) or ""}</td></tr>'
            for f in hits)
        result = ('<table class="list"><thead><tr><th class="ty"></th><th>Nom</th>'
                  '<th class="hide-sm">Emplacement</th><th class="c-date">Modifié</th>'
                  f'<th class="c-size">Taille</th></tr></thead><tbody>{trs}</tbody></table>')
    count = f'{len(hits)} résultat(s)' if q else ""
    body = ('<h1 class="h1">Recherche</h1>'
            '<form class="views" role="search" method="get" action="/recherche">'
            '<label class="sr" for="rq">Rechercher</label>'
            f'<input class="in" id="rq" name="q" value="{esc(q)}" placeholder="Rechercher dans Documents" '
            'style="max-width:360px;height:26px">'
            '<button class="btn" type="submit" style="min-width:0;padding:3px 14px">Rechercher</button>'
            f'<span class="mute" style="margin-left:auto">{count}</span></form>' + result)
    return html(page("Recherche", "docs", body))


@app.get("/telecharger/<path:filepath>")
def download(filepath):
    segs = tuple(s for s in filepath.split("/") if s)
    f = FILES_BY_PATH.get(segs)
    if f is None:
        abort(404)
    if f["decoy"]:
        return Response(f["text"], mimetype="text/plain; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="' + f["name"] + '"'})
    if not os.path.isfile(os.path.join(HANDOUT_DIR, f["source"])):
        abort(404)
    return send_from_directory(HANDOUT_DIR, f["source"], as_attachment=True)


@app.errorhandler(404)
def not_found(_e):
    if not session.get("ok"):
        return redirect("/login")
    body = ('<h1 class="h1">Désolé, cette page est introuvable.</h1>'
            '<p class="lead">Le dossier ou le fichier demandé n\'existe pas ou a été déplacé.</p>'
            '<p><a href="/documents">Retour à la bibliothèque Documents</a></p>'
            '<dl class="kv" style="margin-top:22px;color:var(--mute)">'
            f'<dt>ID de corrélation</dt><dd><code>{uuid.uuid4()}</code></dd>'
            f'<dt>Date et heure</dt><dd>{time.strftime("%d/%m/%Y %H:%M:%S")}</dd></dl>')
    return html(page("Introuvable", "docs", body), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
