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
from html import escape

from flask import Flask, Response, abort, redirect, request, send_from_directory

app = Flask(__name__)


TABS = [("/", "Missions"), ("/contexte", "Contexte"), ("/contacts", "Contacts")]

# Formula bar follows the clicked cell; "Statut" choices are kept in the
# player's own browser (localStorage), never sent anywhere.
SCRIPT = """<script>
(function(){
 var ref=document.getElementById('ref'),val=document.getElementById('val');
 document.querySelectorAll('.grid td[data-ref]').forEach(function(td){
  td.addEventListener('click',function(){
   document.querySelectorAll('.grid .sel').forEach(function(x){x.classList.remove('sel')});
   td.classList.add('sel');ref.textContent=td.dataset.ref;
   val.textContent=td.dataset.f||td.innerText.trim().replace(/\\s+/g,' ');
  });
 });
 var store=null;try{store=window.localStorage}catch(e){}
 document.querySelectorAll('select[data-k]').forEach(function(sel){
  var k='statut-'+sel.dataset.k;
  try{var v=store&&store.getItem(k);if(v)sel.value=v}catch(e){}
  var paint=function(){sel.closest('tr').dataset.statut=sel.value};paint();
  sel.addEventListener('change',function(){try{store&&store.setItem(k,sel.value)}catch(e){}paint()});
 });
})();
</script>"""


def layout(title, body, tab="/", cell="", formula="", note=""):
    here = ' aria-current="page"'
    tabs = "".join(f'<a href="{h}"{here if h == tab else ""}>{t}</a>' for h, t in TABS)
    score = (f'<a class="score" href="{escape(SCOREBOARD_URL)}">Tableau des scores ↗</a>'
             if SCOREBOARD_URL else "")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/crise.css"></head><body>
<header class="title"><span class="doc" aria-hidden="true"></span>
 <div><b>suivi_incident_finale_2026.ods</b> <span class="share">partagé avec l'équipe IT d'urgence</span></div>
 {score}</header>
<div class="menu" aria-hidden="true"><span>Fichier</span><span>Édition</span><span>Affichage</span><span>Insertion</span><span>Format</span><span>Outils</span></div>
{note}
<div class="fx"><span class="ref" id="ref">{cell}</span><span class="f">fx</span><span class="v" id="val">{formula}</span></div>
<main id="main" class="sheet">{body}</main>
<nav class="tabs" aria-label="Feuilles">{tabs}</nav>
{SCRIPT}</body></html>"""


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
LIVE_LABEL = {"site": ("Site DécaFlop", ":8001"), "idor": ("Espace athlètes", ":8004"),
              "sqli": ("Admin résultats", ":8006"), "sap": ("SAP DFlop ERP", ":8008")}
COLS = "ABCDEFGH"


def fr(text):
    """French typography: non-breaking spaces inside guillemets and before : ? !"""
    nb = "\u00a0"
    for a, b in (("« ", "«" + nb), (" »", nb + "»"), (" :", nb + ":"), (" ?", nb + "?"), (" !", nb + "!")):
        text = text.replace(a, b)
    return text


def grid(header, rows, extra="", cls=""):
    """A sheet: lettered columns, numbered rows, each cell knows its reference."""
    letters = "".join(f"<th>{COLS[i]}</th>" for i in range(len(header)))
    head = "".join(f'<td data-ref="{COLS[i]}1">{h}</td>' for i, h in enumerate(header))
    body = [f'<tr class="h"><th class="r">1</th>{head}</tr>']
    for n, (attrs, cells) in enumerate(rows, start=2):
        tds = "".join(f'<td data-ref="{COLS[i]}{n}"{c[1]}>{c[0]}</td>' for i, c in enumerate(cells))
        body.append(f'<tr{attrs}><th class="r">{n}</th>{tds}</tr>')
    return (f'<table class="grid {cls}"><thead><tr><th class="r"></th>{letters}</tr></thead>'
            f'<tbody>{"".join(body)}{extra}</tbody></table>')


def access(live, files):
    out = []
    if live:
        name, port = LIVE_LABEL[live]
        out.append(f'<a href="{escape(service_url(live))}">{name}</a> <span class="mute">({port})</span>')
    for name in files:
        info = file_info(name)
        if info:
            out.append(f'<a class="file" href="/fichiers/{name}" download>{name}</a> <span class="mute">· {info}</span>')
        else:
            out.append(f'<span class="file mute">{name}</span> <span class="mute">· pas encore disponible</span>')
    return "<br>".join(out)


@app.get("/")
def crisis_cell():
    total = sum(m[4] for m in MISSIONS)
    rows = []
    for num, title, cat, level, pts, brief, live, files in MISSIONS:
        status = (f'<select data-k="{num}" aria-label="Statut de la mission {num}">'
                  '<option>À faire</option><option>En cours</option><option>Résolu</option></select>')
        rows.append((f' class="mission" id="mission-{num}"', [
            (num, ""), (f'<span class="mn">{num}</span> <b>{fr(title)}</b>', ""), (fr(brief), ' class="desc"'), (cat, ""),
            (f'<span class="chip {LEVEL_CLASS[level]}">{level}</span>', ""), (str(pts), ' class="num"'),
            (access(live, files), ' class="acc"'), (status, "")]))
    n = len(rows) + 2
    total_row = (f'<tr class="tot"><th class="r">{n}</th><td data-ref="A{n}"></td><td data-ref="B{n}">Total</td>'
                 f'<td data-ref="C{n}"></td><td data-ref="D{n}"></td><td data-ref="E{n}"></td>'
                 f'<td data-ref="F{n}" class="num sel" data-f="=SOMME(F2:F{n-1})">{total}</td>'
                 f'<td data-ref="G{n}"></td><td data-ref="H{n}"></td></tr>')
    body = grid(["N°", "Mission", "Description", "Catégorie", "Niveau", "Points", "Accès / pièces jointes", "Statut"],
                rows, total_row, "frozen")
    note = (f'<p class="note"><b>Contexte :</b> la veille de la finale, la liste de départ a été truquée '
            f'en échangeant les puces de chronométrage. Suivez la piste jusqu\'au coupable. '
            f'<b>Flags :</b> <code>TRIATHLON{{...}}</code> · 9 missions, {total} points · '
            f'détails dans l\'onglet <a href="/contexte">Contexte</a>.</p>')
    return html(layout("Missions · suivi_incident_finale_2026", fr(body), "/", f"F{n}",
                       f"=SOMME(F2:F{n-1})", fr(note)))


@app.get("/contexte")
def context():
    score = (f'<a href="{escape(SCOREBOARD_URL)}">{escape(SCOREBOARD_URL)}</a>' if SCOREBOARD_URL
             else "fourni par l'organisation")
    rows = [("", [(k, ""), (v, ' class="desc"')]) for k, v in [
        ("Incident", "Liste de départ de la finale falsifiée"),
        ("Contexte", "La veille de la finale, quelqu'un s'est introduit dans les systèmes de l'événement "
                     "et a truqué la liste de départ en échangeant les puces de chronométrage. Vous êtes "
                     "l'équipe IT d'urgence : suivez la piste à travers le site DécaFlop, la cabine de "
                     "chronométrage, la clé USB d'un arbitre et le système SAP DFlop ERP. La dernière "
                     "mission désigne le coupable."),
        ("Format des flags", "<code>TRIATHLON{...}</code>"),
        ("Missions", f"9 missions, {sum(m[4] for m in MISSIONS)} points"),
        ("Ordre", "Conseillé dans l'ordre, mais chaque mission se joue seule"),
        ("Périmètre", "Uniquement les services et fichiers listés dans l'onglet Missions. Pas besoin d'internet."),
        ("Tableau des scores", score),
    ]]
    return html(layout("Contexte · suivi_incident_finale_2026", fr(grid(["Élément", "Valeur"], rows)),
                       "/contexte", "A1", "Élément"))


@app.get("/contacts")
def contacts():
    rows = [("", [(a, ""), (b, ""), (c, ' class="num"'), (d, ' class="desc"')]) for a, b, c, d in [
        ("Direction de course", "Bureau de course", "214", "Ouvre l'incident, valide les résultats"),
        ("Support IT", "Astreinte IT", "300", "Accès aux systèmes de l'événement"),
        ("Chronométrage", "Cabine de chronométrage", "231", "Wi-Fi staff, temps intermédiaires"),
        ("Arbitrage", "Jury de course", "240", "Clé USB retrouvée dans la cabine"),
        ("Basis SAP", "Équipe SAP DFlop", "410", "Exports et comptes SAP"),
        ("Marketing", "Communication DécaFlop", "120", "Affiche officielle"),
    ]]
    return html(layout("Contacts · suivi_incident_finale_2026",
                       fr(grid(["Rôle", "Contact", "Poste", "Remarque"], rows)), "/contacts", "A1", "Rôle"))


@app.get("/cellule-de-crise")
def old_path():
    return redirect("/")


@app.errorhandler(404)
def not_found(_e):
    body = ('<div class="empty"><b>Feuille introuvable</b><p>Cette page ou ce fichier n\'existe pas.</p>'
            '<p><a href="/">Retour à l\'onglet Missions</a></p></div>')
    return html(layout("Introuvable · suivi_incident_finale_2026", body, "", "", "#REF!"), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
