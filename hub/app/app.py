"""
"Cellule de crise": the players' entry point (its own container, not a
challenge). One page that briefs the emergency IT crew and lists every mission,
with a link to each live service.

- The hub itself serves NO handout files. The evidence files live on the
  internal share "Intranet DécaFlop" (:8020); the poster and race photo live on the
  DécaFlop site (:8001). Every mission is reached through a live service.
- Links to the live services reuse the host the player typed, with the default
  ports; override with <KEY>_URL (e.g. IDOR_URL, SHARE_URL) if needed.
- The crew login for the share is given in the Contexte sheet.
- Scoreboard (CTFd): CTFD_PORT links it on the player's host; SCOREBOARD_URL
  overrides the address. Teams submit flags there.
- ctfd_ids.json is still read from HANDOUT_DIR (written by ctfd-setup.py) for
  the "Soumettre le flag" deep links.
- Nothing here mentions or links to the staff portal (challenge 01 itself).
"""
import json
import os
from html import escape
from urllib.parse import quote

from flask import Flask, Response, redirect, request

app = Flask(__name__)


TABS = [("/", "Missions"), ("/contexte", "Contexte"), ("/outils", "Outils"), ("/contacts", "Contacts")]

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
    board = scoreboard_url()
    score = (f'<a class="score" href="{escape(board)}scoreboard">Tableau des scores ↗</a>' if board else "")
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
CTFD_PORT = os.environ.get("CTFD_PORT", "").strip()
# Browser toolbox on the Pi (for locked-down laptops): CyberChef + a web terminal.
CYBERCHEF_PORT = os.environ.get("CYBERCHEF_PORT", "").strip()
TERMINAL_PORT = os.environ.get("TERMINAL_PORT", "").strip()
CYBERCHEF_URL = os.environ.get("CYBERCHEF_URL", "").strip()
TERMINAL_URL = os.environ.get("TERMINAL_URL", "").strip()


def ctfd_ids():
    """{mission: {"id", "name"}} written by scripts/ctfd-setup.py next to the handouts."""
    try:
        with open(os.path.join(HANDOUT_DIR, "ctfd_ids.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: v for k, v in data.items()
                if isinstance(v, dict) and str(v.get("id", "")).isdigit() and isinstance(v.get("name"), str)}
    except (OSError, ValueError, AttributeError):
        return {}


def scoreboard_url():
    """CTFd's address: SCOREBOARD_URL if set, else the player's host on CTFD_PORT."""
    if SCOREBOARD_URL:
        return SCOREBOARD_URL.rstrip("/") + "/"
    if CTFD_PORT:
        host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
        return f"http://{host}:{CTFD_PORT}/"
    return ""

# The hub no longer serves any files: the poster/photo are on the DécaFlop site
# (:8001) and every evidence file is on the internal share "Intranet DécaFlop"
# (:8020). Each mission below is reached through a live service.

# (number, title, category, level, points, brief, live service key, files)
# 'files' is kept empty for every mission (no hub downloads); it stays in the
# tuple only so the row layout is unchanged.
MISSIONS = [
    ("01", "Le secret du sponsor", "Web", "Facile", 50,
     "DécaFlop jure que son site n'a rien à cacher. L'équipe parle pourtant d'un "
     "« espace interne » — et pour un truc interne, ils l'ont drôlement bien "
     "signalé aux moteurs de recherche.", "site", []),
    ("02", "Partagez partout", "Stégano", "Facile", 50,
     "Le marketing du sponsor a publié l'affiche officielle de la finale sur son "
     "site et demande de la « partager partout ». Elle a l'air normale… mais elle "
     "est un peu lourde pour une simple affiche.", "site", []),
    ("03", "En transition", "Forensics", "Facile", 75,
     "Le sponsor a mis en ligne sur son site une photo de la zone de transition, "
     "prise par son équipe. Une photo de course comme une autre — mais un appareil "
     "se souvient de plus de choses qu'il n'en montre. Quand, où, et qui l'a "
     "prise ?", "site", []),
    ("04", "Pas votre profil", "Web", "Moyen", 100,
     "L'espace athlètes permet à chacun de consulter son propre profil. Vous êtes "
     "connecté avec le dossard 1042. Le staff et les admins utilisent le même "
     "portail — et le profil admin garderait la trace de qui a touché aux listes "
     "de départ.", "idor", []),
    ("05", "La cabine de chronométrage", "Forensics", "Moyen", 100,
     "La cabine envoie les temps intermédiaires sur le Wi-Fi staff, et sa "
     "connexion passe encore en HTTP en clair. Nous avons capturé le trafic : "
     "la capture est dans le partage interne (Chronométrage / Captures). "
     "Retrouvez ce que la cabine envoyait.", "share", []),
    ("06", "Admin résultats", "Web", "Moyen", 125,
     "Les résultats officiels passent par l'admin résultats. « Réservé au staff "
     "autorisé », dit la page. Le formulaire de connexion a visiblement été écrit "
     "à la hâte la veille de la course.", "sqli", []),
    ("07", "La clé USB de l'arbitre", "Forensics", "Moyen", 125,
     "Un arbitre a oublié sa clé USB dans la cabine et jure avoir « tout supprimé ». "
     "Supprimer un fichier n'efface pas ses octets. Notre image de la clé est dans "
     "le partage interne (Arbitrage / Pièces) : récupérez ce qui a été effacé.",
     "share", []),
    ("09", "Qui a truqué la course ?", "SAP", "Difficile", 250,
     "La table des résultats ZRACE_RESULT a été modifiée la veille de la finale. "
     "Le système a conservé la table des utilisateurs USR02 : comptes, dernières "
     "connexions et anciens hachages de mots de passe. Tout est dans le partage "
     "interne : l'export et la note dans Basis SAP / Exports, la liste de mots dans "
     "IT / Outils, le dossier chiffré dans Direction de course / Dossier incident. "
     "Prouvez qui a fait le coup.", "share", []),
    # --- Audit complémentaire : failles trouvées après l'enquête ---
    ("10", "Identifiants forgés", "Web", "Difficile", 175,
     "L'API des résultats délivre un jeton de session et réserve les données "
     "officielles au rôle admin. À vous d'obtenir cet accès.", "jwt", []),
    ("11", "Supprimé, pas effacé", "Web", "Difficile", 150,
     "Le site de chronométrage a été mis en ligne un peu trop vite. Un jeton "
     "d'export a été retiré de la configuration « par sécurité » juste avant "
     "le déploiement. Retrouvez-le.", "git", []),
    ("12", "Imprimez le vôtre", "Web", "Difficile", 175,
     "Le générateur de certificats de finaliste reprend le nom que vous "
     "saisissez pour composer le document. Il est un peu trop littéral sur ce "
     "nom.", "ssti", []),
    ("13", "Enregistré par confort", "SAP", "Facile", 75,
     "Un raccourci SAP GUI (.sap) trouvé sur un portable de l'équipe a "
     "« enregistré le mot de passe » du DFlop ERP. Il est dans le partage interne "
     "(IT / Sauvegardes postes / portable-equipe-03). Récupérez-le.", "share", []),
    ("14", "Le gateway ouvert", "SAP", "Moyen", 150,
     "Le moniteur du gateway SAP DFlop est accessible depuis le réseau de "
     "l'événement, et personne n'a verrouillé qui peut s'y connecter. Voyez "
     "jusqu'où va cette exposition.", "sapgw", []),
    ("15", "En dur", "SAP", "Moyen", 150,
     "Un rapport ABAP, ZDFLOP_RESULT_EXPORT, pousse les résultats par RFC. "
     "Son jeton d'export n'est « pas censé » figurer dans le code. La source "
     "est dans le partage interne (Basis SAP / Développements) : lisez-la et "
     "jugez.", "share", []),
]

PORTS = {"site": ("SITE_URL", 8001), "share": ("SHARE_URL", 8020),
         "idor": ("IDOR_URL", 8004), "sqli": ("SQLI_URL", 8006),
         "jwt": ("JWT_URL", 8010), "git": ("GIT_URL", 8011), "ssti": ("SSTI_URL", 8012), "sapgw": ("SAPGW_URL", 8014)}


def service_url(key):
    """URL of a live challenge, on the same host the player used to reach us."""
    env, port = PORTS[key]
    if os.environ.get(env):
        return os.environ[env]
    host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
    return f"http://{host}:{port}/"


def tool_url(override, port):
    """A browser tool hosted on the player's own host (CyberChef :8090, terminal :8091)."""
    if override:
        return override.rstrip("/") + "/"
    if not port:
        return ""
    host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
    return f"http://{host}:{port}/"


LEVEL_CLASS = {"Facile": "lv1", "Moyen": "lv2", "Difficile": "lv3"}
LIVE_LABEL = {"site": ("Site DécaFlop", ":8001"), "share": ("Intranet DécaFlop", ":8020"),
              "idor": ("Espace athlètes", ":8004"), "sqli": ("Admin résultats", ":8006"),
              "jwt": ("Results API", ":8010"), "git": ("Site chronométrage", ":8011"),
              "ssti": ("Générateur de certificats", ":8012"), "sapgw": ("Gateway SAP", ":8014")}
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


def access(live):
    """Every mission is reached through a live service; the hub serves no files."""
    if not live:
        return ""
    name, port = LIVE_LABEL[live]
    return f'<a href="{escape(service_url(live))}">{name}</a> <span class="mute">({port})</span>'


@app.get("/")
def crisis_cell():
    total = sum(m[4] for m in MISSIONS)
    board = scoreboard_url()
    ids = ctfd_ids()
    rows = []
    for num, title, cat, level, pts, brief, live, _files in MISSIONS:
        submit = ""
        if board:
            target = f"{board}challenges"
            if num in ids:            # opens that challenge's popup in CTFd
                target += "#" + quote(f"{ids[num]['name']}-{ids[num]['id']}", safe="")
            submit = f'<a class="submit" href="{escape(target)}">Soumettre le flag ↗</a>'
        status = (f'<select data-k="{num}" aria-label="Statut de la mission {num}">'
                  '<option>À faire</option><option>En cours</option><option>Résolu</option></select>'
                  + submit)
        rows.append((f' class="mission" id="mission-{num}"', [
            (num, ""), (f'<span class="mn">{num}</span> <b>{fr(title)}</b>', ""), (fr(brief), ' class="desc"'), (cat, ""),
            (f'<span class="chip {LEVEL_CLASS[level]}">{level}</span>', ""), (str(pts), ' class="num"'),
            (access(live), ' class="acc"'), (status, "")]))
    n = len(rows) + 2
    total_row = (f'<tr class="tot"><th class="r">{n}</th><td data-ref="A{n}"></td><td data-ref="B{n}">Total</td>'
                 f'<td data-ref="C{n}"></td><td data-ref="D{n}"></td><td data-ref="E{n}"></td>'
                 f'<td data-ref="F{n}" class="num sel" data-f="=SOMME(F2:F{n-1})">{total}</td>'
                 f'<td data-ref="G{n}"></td><td data-ref="H{n}"></td></tr>')
    body = grid(["N°", "Mission", "Description", "Catégorie", "Niveau", "Points", "Accès", "Statut"],
                rows, total_row, "frozen")
    note = (f'<p class="note"><b>Contexte :</b> la veille de la finale, la liste de départ a été truquée '
            f'en échangeant les puces de chronométrage. Suivez la piste jusqu\'au coupable. '
            f'<b>Flags :</b> <code>TRIATHLON{{...}}</code> · {len(MISSIONS)} missions, {total} points'
            + (f' · à soumettre sur le <a href="{escape(board)}">tableau des scores</a>' if board else "")
            + ' · '
            f'détails dans l\'onglet <a href="/contexte">Contexte</a>.</p>')
    return html(layout("Missions · suivi_incident_finale_2026", fr(body), "/", f"F{n}",
                       f"=SOMME(F2:F{n-1})", fr(note)))


@app.get("/contexte")
def context():
    board = scoreboard_url()
    score = (f'<a href="{escape(board)}">{escape(board)}</a> (équipes, flags, indices et classement)' if board
             else "fourni par l'organisation")
    rows = [("", [(k, ""), (v, ' class="desc"')]) for k, v in [
        ("Incident", "Liste de départ de la finale falsifiée"),
        ("Contexte", "La veille de la finale, quelqu'un s'est introduit dans les systèmes de l'événement "
                     "et a truqué la liste de départ en échangeant les puces de chronométrage. Vous êtes "
                     "l'équipe IT d'urgence : suivez la piste à travers le site DécaFlop, la cabine de "
                     "chronométrage, la clé USB d'un arbitre et le système SAP DFlop ERP. La dernière "
                     "mission désigne le coupable."),
        ("Format des flags", "<code>TRIATHLON{...}</code>"),
        ("Missions", f"{len(MISSIONS)} missions, {sum(m[4] for m in MISSIONS)} points"),
        ("Ordre", "Conseillé dans l'ordre, mais chaque mission se joue seule"),
        ("Partage interne", "Les fichiers de preuve sont sur « Intranet DécaFlop », l'espace documentaire "
                            "interne (:8020). L'identifiant de connexion ne s'affiche plus : il se cache "
                            "dans les ressources du site DécaFlop — commencez par la mission 01."),
        ("Périmètre", "Uniquement les services listés dans l'onglet Missions. Pas besoin d'internet."),
        ("Outils", "Poste verrouillé ? Tout est accessible au navigateur — voir l'onglet "
                   "<a href=\"/outils\">Outils</a> (CyberChef et terminal d'équipe, hébergés sur le Pi)."),
        ("Tableau des scores", score),
    ]]
    return html(layout("Contexte · suivi_incident_finale_2026", fr(grid(["Élément", "Valeur"], rows)),
                       "/contexte", "A1", "Élément"))


@app.get("/outils")
def outils():
    cc = tool_url(CYBERCHEF_URL, CYBERCHEF_PORT)
    term = tool_url(TERMINAL_URL, TERMINAL_PORT)
    board = scoreboard_url()

    def addr(u):
        return ((f'<a href="{escape(u)}">{escape(u)}</a>', ' class="desc"') if u
                else ('<span class="mute">non configuré</span>', ' class="desc"'))

    rows = [("", [(name, ""), addr(u), (desc, ' class="desc"')]) for name, u, desc in [
        ("CyberChef", cc,
         "Base64, EXIF, dézip (même protégé), carving de fichiers, MD5, décodage et "
         "signature de JWT — tout dans le navigateur, rien à installer."),
        ("Terminal d'équipe", term,
         "Un shell Linux dans le navigateur : git-dumper, john, binwalk, foremost, "
         "exiftool, curl, python3. Chaque connexion a son propre espace de travail."),
        ("Tableau des scores", board,
         "CTFd : équipes, soumission des flags, indices et classement."),
    ]]
    note = ('<p class="note"><b>Poste verrouillé ?</b> Pas besoin d\'installer quoi que ce '
            'soit : un simple navigateur suffit. CyberChef couvre la plupart des épreuves ; '
            'le terminal d\'équipe sert de filet pour le reste (surtout récupérer un dépôt '
            '<code>.git</code>). Tout tourne sur le Pi, hors ligne.</p>')
    return html(layout("Outils · suivi_incident_finale_2026",
                       fr(grid(["Outil", "Adresse", "À quoi ça sert"], rows)),
                       "/outils", "A1", "Outil", fr(note)))


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
