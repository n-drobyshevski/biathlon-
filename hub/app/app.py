"""
"Cellule de crise": the players' entry point (its own container, not a
challenge). One page that briefs the emergency IT crew and lists every mission,
with a link to each live service.

- The hub itself serves NO handout files. The evidence files live on the
  internal share "Partage DFlop" (:8020); the poster and race photo live on the
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
 document.querySelectorAll('.grid td[data-ref],.tile[data-ref]').forEach(function(td){
  td.addEventListener('click',function(e){
   if(e.target.closest('a,button'))return;
   document.querySelectorAll('.grid .sel,.tile.sel').forEach(function(x){x.classList.remove('sel')});
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


# Marks a link that opens another tool in a new tab (instead of an arrow character).
EXT = ('<svg class="ext" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">'
       '<path d="M6 3H3v10h10v-3M9 2.5h4.5V7M13.5 2.5 7.5 8.5" fill="none" stroke="currentColor" '
       'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>')
NEW_TAB = ' target="_blank" rel="noopener"'
DOC = "suivi_incident_finale_2026.ods"


def layout(title, body, tab="/", cell="", formula="", note="", scripts=""):
    here = ' aria-current="page"'
    tabs = "".join(f'<a href="{h}"{here if h == tab else ""}>{t}</a>' for h, t in TABS)
    board = scoreboard_url()
    score = (f'<a class="score" href="{escape(board)}scoreboard"{NEW_TAB}>Tableau des scores {EXT}</a>'
             if board else "")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{DOC} - {title}</title><link rel="stylesheet" href="/static/crise.css"></head><body>
<header class="title"><span class="doc" aria-hidden="true"></span>
 <div><b>{DOC}</b> <span class="share">partagé avec l'équipe IT d'urgence</span></div>
 {score}</header>
<div class="menu" aria-hidden="true"><span>Fichier</span><span>Édition</span><span>Affichage</span><span>Insertion</span><span>Format</span><span>Outils</span></div>
{note}
<div class="fx"><span class="ref" id="ref">{cell}</span><span class="f">fx</span><span class="v" id="val">{formula}</span></div>
<main id="main" class="sheet">{body}</main>
<nav class="tabs" aria-label="Feuilles">{tabs}</nav>
{SCRIPT}{scripts}</body></html>"""


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
# (:8001) and every evidence file is on the internal share "Partage DFlop"
# (:8020). Each mission below is reached through a live service.

# (number, title, category, level, points, brief, live service key, files)
# 'files' is kept empty for every mission (no hub downloads); it stays in the
# tuple only so the row layout is unchanged.
MISSIONS = [
    ("01", "Le secret du sponsor", "Web", "Facile", 50,
     "DécaFlop jure que son site n'a rien à cacher. L'équipe parle pourtant d'un "
     "« espace interne ». Pour un truc interne, ils l'ont drôlement bien "
     "signalé aux moteurs de recherche.", "site", []),
    ("02", "Partagez partout", "Stégano", "Facile", 50,
     "Le marketing du sponsor a publié l'affiche officielle de la finale sur son "
     "site et demande de la « partager partout ». Elle a l'air normale, mais elle "
     "est un peu lourde pour une simple affiche.", "site", []),
    ("03", "En transition", "Forensics", "Facile", 75,
     "Le sponsor a mis en ligne sur son site une photo de la zone de transition, "
     "prise par son équipe. Une photo de course comme une autre, mais un appareil "
     "se souvient de plus de choses qu'il n'en montre. Quand, où, et qui l'a "
     "prise ?", "site", []),
    ("04", "Pas votre profil", "Web", "Moyen", 100,
     "L'espace athlètes permet à chacun de consulter son propre profil. Vous êtes "
     "connecté avec le dossard 1042. Le staff et les admins utilisent le même "
     "portail, et le profil admin garderait la trace de qui a touché aux listes "
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
LIVE_LABEL = {"site": ("Site DécaFlop", ":8001"), "share": ("Partage DFlop", ":8020"),
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


def grid(header, rows, extra="", cls="", start=1):
    """A sheet: lettered columns, numbered rows, each cell knows its reference."""
    letters = "".join(f"<th>{COLS[i]}</th>" for i in range(len(header)))
    head = "".join(f'<td data-ref="{COLS[i]}{start}">{h}</td>' for i, h in enumerate(header))
    body = [f'<tr class="h"><th class="r">{start}</th>{head}</tr>']
    for n, (attrs, cells) in enumerate(rows, start=start + 1):
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
            submit = f'<a class="submit" href="{escape(target)}"{NEW_TAB}>Soumettre le flag {EXT}</a>'
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
    where = (f' et se soumettent sur le <a href="{escape(board)}"{NEW_TAB}>tableau des scores</a>'
             if board else "")
    note = (f'<p class="note">La veille de la finale, la liste de départ a été truquée en échangeant les '
            f'puces de chronométrage. Suivez la piste jusqu\'au coupable. {len(MISSIONS)} missions, '
            f'{total} points. Les flags ont la forme <code>TRIATHLON{{...}}</code>{where}. '
            f'Détails dans l\'onglet <a href="/contexte">Contexte</a>.</p>')
    return html(layout("Missions", fr(body), "/", f"F{n}",
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
        ("Partage interne", "Les fichiers de preuve sont sur « Partage DFlop », l'espace documentaire "
                            "interne (:8020). L'identifiant de connexion est affiché sur le portail "
                            "staff du site DécaFlop (mission 01)."),
        ("Périmètre", "Uniquement les services listés dans l'onglet Missions. Pas besoin d'internet."),
        ("Outils", "Un navigateur suffit, même sur un poste verrouillé. CyberChef et le terminal "
                   "d'équipe tournent sur le Pi, dans l'onglet <a href=\"/outils\">Outils</a>."),
        ("Tableau des scores", score),
    ]]
    return html(layout("Contexte", fr(grid(["Élément", "Valeur"], rows)),
                       "/contexte", "A1", "Élément"))


# Launcher tiles on the Outils sheet. Each tool says what it can do in general and
# never which mission it helps with (no spoilers, same rule as the briefs).
TOOL_ICONS = {
    "chef": '<path d="M7 14.5c-2.2 0-3.5-1.6-3.5-3.4 0-1.9 1.5-3.3 3.3-3.3.5-2.2 2.6-3.8 5.2-3.8s4.7 1.6 '
            '5.2 3.8c1.8 0 3.3 1.4 3.3 3.3 0 1.8-1.3 3.4-3.5 3.4V19H7z" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linejoin="round"/><path d="M7 16.5h10" stroke="currentColor" stroke-width="1.7"/>',
    "term": '<rect x="3" y="4.5" width="18" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
            '<path d="M7 9.5l3 2.5-3 2.5M12 15h5" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round"/>',
    "board": '<path d="M4 20V13h4.5v7M9.75 20V8h4.5v12M15.5 20v-9.5H20V20" fill="none" stroke="currentColor" '
             'stroke-width="1.7" stroke-linejoin="round"/><path d="M3 20h18" stroke="currentColor" stroke-width="1.7"/>',
}


def tools():
    return [
        {"name": "CyberChef", "icon": "chef", "url": tool_url(CYBERCHEF_URL, CYBERCHEF_PORT),
         "purpose": "Décoder, convertir et analyser des fichiers, directement dans le navigateur.",
         "chips": ["Base64", "EXIF", "Dézip, même protégé", "Extraction de fichiers", "MD5", "JWT"]},
        {"name": "Terminal d'équipe", "icon": "term", "url": tool_url(TERMINAL_URL, TERMINAL_PORT),
         "purpose": "Un shell Linux dans le navigateur, avec les outils de l'équipe déjà installés.",
         "chips": ["git-dumper", "john", "binwalk", "foremost", "exiftool", "curl", "python3"]},
        {"name": "Tableau des scores", "icon": "board", "url": scoreboard_url(),
         "purpose": "Créez ou rejoignez votre équipe, soumettez les flags et suivez le classement.",
         "chips": ["Équipes", "Flags", "Indices", "Classement"]},
    ]


def tile(n, t):
    icon = f'<span class="ti"><svg viewBox="0 0 24 24" aria-hidden="true">{TOOL_ICONS[t["icon"]]}</svg></span>'
    chips = "".join(f'<span class="tag">{escape(c)}</span>' for c in t["chips"])
    url = t["url"]
    if url:
        state = f'<span class="st wait" data-check="{escape(url)}">Vérification</span>'
        shown = url.split("://", 1)[-1].rstrip("/")
        foot = (f'<span class="addr"><span>{escape(shown)}</span>'
                f'<button type="button" data-copy="{escape(url)}">Copier</button></span>'
                f'<a class="open" href="{escape(url)}"{NEW_TAB}>Ouvrir {EXT}</a>')
        formula = f'{t["name"]}, {url}'
    else:
        state = '<span class="st off">Non configuré</span>'
        foot = ('<span class="addr none">Adresse non définie</span>'
                '<span class="open off" aria-disabled="true">Ouvrir</span>')
        formula = f'{t["name"]}, non configuré'
    sel = " sel" if n == 1 else ""
    return (f'<article class="tile{sel}" data-ref="Objet {n}" data-f="{escape(formula)}">'
            f'<div class="top">{icon}<h2>{escape(t["name"])}</h2>{state}</div>'
            f'<p>{escape(t["purpose"])}</p><div class="tags">{chips}</div>'
            f'<div class="ft">{foot}</div></article>')


# Tool state is checked from the player's browser (the hub never calls the tools):
# an opaque no-cors answer means the tool is up. Copier falls back to execCommand
# because the Pi serves plain HTTP, where navigator.clipboard is unavailable.
TOOLS_JS = """<script>
(function(){
 document.querySelectorAll('[data-check]').forEach(function(el){
  var ctl=window.AbortController?new AbortController():null;
  var t=setTimeout(function(){ctl&&ctl.abort()},3000);
  var set=function(ok){clearTimeout(t);el.classList.remove('wait');el.classList.add(ok?'ok':'bad');
   el.textContent=ok?'En ligne':'Injoignable'};
  fetch(el.dataset.check,{mode:'no-cors',cache:'no-store',signal:ctl?ctl.signal:undefined})
   .then(function(){set(true)},function(){set(false)});
 });
 document.querySelectorAll('button[data-copy]').forEach(function(b){
  b.addEventListener('click',function(){
   var v=b.dataset.copy;
   function ok(){b.textContent='Copié';setTimeout(function(){b.textContent='Copier'},1500)}
   function legacy(){var a=document.createElement('textarea');a.value=v;a.style.position='fixed';
    a.style.opacity='0';document.body.appendChild(a);a.select();
    try{document.execCommand('copy');ok()}catch(e){}a.remove()}
   if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(v).then(ok,legacy)}
   else{legacy()}
  });
 });
})();
</script>"""


@app.get("/outils")
def outils():
    ts = tools()
    tiles = "".join(tile(n, t) for n, t in enumerate(ts, 1))
    share = (f'<a href="{escape(service_url("share"))}">Partage DFlop</a> '
             '<span class="mute">(:8020)</span>')
    rows = [("", [(k, ' class="k"'), (v, ' class="desc"')]) for k, v in [
        ("Hors ligne", "Tout tourne sur le Pi de l'événement. Pas besoin d'internet."),
        ("Rien à installer", "Un navigateur suffit, même sur un poste verrouillé."),
        ("Fichiers de preuve", f"Ils sont sur {share}. Glissez un fichier téléchargé dans la zone "
                               "Input de CyberChef pour l'analyser."),
        ("Espace de travail", "Le terminal donne à chaque connexion son propre dossier, sur le Pi. "
                              "Il ne voit pas les fichiers de votre ordinateur."),
    ]]
    know = grid(["Bon à savoir", ""], rows, start=8)
    body = f'<div class="canvas"><div class="tiles">{tiles}</div><div class="know">{know}</div></div>'
    first = ts[0]
    formula = f'{first["name"]}, {first["url"]}' if first["url"] else f'{first["name"]}, non configuré'
    return html(layout("Outils", fr(body), "/outils", "Objet 1", formula, scripts=TOOLS_JS))


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
    return html(layout("Contacts",
                       fr(grid(["Rôle", "Contact", "Poste", "Remarque"], rows)), "/contacts", "A1", "Rôle"))


@app.get("/cellule-de-crise")
def old_path():
    return redirect("/")


@app.errorhandler(404)
def not_found(_e):
    body = ('<div class="empty"><b>Feuille introuvable</b><p>Cette page ou ce fichier n\'existe pas.</p>'
            '<p><a href="/">Retour à l\'onglet Missions</a></p></div>')
    return html(layout("Introuvable", body, "", "", "#REF!"), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
