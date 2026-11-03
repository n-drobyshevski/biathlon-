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
import hashlib
import hmac
import json
import os
from html import escape
from urllib.parse import quote

from flask import Flask, Response, redirect, request

app = Flask(__name__)


TABS = [("/", "Missions"), ("/contexte", "Contexte"), ("/outils", "Outils"),
        ("/guide", "Mode guidé"), ("/contacts", "Contacts")]

# Shared page script. The formula bar follows the clicked cell. Mission statuses
# and the guide steps a player has revealed stay in that player's browser
# (localStorage), shared between tabs and never sent anywhere. Copier falls back
# to execCommand because the Pi serves plain HTTP, where navigator.clipboard is off.
SCRIPT = r"""<script>
(function(){
 var ref=document.getElementById('ref'),val=document.getElementById('val');
 window.hubFx=function(r,v){if(ref)ref.textContent=r;if(val)val.textContent=v};
 document.querySelectorAll('.grid td[data-ref],.tile[data-ref]').forEach(function(td){
  td.addEventListener('click',function(e){
   if(e.target.closest('a,button,select'))return;
   document.querySelectorAll('.grid .sel,.tile.sel').forEach(function(x){x.classList.remove('sel')});
   td.classList.add('sel');hubFx(td.dataset.ref,td.dataset.f||td.innerText.trim().replace(/\s+/g,' '));
  });
 });
 var store=null;try{store=window.localStorage}catch(e){}
 function get(k){try{return store?store.getItem(k):null}catch(e){return null}}
 function put(k,v){try{if(store)store.setItem(k,v)}catch(e){}}
 function paint(k){
  var v=get('statut-'+k)||'À faire';
  document.querySelectorAll('select[data-k="'+k+'"]').forEach(function(s){s.value=v});
  document.querySelectorAll('[data-m="'+k+'"]').forEach(function(el){el.dataset.statut=v});
  document.querySelectorAll('[data-m="'+k+'"] .stl').forEach(function(el){el.textContent=v});
 }
 function progress(){
  var p=document.querySelector('.prog');if(!p)return;
  var n=0,pts=0;
  document.querySelectorAll('tr[data-pts]').forEach(function(tr){
   if(tr.dataset.statut==='Résolu'){n++;pts+=+tr.dataset.pts}});
  p.querySelector('.pn').textContent=n;p.querySelector('.pp').textContent=pts;
  p.querySelector('.bar i').style.width=Math.round(pts/(+p.dataset.total||1)*100)+'%';
 }
 var keys={};document.querySelectorAll('select[data-k]').forEach(function(s){keys[s.dataset.k]=1});
 Object.keys(keys).forEach(paint);progress();
 document.addEventListener('change',function(e){var s=e.target.closest('select[data-k]');if(!s)return;
  put('statut-'+s.dataset.k,s.value);paint(s.dataset.k);progress()});
 function steps(box){
  var k=box.dataset.g,li=box.querySelectorAll('.step'),n=li.length;
  var shown=Math.min(Math.max(parseInt(get('guide-'+k),10)||1,1),n);
  li.forEach(function(x,i){x.classList.toggle('hidden',i>=shown)});
  var c=box.querySelector('.gcount');if(c)c.textContent='Étape '+shown+' sur '+n;
  box.querySelectorAll('[data-go="next"],[data-go="all"]').forEach(function(b){b.hidden=shown>=n});
  var r=box.querySelector('[data-go="reset"]');if(r)r.hidden=shown<2;
  document.querySelectorAll('[data-gp="'+k+'"]').forEach(function(x){x.textContent=shown+'/'+n});
  return {k:k,shown:shown,n:n};
 }
 function allSteps(){document.querySelectorAll('[data-g]').forEach(steps)}
 allSteps();
 function copy(b){var v=b.dataset.copy,icon=b.classList.contains('cpy');
  function ok(){if(icon){b.classList.add('done');setTimeout(function(){b.classList.remove('done')},1500)}
   else{b.textContent='Copié';setTimeout(function(){b.textContent='Copier'},1500)}}
  function legacy(){var a=document.createElement('textarea');a.value=v;a.style.position='fixed';
   a.style.opacity='0';document.body.appendChild(a);a.select();
   try{document.execCommand('copy');ok()}catch(e){}a.remove()}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(v).then(ok,legacy)}
  else{legacy()}}
 document.addEventListener('click',function(e){
  var b=e.target.closest('[data-g] [data-go]');
  if(b){var s=steps(b.closest('[data-g]'));
   var next=b.dataset.go==='next'?s.shown+1:b.dataset.go==='all'?s.n:1;
   put('guide-'+s.k,String(next));
   document.querySelectorAll('[data-g="'+s.k+'"]').forEach(steps);return}
  var c=e.target.closest('button[data-copy]');if(c)copy(c);
 });
 window.addEventListener('storage',function(e){if(!e.key)return;
  if(e.key.indexOf('statut-')===0){paint(e.key.slice(7));progress()}
  if(e.key.indexOf('guide-')===0)allSteps()});
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
<title>{DOC} - {title}</title><link rel="stylesheet" href="/static/crise.css"></head><body><script>document.documentElement.className+=' js'</script>
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

# Optional beginner walkthrough ("Mode guidé"), gated by a simple password the
# organizer hands out. Unlock is remembered by a cookie whose value is a token
# derived from the password (so a bogus cookie does not unlock it). The repo is
# public, so this is a spoiler gate for first-timers, not a security boundary.
GUIDE_PASSWORD = os.environ.get("GUIDE_PASSWORD", "debutant").strip()
GUIDE_TOKEN = hashlib.sha256(("decaflop-guide:" + GUIDE_PASSWORD).encode()).hexdigest()


def guide_unlocked():
    tok = request.cookies.get("guide", "")
    return bool(tok) and hmac.compare_digest(tok, GUIDE_TOKEN)


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


SECTIONS = [("Enquête principale", "missions 01 à 09", lambda num: int(num) < 10),
            ("Audit complémentaire", "missions 10 à 15", lambda num: int(num) >= 10)]
STATUSES = ("À faire", "En cours", "Résolu")


def section_of(num):
    return next(sec for sec in SECTIONS if sec[2](num))


def submit_link(num, board, ids):
    """CTFd link that opens this mission's challenge (or the challenge list)."""
    if not board:
        return ""
    target = f"{board}challenges"
    if num in ids:
        target += "#" + quote(f"{ids[num]['name']}-{ids[num]['id']}", safe="")
    return f'<a class="submit" href="{escape(target)}"{NEW_TAB}>Soumettre le flag {EXT}</a>'


def status_select(num):
    opts = "".join(f"<option>{st}</option>" for st in STATUSES)
    return f'<select data-k="{num}" aria-label="Statut de la mission {num}">{opts}</select>'


def open_button(live):
    name, port = LIVE_LABEL[live]
    return (f'<a class="open" href="{escape(service_url(live))}"{NEW_TAB}>Ouvrir {EXT}</a>'
            f'<span class="svc">{name} <span class="mute">({port})</span></span>')


def mission_panel(m, board, ids, unlocked):
    """Details of one mission (brief, access, status). The guide steps are added only
    when the player unlocked the Mode guidé, so the page never spoils by default."""
    num, title, cat, level, pts, brief, live, _files = m
    if unlocked and num in GUIDE:
        extra = f'<div class="mp-guide"><h3>Mode guidé</h3>{guide_block(num)}</div>'
    else:
        extra = ('<p class="mp-lock">Besoin d\'un coup de pouce ? Le <a href="/guide">Mode guidé</a> '
                 'explique chaque mission pas à pas. Demandez son mot de passe à l\'organisation.</p>')
    return (f'<section class="mpanel" id="detail-{num}" data-m="{num}" aria-label="Mission {num}">'
            f'<div class="mp-hd"><span class="mp-no">Mission {num}, {section_of(num)[0].lower()}</span>'
            f'<h2>{escape(title)}</h2><div class="mp-tags"><span class="chip cat">{escape(cat)}</span>'
            f'<span class="chip {LEVEL_CLASS[level]}">{level}</span><span class="pts">{pts} points</span></div></div>'
            f'<div class="mp-bd"><p class="brief">{brief}</p>'
            f'<div class="mp-sec"><h3>Accès</h3><div class="mp-row">{open_button(live)}</div></div>'
            f'<div class="mp-sec"><h3>Statut</h3><div class="mp-row">{status_select(num)}'
            f'{submit_link(num, board, ids)}</div></div>{extra}</div></section>')


# Missions sheet: one mission is selected at a time and its panel shows beside the
# list (under its row on narrow screens). The hash keeps the #mission-NN form that
# CTFd links to.
MISSIONS_JS = r"""<script>
(function(){
 var split=document.querySelector('.split');if(!split)return;
 var side=split.querySelector('.mpanels'),narrow=window.matchMedia('(max-width:900px)');
 var rows=[].slice.call(split.querySelectorAll('tr[data-m]')),cur=null;
 function place(){
  var old=split.querySelector('tr.exp');
  if(old){[].slice.call(old.querySelectorAll('.mpanel')).forEach(function(x){side.appendChild(x)});old.remove()}
  if(!narrow.matches||!cur)return;
  var tr=document.getElementById('mission-'+cur),row=document.createElement('tr'),td=document.createElement('td');
  row.className='exp';td.colSpan=8;row.appendChild(td);td.appendChild(document.getElementById('detail-'+cur));
  tr.parentNode.insertBefore(row,tr.nextSibling);
 }
 function select(k,push){
  var tr=document.getElementById('mission-'+k);if(!tr)return;
  cur=k;
  rows.forEach(function(r){r.classList.toggle('pick',r===tr)});
  split.querySelectorAll('.mpanel').forEach(function(x){x.classList.toggle('on',x.id==='detail-'+k)});
  if(window.hubFx)hubFx('B'+tr.dataset.r,tr.dataset.t);
  if(push&&history.replaceState)history.replaceState(null,'','#mission-'+k);
  place();
 }
 function fromHash(){var m=/^#(?:mission|detail)-(\d\d)$/.exec(location.hash);return m&&m[1]}
 var first=fromHash();
 if(!first){var open=rows.filter(function(r){return r.dataset.statut!=='Résolu'})[0]||rows[0];first=open&&open.dataset.m}
 if(first)select(first,false);
 split.addEventListener('click',function(e){
  if(e.target.closest('.mpanel'))return;
  var a=e.target.closest('a.pick'),tr=e.target.closest('tr[data-m]');
  if(!a&&e.target.closest('a,button,select'))return;
  if(!tr)return;if(a)e.preventDefault();
  if(narrow.matches&&tr.dataset.m===cur){cur=null;rows.forEach(function(r){r.classList.remove('pick')});place();return}
  select(tr.dataset.m,true);
 });
 split.addEventListener('keydown',function(e){
  var a=e.target.closest('a.pick');if(!a||(e.key!=='ArrowDown'&&e.key!=='ArrowUp'))return;
  var i=rows.indexOf(a.closest('tr'))+(e.key==='ArrowDown'?1:-1);
  if(i<0||i>=rows.length)return;e.preventDefault();select(rows[i].dataset.m,true);rows[i].querySelector('a.pick').focus();
 });
 window.addEventListener('hashchange',function(){var k=fromHash();if(k)select(k,false)});
 if(narrow.addEventListener)narrow.addEventListener('change',place);else if(narrow.addListener)narrow.addListener(place);
})();
</script>"""


@app.get("/")
def crisis_cell():
    total = sum(m[4] for m in MISSIONS)
    board = scoreboard_url()
    ids = ctfd_ids()
    unlocked = guide_unlocked()
    heads = ["N°", "Mission", "Catégorie", "Niveau", "Points", "Accès", "Statut"]
    letters = "".join(f"<th>{COLS[i]}</th>" for i in range(len(heads)))
    body = ['<tr class="h"><th class="r">1</th>' +
            "".join(f'<td data-ref="{COLS[i]}1">{h}</td>' for i, h in enumerate(heads)) + "</tr>"]
    panels, r = [], 1
    for sec, span, test in SECTIONS:
        ms = [m for m in MISSIONS if test(m[0])]
        r += 1
        body.append(f'<tr class="secr"><th class="r">{r}</th><td colspan="{len(heads)}" data-ref="A{r}">'
                    f'{sec}<span>{span}, {sum(m[4] for m in ms)} points</span></td></tr>')
        for m in ms:
            num, title, cat, level, pts, _brief, live, _files = m
            r += 1
            body.append(
                f'<tr class="mission" id="mission-{num}" data-m="{num}" data-pts="{pts}" data-r="{r}" '
                f'data-t="{escape(title)}"><th class="r">{r}</th><td data-ref="A{r}">{num}</td>'
                f'<td data-ref="B{r}" class="mi"><a class="pick" href="#detail-{num}">{escape(title)}</a></td>'
                f'<td data-ref="C{r}">{escape(cat)}</td>'
                f'<td data-ref="D{r}"><span class="chip {LEVEL_CLASS[level]}">{level}</span></td>'
                f'<td data-ref="E{r}" class="num">{pts}</td>'
                f'<td data-ref="F{r}" class="acc">{access(live)}</td>'
                f'<td data-ref="G{r}" class="stc"><span class="dot"></span><span class="stl">À faire</span></td></tr>')
            panels.append(mission_panel(m, board, ids, unlocked))
    n = r + 1
    body.append(f'<tr class="tot"><th class="r">{n}</th><td data-ref="A{n}"></td><td data-ref="B{n}">Total</td>'
                f'<td data-ref="C{n}"></td><td data-ref="D{n}"></td>'
                f'<td data-ref="E{n}" class="num sel" data-f="=SOMME(E3:E{r})">{total}</td>'
                f'<td data-ref="F{n}"></td><td data-ref="G{n}"></td></tr>')
    prog = (f'<div class="prog" data-total="{total}"><span><b class="pn">0</b> sur {len(MISSIONS)} résolues</span>'
            '<span class="bar" aria-hidden="true"><i></i></span>'
            f'<span><b class="pp">0</b> sur {total} points</span>'
            '<span class="mute pnote">Suivi enregistré dans ce navigateur</span></div>')
    table = (f'<table class="grid mlist"><thead><tr><th class="r"></th>{letters}</tr></thead>'
             f'<tbody>{"".join(body)}</tbody></table>')
    page_body = (f'{prog}<div class="split"><div class="mwrap">{table}</div>'
                 f'<div class="mpanels">{"".join(panels)}</div></div>')
    where = (f' et se soumettent sur le <a href="{escape(board)}"{NEW_TAB}>tableau des scores</a>'
             if board else "")
    note = (f'<p class="note">La veille de la finale, la liste de départ a été truquée en échangeant les '
            f'puces de chronométrage. Suivez la piste jusqu\'au coupable. {len(MISSIONS)} missions, '
            f'{total} points. Les flags ont la forme <code>TRIATHLON{{...}}</code>{where}. '
            f'Détails dans l\'onglet <a href="/contexte">Contexte</a>.</p>')
    return html(layout("Missions", fr(page_body), "/", f"E{n}", f"=SOMME(E3:E{r})", fr(note),
                       scripts=MISSIONS_JS))


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
# an opaque no-cors answer means the tool is up. Copier is handled by SCRIPT.
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


# --------------------------------------------------------------- Mode guidé
# A beginner walkthrough per mission: one plain-language "why", where to go,
# then 3-5 steps. Steps use only the browser, CyberChef and the team terminal
# (the Outils tab) plus the share login players get from mission 01. Flags are
# random per event, so the last step says WHERE the flag appears and never
# contains a flag or the saboteur's name. Backticks mark inline code.
GUIDE = {
    "01": ("Les robots d'indexation lisent un fichier qui liste les pages qu'un site "
           "préfère garder hors des moteurs de recherche.",
           "Un navigateur suffit.",
           ["Ouvrez `/robots.txt` sur le site DécaFlop.",
            "Repérez la ligne `Disallow:` : elle donne un chemin vers un espace staff.",
            "Ouvrez ce chemin : le portail staff affiche le flag (et l'identifiant du partage interne, utile plus tard)."]),
    "02": ("Un fichier peut en cacher un autre : ici une archive ZIP est collée à la fin d'une image PNG.",
           "Le site, puis CyberChef.",
           ["Dans l'espace presse (`/presse`), téléchargez l'affiche officielle.",
            "Dans CyberChef, glissez l'image en entrée et appliquez l'opération `Unzip` (ou `Extract Files`).",
            "Ouvrez le fichier `flag.txt` extrait : il contient le flag."]),
    "03": ("Les photos gardent des métadonnées EXIF : date, auteur, parfois coordonnées GPS.",
           "Le site, puis CyberChef.",
           ["Dans les actualités (`/actualites`), téléchargez la photo en taille réelle.",
            "Dans CyberChef, appliquez `Extract EXIF` sur la photo.",
            "Lisez le champ `Image Description` : il contient le flag. Notez aussi la date et l'auteur, ils reviennent plus tard."]),
    "04": ("La page affiche un profil à partir d'un numéro dans l'URL, sans vérifier que c'est bien le vôtre "
           "(faille IDOR).",
           "Le navigateur.",
           ["Connectez-vous : vous arrivez sur `/profile/1042`, votre dossard.",
            "Changez le numéro dans l'URL pour `1000`, le compte admin.",
            "Le flag est dans l'encadré Jeton d'audit du profil admin."]),
    "05": ("Une connexion en HTTP non chiffré laisse passer l'identifiant et le mot de passe en clair sur le réseau.",
           "Le partage interne, puis CyberChef.",
           ["Dans le partage, dossier Chronométrage puis Captures, téléchargez `timing_booth.pcap`.",
            "Dans CyberChef, appliquez `Extract Strings` et cherchez la ligne qui commence par `Authorization: Basic` suivie d'un texte.",
            "Appliquez `From Base64` sur ce texte : vous obtenez `timingop:` suivi du flag. Le flag est la partie après le deux-points."]),
    "06": ("Le formulaire de connexion insère directement votre saisie dans une requête SQL, "
           "on peut donc la détourner (injection SQL).",
           "Le navigateur.",
           ["Dans le champ identifiant, saisissez `' OR '1'='1' -- ` (gardez l'espace à la fin).",
            "Mettez n'importe quel mot de passe et validez.",
            "Vous arrivez sur le tableau de bord : le flag est dans l'encadré Code de validation."]),
    "07": ("Supprimer un fichier n'efface pas aussitôt ses octets : on peut les récupérer dans une image disque "
           "(récupération par carving).",
           "Le partage interne, puis CyberChef.",
           ["Dans le partage, dossier Arbitrage puis Pièces, téléchargez `referee_usb.img` dans un dossier vide.",
            "Dans CyberChef, appliquez `Extract Files` : l'image PNG cachée est détectée et extraite.",
            "Ouvrez l'image PNG extraite : le flag y est écrit."]),
    "09": ("Un ancien hachage de mot de passe peut se casser avec une liste de mots. Ici le champ BCODE vaut "
           "le MD5 du mot de passe mis en majuscules.",
           "Le partage interne, puis CyberChef (ou le terminal).",
           ["Dans le partage, Basis SAP puis Exports, ouvrez `SAP_USR02_export.csv`.",
            "Repérez l'utilisateur dont la dernière connexion est le 2026-11-01 vers 18h42 : c'est le suspect.",
            "Pour chaque mot de `wordlist.txt` (dossier IT puis Outils), dans CyberChef : `To Upper case` puis `MD5`, et comparez au BCODE du suspect. Le mot qui correspond est son mot de passe.",
            "Avec ce mot de passe, ouvrez `case_file.zip` (Direction de course puis Dossier incident) via `Unzip` avec mot de passe. Le fichier `flag.txt` donne le flag et nomme le coupable."]),
    "10": ("Un jeton JWT est seulement signé : si la clé de signature est faible, on peut forger soi-même un "
           "jeton admin.",
           "La Results API, puis CyberChef.",
           ["Ouvrez `/api/token` pour obtenir un jeton d'invité.",
            "Trouvez la clé de signature HS256 : cassez-la avec la liste de mots de l'équipe, ou récupérez-la via la mission 11.",
            "Dans CyberChef, `JWT Sign` avec la charge `{\"role\":\"admin\"}`, algorithme HS256 et cette clé.",
            "Appelez `/api/results` avec l'en-tête `Authorization: Bearer` suivi de votre jeton : le flag est dans le champ `signature_officielle`."]),
    "11": ("Un dossier `.git` laissé en ligne permet de reconstituer tout le code, y compris ce qui a été "
           "supprimé dans un commit récent.",
           "Le site chronométrage, puis le terminal d'équipe.",
           ["Vérifiez l'exposition en ouvrant `/.git/` sur le site de chronométrage.",
            "Dans le terminal, lancez `git-dumper http://ADRESSE:8011/.git/ ./dump` (ADRESSE est l'adresse du Pi).",
            "Allez dans le dossier (`cd dump`) et lisez la version précédente : `git show HEAD~1:config.py`. Le jeton d'export qui avait été retiré est le flag (ce fichier révèle aussi la clé JWT de la mission 10)."]),
    "12": ("Le générateur insère votre nom dans un modèle de page : on peut y glisser du code de modèle "
           "(faille SSTI).",
           "Le générateur de certificats.",
           ["Dans le champ du nom, saisissez `{{7*7}}` : si le certificat affiche `49`, l'injection fonctionne.",
            "Saisissez ensuite `{{ config['FLAG'] }}` : le certificat imprime le flag à la place du nom."]),
    "13": ("Un raccourci SAP GUI (`.sap`) peut stocker un mot de passe enregistré, ici simplement encodé en base64.",
           "Le partage interne, puis CyberChef.",
           ["Dans le partage, IT puis Sauvegardes postes puis portable-equipe-03, ouvrez `dflop_erp.sap`.",
            "Repérez la ligne `Password=` suivie d'un texte encodé.",
            "Dans CyberChef, `From Base64` sur ce texte : vous obtenez le flag."]),
    "14": ("Un gateway SAP sans liste de contrôle (reginfo vide) laisse n'importe quel programme externe "
           "s'enregistrer.",
           "Le gateway SAP.",
           ["Ouvrez `/sap/gw/reginfo` : la liste d'accès est vide, tout est autorisé.",
            "Sur la page d'accueil, utilisez le formulaire pour enregistrer un programme (TP) avec un nom quelconque.",
            "La réponse affiche une Clé d'enregistrement : c'est le flag."]),
    "15": ("Un secret écrit en dur dans le code peut être découpé en morceaux pour échapper à une simple recherche.",
           "Le partage interne.",
           ["Dans le partage, Basis SAP puis Développements, ouvrez `ZDFLOP_RESULT_EXPORT.abap`.",
            "Repérez les variables `lv_a`, `lv_b` et `lv_c` (ignorez `lv_decoy`, un leurre).",
            "Remettez les morceaux dans l'ordre a puis b puis c : vous obtenez le flag."]),
}


COPY_ICON = ('<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">'
             '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/>'
             '<path d="M3 10.5V3.5a1 1 0 0 1 1-1h6.5" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>')


def gcode(text, copy=False):
    """Escape a guide line and turn `backtick` spans into <code> (no other raw HTML).
    With copy=True each span gets a Copier button holding the exact text, trailing
    spaces included."""
    parts = escape(text).split("`")
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(part)
        elif copy:
            out.append(f'<span class="cc"><code>{part}</code><button type="button" class="cpy" '
                       f'data-copy="{part}" title="Copier" aria-label="Copier {part}">{COPY_ICON}</button></span>')
        else:
            out.append(f"<code>{part}</code>")
    return "".join(out)


MISSION_BY_NUM = {m[0]: m for m in MISSIONS}


def guide_where(num):
    """Links for where to go: the mission's live service, then the browser tools
    that the guide line names (CyberChef, the team terminal)."""
    _concept, tool, _steps = GUIDE[num]
    live = MISSION_BY_NUM[num][6]
    name, port = LIVE_LABEL[live]
    links = [f'<a class="wto" href="{escape(service_url(live))}"{NEW_TAB}>{name} '
             f'<span class="mute">({port})</span> {EXT}</a>']
    for label, key, url in (("CyberChef", "CyberChef", tool_url(CYBERCHEF_URL, CYBERCHEF_PORT)),
                            ("Terminal d'équipe", "terminal", tool_url(TERMINAL_URL, TERMINAL_PORT))):
        if key in tool:
            links.append(f'<a class="wto" href="{escape(url)}"{NEW_TAB}>{label} {EXT}</a>' if url else
                         f'<span class="wto off">{label} <span class="mute">(non configuré)</span></span>')
    return "".join(links)


def guide_block(num):
    """One mission's guide: the principle, where to go, then the steps. The shared
    script reveals the steps one at a time and remembers how far the player got."""
    concept, tool, steps = GUIDE[num]
    items = "".join(f'<li class="step{"" if i == 0 else " hidden"}">{gcode(st, copy=True)}</li>'
                    for i, st in enumerate(steps))
    return (f'<div class="gblock"><p class="concept">{gcode(concept)}</p>'
            f'<div class="gwhere"><h4>Où aller</h4><div class="wlinks">{guide_where(num)}</div>'
            f'<p class="wtxt">{gcode(tool)}</p></div>'
            f'<div class="gsteps" data-g="{num}"><h4>Étapes</h4><ol class="steps">{items}</ol>'
            '<div class="gctl"><button class="next" type="button" data-go="next">Étape suivante</button>'
            '<button class="all" type="button" data-go="all">Tout afficher</button>'
            '<button class="reset" type="button" data-go="reset" hidden>Recommencer</button>'
            f'<span class="gcount">Étape 1 sur {len(steps)}</span></div></div></div>')


def guide_lock(error="", status=200):
    err = f'<p class="status err" role="alert">{escape(error)}</p>' if error else ""
    body = (
        '<div class="lock"><h1>Mode guidé</h1>'
        '<p>Un pas-à-pas pour les grands débutants. Chaque mission y est expliquée en une phrase, avec '
        'où aller et des étapes révélées une par une. Le guide ne donne jamais le flag.</p>'
        '<p>C\'est optionnel. Demandez le mot de passe à l\'organisation si vous voulez ces explications.</p>'
        f'<form method="post" action="/guide">{err}'
        '<label for="mdp">Mot de passe</label>'
        '<input class="in" id="mdp" name="motdepasse" type="password" autocomplete="off" '
        'autocapitalize="none" spellcheck="false" autofocus>'
        '<button class="go" type="submit">Déverrouiller</button></form></div>')
    return html(layout("Mode guidé", fr(body), "/guide", "A1", "Mode guidé"), status)


def guide_page():
    board = scoreboard_url()
    ids = ctfd_ids()
    index, sections = [], []
    for sec, span, test in SECTIONS:
        entries, cards = [], []
        for num, title, cat, level, pts, _brief, _live, _files in MISSIONS:
            if not test(num) or num not in GUIDE:
                continue
            n = len(GUIDE[num][2])
            entries.append(
                f'<li><a href="#guide-{num}" data-m="{num}"><span class="dot"></span><span class="no">{num}</span>'
                f'<span class="t">{escape(title)}</span><span class="gp" data-gp="{num}">1/{n}</span></a></li>')
            cards.append(
                f'<article class="gcard" id="guide-{num}" data-m="{num}">'
                f'<div class="gtop"><span class="mn">{num}</span> <b>{escape(title)}</b> '
                f'<span class="chip {LEVEL_CLASS[level]}">{level}</span> <span class="chip cat">{escape(cat)}</span> '
                f'<span class="pts">{pts} points</span></div>{guide_block(num)}'
                f'<div class="gfoot">{status_select(num)}{submit_link(num, board, ids)}'
                f'<a class="back" href="/#mission-{num}">Voir la mission</a></div></article>')
        index.append(f'<div class="gsec"><h2>{sec}</h2><ol>{"".join(entries)}</ol></div>')
        sections.append(f'<h2 class="gsech">{sec}<span>{span}</span></h2>{"".join(cards)}')
    intro = ('<p class="ghead">Chaque fiche explique la technique en une phrase, indique où aller, puis révèle '
             'les étapes une par une. Les flags changent à chaque événement, donc la dernière étape dit où le '
             'flag apparaît. Recopiez-le ensuite dans le tableau des scores. Votre avancement reste dans ce '
             'navigateur.</p>')
    body = (f'<div class="gwrap"><nav class="gindex" aria-label="Sommaire du guide">{"".join(index)}</nav>'
            f'<div class="gmain">{intro}{"".join(sections)}</div></div>')
    return html(layout("Mode guidé", fr(body), "/guide", "A1", "Mode guidé"))


@app.get("/guide")
def guide():
    return guide_page() if guide_unlocked() else guide_lock()


@app.post("/guide")
def guide_post():
    given = request.form.get("motdepasse", "")
    if hmac.compare_digest(given, GUIDE_PASSWORD):
        resp = redirect("/guide")
        resp.set_cookie("guide", GUIDE_TOKEN, max_age=60 * 60 * 24 * 7, samesite="Lax")
        return resp
    return guide_lock("Mot de passe incorrect.", 401)


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
