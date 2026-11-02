"""
"Cellule de crise": the players' entry point (its own container, not a
challenge). One page that briefs the emergency IT crew and lists every mission, with a link to each
live challenge and downloads for every handout.

- Handouts are read from HANDOUT_DIR (docker-compose mounts handouts/dist
  there, read-only). Only the whitelisted file names below can be downloaded.
- Links to the other live challenges reuse the host the player typed, with the
  default ports; override with IDOR_URL / SQLI_URL / SAP_URL if needed.
- SCOREBOARD_URL (optional) adds a "submit a flag" button.
- Nothing here mentions or links to the staff portal (challenge 01 itself).
"""
import os

from flask import Flask, Response, abort, redirect, request, send_from_directory

app = Flask(__name__)


def layout(title, body):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/crise.css"></head><body>
<header class="top"><div class="in">
 <a class="mark" href="/"><span class="dot" aria-hidden="true"></span>CELLULE DE CRISE</a>
 <span class="org">DécaFlop · usage interne · équipe IT d'urgence</span>
</div></header>
<main id="main">{body}</main>
<footer class="foot"><div class="in"><span>DécaFlop · usage interne</span>
<span>Finale 2026</span></div></footer></body></html>"""


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")

HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
SCOREBOARD_URL = os.environ.get("SCOREBOARD_URL", "").strip()

# mission files: name -> short label shown on the button
FILES = {
    "decaflop_poster.png": "Affiche (PNG)",
    "transition_shot.jpg": "Photo (JPG)",
    "timing_booth.pcap": "Capture réseau (PCAP)",
    "referee_usb.img": "Image de la clé (IMG)",
    "SAP_USR02_export.csv": "Export USR02 (CSV)",
    "sap_hint.txt": "Note SAP (TXT)",
    "wordlist.txt": "Liste de mots (TXT)",
    "case_file.zip": "Dossier chiffré (ZIP)",
}

# (number, title, category, level, points, brief, live service key or None, files)
MISSIONS = [
    ("01", "Le secret du sponsor", "Web", "Facile", 50,
     "DécaFlop jure que son site n'a rien à cacher. L'équipe parle pourtant d'un "
     "« espace interne » — et pour un truc interne, ils l'ont drôlement bien "
     "signalé aux moteurs de recherche.", "site", []),
    ("02", "Partagez partout", "Stégano", "Facile", 50,
     "Le marketing a diffusé une affiche pour la finale en demandant de la "
     "« partager partout ». Elle a l'air normale… mais elle est un peu lourde "
     "pour une simple affiche.", None, ["decaflop_poster.png"]),
    ("03", "En transition", "Forensics", "Facile", 75,
     "Une photo de l'appareil de l'équipe est apparue sur le PC de la cabine de "
     "chronométrage. Une photo de course comme une autre — mais un appareil se "
     "souvient de plus de choses qu'il n'en montre. Quand, où, et qui l'a prise ?",
     None, ["transition_shot.jpg"]),
    ("04", "Pas votre profil", "Web", "Moyen", 100,
     "L'espace athlètes permet à chacun de consulter son propre profil. Vous êtes "
     "connecté avec le dossard 1042. Le staff et les admins utilisent le même "
     "portail — et le profil admin garderait la trace de qui a touché aux listes "
     "de départ.", "idor", []),
    ("05", "La cabine de chronométrage", "Forensics", "Moyen", 100,
     "La cabine envoie les temps intermédiaires sur le Wi-Fi staff, et sa "
     "connexion passe encore en HTTP en clair. Nous avons capturé le trafic. "
     "Retrouvez ce que la cabine envoyait.", None, ["timing_booth.pcap"]),
    ("06", "Admin résultats", "Web", "Moyen", 125,
     "Les résultats officiels passent par l'admin résultats. « Réservé au staff "
     "autorisé », dit la page. Le formulaire de connexion a visiblement été écrit "
     "à la hâte la veille de la course.", "sqli", []),
    ("07", "La clé USB de l'arbitre", "Forensics", "Moyen", 125,
     "Un arbitre a oublié sa clé USB dans la cabine et jure avoir « tout supprimé ». "
     "Supprimer un fichier n'efface pas ses octets. Nous avons fait une image de "
     "la clé : récupérez ce qui a été effacé.", None, ["referee_usb.img"]),
    ("08", "SAP DFlop ERP", "SAP", "Difficile", 200,
     "DécaFlop gère tout dans SAP DFlop ERP — stocks, paie et, visiblement, les "
     "résultats officiels. L'écran de connexion est exposé sur le réseau de "
     "l'événement. Entrez.", "sap", []),
    ("09", "Qui a truqué la course ?", "SAP", "Difficile", 250,
     "La table des résultats ZRACE_RESULT a été modifiée la veille de la finale. "
     "Le système a conservé la table des utilisateurs USR02 : comptes, dernières "
     "connexions et anciens hachages de mots de passe. Prouvez qui a fait le coup.",
     None, ["SAP_USR02_export.csv", "sap_hint.txt", "wordlist.txt", "case_file.zip"]),
]

PORTS = {"site": ("SITE_URL", 8001), "idor": ("IDOR_URL", 8004), "sqli": ("SQLI_URL", 8006), "sap": ("SAP_URL", 8008)}


def service_url(key):
    """URL of a live challenge, on the same host the player used to reach us."""
    env, port = PORTS[key]
    if os.environ.get(env):
        return os.environ[env]
    host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
    return f"http://{host}:{port}/"


def file_info(name):
    path = os.path.join(HANDOUT_DIR, name)
    if not os.path.isfile(path):
        return None
    size = os.path.getsize(path)
    for unit in ("o", "Ko", "Mo"):
        if size < 1024 or unit == "Mo":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}".replace(".", ",")
        size /= 1024


@app.get("/fichiers/<name>")
def download(name):
    if name not in FILES or not file_info(name):
        abort(404)
    return send_from_directory(HANDOUT_DIR, name, as_attachment=True)


LEVEL_CLASS = {"Facile": "lv1", "Moyen": "lv2", "Difficile": "lv3"}
LIVE_LABEL = {"site": "Ouvrir le site DécaFlop", "idor": "Ouvrir l'espace athlètes",
              "sqli": "Ouvrir l'admin résultats", "sap": "Ouvrir SAP DFlop ERP"}


def mission_card(num, title, cat, level, pts, brief, live, files):
    from html import escape
    actions = []
    if live:
        actions.append(f'<a class="btn blue" href="{escape(service_url(live))}">{LIVE_LABEL[live]}</a>')
    for name in files:
        size = file_info(name)
        if size:
            actions.append(f'<a class="dl" href="/fichiers/{name}" download>'
                           f'<b>{FILES[name]}</b><span>{name} · {size}</span></a>')
        else:
            actions.append(f'<span class="dl off"><b>{FILES[name]}</b>'
                           f'<span>{name} · pas encore disponible</span></span>')
    return f"""<article class="mission" id="mission-{num}">
 <div class="mhead"><span class="mnum">{num}</span>
  <span class="tag cat">{cat}</span><span class="tag {LEVEL_CLASS[level]}">{level}</span>
  <span class="pts">{pts} pts</span></div>
 <h3 class="h">{title}</h3>
 <p>{brief}</p>
 <div class="mact">{"".join(actions)}</div>
</article>"""


@app.get("/")
def crisis_cell():
    total = sum(m[4] for m in MISSIONS)
    from html import escape
    score = (f'<a class="btn" href="{escape(SCOREBOARD_URL)}">Soumettre un flag</a>' if SCOREBOARD_URL
             else '<span class="small">Soumettez vos flags sur le tableau des scores de l\'organisation.</span>')
    body = f"""<section class="banner slim crisis"><div class="in">
 <div>
  <span class="tagline">Incident en cours · Finale 2026</span>
  <h1 class="h">Cellule <em>de crise</em></h1>
  <p>La veille de la finale, quelqu'un s'est introduit dans les systèmes de
     l'événement et a <b>truqué la liste de départ</b> en échangeant les puces de
     chronométrage. Vous êtes l'équipe IT d'urgence : suivez la piste à travers le
     site DécaFlop, la cabine de chronométrage, la clé USB d'un arbitre et le
     système <b>SAP DFlop ERP</b>. La dernière mission désigne le coupable.</p>
  {score}
 </div>
</div></section>
<section class="sec"><div class="in">
 <div class="rules">
  <div><b>Format des flags</b><code>TRIATHLON{{...}}</code></div>
  <div><b>Missions</b>9 missions · {total} points</div>
  <div><b>Ordre</b>Conseillé dans l'ordre, mais chaque mission se joue seule</div>
  <div><b>Périmètre</b>Uniquement les services et fichiers listés ici. Pas besoin d'internet.</div>
 </div>
 <div class="missions">{"".join(mission_card(*m) for m in MISSIONS)}</div>
</div></section>"""
    return html(layout("Cellule de crise · DécaFlop", body))


@app.get("/cellule-de-crise")
def old_path():
    return redirect("/")


@app.errorhandler(404)
def not_found(_e):
    return html(layout("Introuvable · Cellule de crise", """<div class="page"><div class="panel">
 <h1 class="h">Introuvable</h1><p class="mute">Cette page ou ce fichier n'existe pas.</p>
 <a class="btn blue" href="/">Retour à la cellule de crise</a></div></div>"""), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
