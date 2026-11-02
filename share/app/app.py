#!/usr/bin/env python3
"""
Intranet DFlop — DécaFlop's event intranet / wiki (its own container, not a
challenge). Players log in with the crew account the challenge-01 staff portal
hands out, then browse one space per team; each space holds wiki pages that
describe its part of the incident, with the evidence files attached.

- Pages are fixed, author-written HTML (no user input is rendered as HTML, no
  search box). Attachments are read from HANDOUT_DIR (docker-compose mounts
  handouts/dist there, read-only) and served byte-for-byte through an explicit
  filename -> source map. Nothing outside that map is downloadable; there is no
  path traversal. A file that isn't built yet shows "pas encore disponible" and
  404s on download.
- Login, session, rate-limit and the "redirect to login when logged out" rule
  are unchanged from the former file share.
"""
import hmac
import os
import time
from html import escape as esc

from flask import Flask, Response, abort, redirect, request, send_from_directory, session

HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

app = Flask(__name__)
app.secret_key = os.environ.get("SHARE_SECRET_KEY") or os.urandom(32)

# --------------------------------------------------------------------------
# Inline SVG icons (no external assets — the Pi is offline)
# --------------------------------------------------------------------------
LOGO = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z"/><path d="M4 20a2 2 0 0 1 2-2h13"/></svg>')
PAGE_ICON = ('<svg class="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" '
             'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v4h4"/></svg>')
FILE_BIG = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M6 2h7l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>'
            '<path d="M13 2v5h5"/></svg>')
DL = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
      '<path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M5 21h14"/></svg>')

CSS = """
*{box-sizing:border-box}
:root{--bg:#f6f4f1;--panel:#fff;--line:#e6e1da;--accent:#c2410c;--ink:#2b2724;
 --mute:#8a8178;--soft:#faf8f5}
html{-webkit-text-size-adjust:100%}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);
 font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
svg{display:block}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;background:var(--panel);
 border-bottom:1px solid var(--line);padding:0 20px;height:56px}
.brand{display:flex;align-items:center;gap:11px;font-weight:700;letter-spacing:-.01em;font-size:16px}
.brand .logo{display:grid;place-items:center;width:30px;height:30px;border-radius:8px;background:var(--accent);flex:none}
.brand small{display:block;font-weight:500;color:var(--mute);font-size:11.5px}
.user{display:flex;align-items:center;gap:9px;font-size:13.5px;font-weight:600;white-space:nowrap}
.user .avatar{width:30px;height:30px;border-radius:50%;background:#efe9e2;color:var(--accent);
 display:grid;place-items:center;font-size:12px;font-weight:800;border:1px solid var(--line)}
.user .logout{color:var(--mute);font-size:12.5px;font-weight:600}
.user .logout:hover{color:var(--accent)}
.app{display:grid;grid-template-columns:262px 1fr;min-height:calc(100vh - 56px)}
.side{border-right:1px solid var(--line);background:var(--soft);padding:14px 10px;overflow:auto}
.side .home{display:block;padding:7px 10px;border-radius:7px;font-weight:650;font-size:13.5px;color:var(--ink)}
.side .home:hover{background:#efe9e2}
.side .home.active{background:#f6e7df;color:var(--accent)}
.side h4{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--mute);margin:16px 10px 5px}
.side ul{list-style:none;margin:0;padding:0}
.side li a{display:flex;align-items:center;gap:8px;padding:6px 10px 6px 12px;border-radius:7px;
 font-size:13.5px;color:var(--ink)}
.side li a:hover{background:#efe9e2}
.side li a .ic{color:#b7a690;flex:none}
.side li a.active{background:#f6e7df;color:var(--accent);font-weight:700}
.side li a.active .ic{color:var(--accent)}
.side .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.main{padding:24px 30px;min-width:0}
.wrap{max-width:820px}
.crumb{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--mute);margin-bottom:16px;flex-wrap:wrap}
.crumb a:hover{color:var(--ink)}
.crumb .sep{opacity:.5}
.crumb .cur{color:var(--ink);font-weight:600}
h1.title{font-size:26px;margin:0 0 6px;font-weight:700;line-height:1.2;overflow-wrap:anywhere}
.meta{color:var(--mute);font-size:13px;margin:0 0 20px}
.body{font-size:15px}
.body p{margin:0 0 14px;max-width:68ch}
.body ul{margin:0 0 14px;padding-left:20px}
.body li{margin:4px 0;max-width:66ch}
.body a{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.body code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;background:var(--soft);
 border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.seealso{background:var(--soft);border:1px solid var(--line);border-left:3px solid var(--accent);
 border-radius:8px;padding:11px 14px;font-size:13.5px;max-width:68ch}
.seealso b{color:var(--ink)}
.attach{margin-top:28px;max-width:640px}
.attach h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);margin:0 0 12px}
.atts{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.att{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px;background:var(--panel);
 border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.att .ai{width:40px;height:40px;border-radius:9px;display:grid;place-items:center;background:var(--soft);color:var(--accent);flex:none}
.att .an{font-weight:650;overflow-wrap:anywhere}
.att .am{color:var(--mute);font-size:12.5px;margin-top:2px}
.att .am.na{font-style:italic}
.dl{display:inline-flex;align-items:center;gap:7px;background:var(--accent);color:#fff;border-radius:8px;
 padding:9px 14px;font-size:13.5px;font-weight:700;white-space:nowrap}
.dl:hover{background:#a83809;color:#fff}
/* home */
.banner{background:var(--ink);color:#fff;border-radius:12px;padding:22px 24px;margin-bottom:26px;max-width:820px}
.banner .tag{display:inline-block;background:var(--accent);color:#fff;font-size:11px;font-weight:800;
 letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:999px}
.banner h1{font-size:21px;margin:12px 0 8px;line-height:1.25}
.banner p{margin:0;color:#d8d2cb;font-size:14px;max-width:62ch}
.banner .ref{font-family:ui-monospace,Menlo,Consolas,monospace;color:#fff}
.sec{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);margin:0 0 12px}
.spaces{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;max-width:820px;margin-bottom:28px}
.sp{display:block;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:16px}
.sp:hover{border-color:#d9d0c4}
.sp .spn{font-weight:700;font-size:15px}
.sp .spm{color:var(--mute);font-size:12.5px;margin-top:4px}
.recent{list-style:none;margin:0;padding:0;max-width:820px}
.recent li{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;padding:9px 0;border-top:1px solid var(--line)}
.recent li:first-child{border-top:0}
.recent .rt{font-weight:650}
.recent .rm{color:var(--mute);font-size:12.5px}
.badge{flex:none;font-size:10px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;padding:3px 6px;border-radius:4px}
.b-csv{background:#e8f3ec;color:#1f7a4d}
.b-txt{background:#edeef1;color:#5a6472}
.b-pcap{background:#e2f1f2;color:#0f6b73}
.b-img{background:#efeaf7;color:#6b3fa0}
.b-zip{background:#f7eedd;color:#8a5a00}
.b-sap{background:#e7edfb;color:#2a52be}
.b-abap{background:#f3e9e3;color:#9a4a24}
.mnav{display:none}
/* login */
.login-wrap{min-height:100vh;display:grid;place-items:center;padding:24px}
.login-card{width:100%;max-width:380px;background:var(--panel);border:1px solid var(--line);
 border-radius:14px;padding:30px 28px;box-shadow:0 10px 30px rgba(43,39,36,.06)}
.login-card .brand{font-size:19px;margin-bottom:4px}
.login-card .brand .logo{width:36px;height:36px}
.login-card .tag{color:var(--mute);font-size:13px;margin:0 0 22px 47px}
.fld{margin-bottom:14px}
.fld label{display:block;font-size:12.5px;font-weight:650;margin-bottom:6px}
.fld input{width:100%;font:inherit;font-size:14px;padding:11px 12px;border:1px solid #d9d0c4;border-radius:9px;background:var(--soft)}
.fld input:focus{outline:none;border-color:var(--accent)}
.loginerr{background:#fdecee;border:1px solid #f3c6cc;color:#8a1020;border-radius:9px;padding:9px 12px;font-size:13px;margin:0 0 14px}
.note{margin:18px 0 0;font-size:12.5px;color:var(--mute);background:var(--soft);border:1px solid var(--line);
 border-radius:9px;padding:11px 13px;line-height:1.45}
.btn{display:inline-flex;align-items:center;gap:8px;justify-content:center;width:100%;margin-top:4px;
 background:var(--accent);color:#fff;border:0;border-radius:9px;padding:12px;font:inherit;font-size:15px;font-weight:700;cursor:pointer}
.btn:hover{background:#a83809;color:#fff}
.center{text-align:center;padding:48px 0}
.center h1{font-size:22px;margin:0 0 6px}
.center p{color:var(--mute);margin:0 0 16px}
@media (max-width:760px){
 .top{padding:0 14px;height:52px;gap:10px}
 .brand small{display:none}
 .app{grid-template-columns:1fr}
 .side{display:none}
 .main{padding:16px}
 .spaces{grid-template-columns:1fr}
 .att{grid-template-columns:auto 1fr;gap:8px 12px}
 .att .dl{grid-column:1 / -1;justify-content:center}
 .mnav{display:block;margin-bottom:14px}
 .mnav summary{list-style:none;display:inline-flex;align-items:center;gap:8px;background:var(--panel);
  border:1px solid var(--line);border-radius:9px;padding:9px 13px;font-weight:650;font-size:13.5px;cursor:pointer}
 .mnav summary::-webkit-details-marker{display:none}
 .mnav .side{display:block;border:0;background:transparent;padding:12px 2px 0}
}
"""


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")


def head(title):
    return ("<!doctype html><html lang=fr><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>" + esc(title) + "</title><style>" + CSS + "</style></head><body>")


def fr(text):
    """French typography: non-breaking spaces inside « » and before : ? !"""
    nb = chr(160)
    for a, b in (("« ", "«" + nb), (" »", nb + "»"), (" :", nb + ":"), (" ?", nb + "?"), (" !", nb + "!")):
        text = text.replace(a, b)
    return text


def fr_size(n):
    size = float(n)
    for unit in ("o", "Ko", "Mo"):
        if size < 1024 or unit == "Mo":
            return f"{size:.0f} {unit}" if unit == "o" else (f"{size:.1f} {unit}").replace(".", ",")
        size /= 1024


# --------------------------------------------------------------------------
# Content model: attachment metadata + the spaces/pages. Page bodies are fixed
# author HTML with no credentials, flags or payloads.
# --------------------------------------------------------------------------
# filename -> (badge, type label). This is also the download whitelist: the
# source file in HANDOUT_DIR has the same name.
FILES = {
    "timing_booth.pcap": ("pcap", "Capture réseau (PCAP)"),
    "referee_usb.img": ("img", "Image disque brute"),
    "SAP_USR02_export.csv": ("csv", "CSV · export de table"),
    "sap_hint.txt": ("txt", "Note d'export"),
    "wordlist.txt": ("txt", "Liste de mots"),
    "case_file.zip": ("zip", "Archive chiffrée"),
    "dflop_erp.sap": ("sap", "Raccourci SAP GUI"),
    "ZDFLOP_RESULT_EXPORT.abap": ("abap", "Source ABAP"),
}

_P_INCIDENT = (
    "<p>Dossier de l'incident de la finale. La veille de la course, la liste de "
    "départ a été falsifiée en échangeant des puces de chronométrage. Ce dossier "
    "regroupe les pièces transmises par les différents services.</p>"
    "<p>L'archive jointe est protégée par mot de passe ; elle contient la "
    "conclusion de l'enquête. La passphrase se déduit du travail mené sur les "
    "comptes SAP (espace Basis SAP).</p>")
_P_PCAP = (
    "<p>La cabine de chronométrage envoie les temps intermédiaires sur le Wi-Fi "
    "staff, et sa connexion passe encore en HTTP en clair. Nous avons capturé le "
    "trafic pendant la soirée qui a précédé la finale.</p>"
    "<p>La capture réseau est jointe ci-dessous.</p>")
_P_USB = (
    "<p>Une clé USB oubliée par un arbitre a été retrouvée dans la cabine. Son "
    "propriétaire affirme avoir « tout supprimé », mais nous en avons fait une "
    "image avant toute manipulation.</p>"
    "<p>L'image brute de la clé est jointe ci-dessous.</p>")
_P_USR02 = (
    "<p>La table des résultats <code>ZRACE_RESULT</code> du SAP DFlop ERP "
    "(système DFL, mandant 001) a été modifiée la veille de la finale. Pour "
    "l'enquête, l'équipe Basis a exporté la table des utilisateurs USR02 : "
    "comptes, dernières connexions et anciens hachages de mots de passe.</p>"
    "<p>L'export et la note d'accompagnement sont joints ci-dessous.</p>"
    "<p class=\"seealso\"><b>Voir aussi :</b> le moniteur du gateway SAP (service "
    "interne, port 8014) et la page <a href=\"/espace/basis/developpements\">"
    "Développements</a>.</p>")
_P_DEV = (
    "<p>Rapports et développements maison du DFlop ERP. Le rapport "
    "<code>ZDFLOP_RESULT_EXPORT</code> pousse les résultats vers le système de "
    "résultats par RFC.</p>"
    "<p>Rappel de l'équipe : ne pas laisser de jeton d'accès en dur dans le code "
    "source. La source du rapport est jointe ci-dessous.</p>")
_P_OUTILS = (
    "<p>Boîte à outils de l'équipe IT d'urgence pour l'enquête : listes de mots "
    "pour les tests de robustesse, scripts divers.</p>"
    "<p>La liste de mots utilisée est jointe ci-dessous.</p>")
_P_SAUV = (
    "<p>Sauvegardes des postes de l'équipe. Dossier du portable "
    "<code>portable-equipe-03</code>.</p>"
    "<p>Le raccourci SAP GUI ci-joint ouvre le système DFL, mandant 001 — l'ERP "
    "de production DFlop — et a « enregistré le mot de passe » du compte.</p>")
_P_BIENVENUE = (
    "<p>Bienvenue sur l'Intranet DFlop, l'espace de travail interne de "
    "l'événement. Chaque service dispose de son espace ; retrouvez les procédures, "
    "plannings et comptes-rendus dans la barre latérale.</p>"
    "<p>Pour toute question sur vos accès, contactez l'astreinte IT (poste 300).</p>")
_P_PROCEDURES = (
    "<p>Procédures du jour J, côté systèmes.</p>"
    "<ul><li>Ouverture des accès staff à 6 h 00.</li>"
    "<li>Vérification des sauvegardes avant la première épreuve.</li>"
    "<li>Astreinte IT joignable au poste 300 toute la journée.</li></ul>"
    "<p>Document de travail, mis à jour au fil de l'eau.</p>")
_P_PLANNING = (
    "<p>Planning des bénévoles pour le week-end de la finale.</p>"
    "<ul><li>Samedi : accueil et dossards, ravitaillement vélo, point d'eau course.</li>"
    "<li>Dimanche : parc à vélos, village partenaires.</li></ul>"
    "<p>Contact logistique : poste 118. Pensez à emporter de l'eau.</p>")
_P_CR = (
    "<p>Compte-rendu de la réunion d'organisation.</p>"
    "<ul><li>Validation du programme et des horaires.</li>"
    "<li>Rappel des consignes de sécurité sur le parcours.</li>"
    "<li>Point météo : conditions favorables attendues.</li></ul>"
    "<p>Prochaine réunion : le matin de la course, 6 h 30, au bureau de course.</p>")

SPACES = [
    {"key": "direction", "name": "Direction de course", "pages": [
        {"slug": "dossier-incident", "title": "Dossier incident", "by": "Direction de course",
         "date": "2 nov. 2026", "body": _P_INCIDENT, "files": ["case_file.zip"]},
        {"slug": "compte-rendu-reunion", "title": "Compte-rendu de réunion", "by": "Direction de course",
         "date": "30 oct. 2026", "body": _P_CR, "files": []},
    ]},
    {"key": "chrono", "name": "Chronométrage", "pages": [
        {"slug": "capture-wifi-cabine", "title": "Capture Wi-Fi de la cabine", "by": "Équipe IT d'urgence",
         "date": "1 nov. 2026", "body": _P_PCAP, "files": ["timing_booth.pcap"]},
    ]},
    {"key": "arbitrage", "name": "Arbitrage", "pages": [
        {"slug": "cle-usb", "title": "Clé USB retrouvée", "by": "Arbitrage",
         "date": "1 nov. 2026", "body": _P_USB, "files": ["referee_usb.img"]},
    ]},
    {"key": "basis", "name": "Basis SAP", "pages": [
        {"slug": "export-usr02", "title": "Export USR02", "by": "Basis SAP",
         "date": "1 nov. 2026", "body": _P_USR02, "files": ["SAP_USR02_export.csv", "sap_hint.txt"]},
        {"slug": "developpements", "title": "Développements", "by": "Basis SAP",
         "date": "28 oct. 2026", "body": _P_DEV, "files": ["ZDFLOP_RESULT_EXPORT.abap"]},
    ]},
    {"key": "it", "name": "IT", "pages": [
        {"slug": "outils", "title": "Outils", "by": "Équipe IT d'urgence",
         "date": "31 oct. 2026", "body": _P_OUTILS, "files": ["wordlist.txt"]},
        {"slug": "sauvegardes-postes", "title": "Sauvegardes postes", "by": "Équipe IT d'urgence",
         "date": "30 oct. 2026", "body": _P_SAUV, "files": ["dflop_erp.sap"]},
        {"slug": "bienvenue", "title": "Bienvenue", "by": "Communication DécaFlop",
         "date": "27 oct. 2026", "body": _P_BIENVENUE, "files": []},
        {"slug": "procedures-jour-j", "title": "Procédures jour J", "by": "Direction de course",
         "date": "29 oct. 2026", "body": _P_PROCEDURES, "files": []},
    ]},
    {"key": "logistique", "name": "Logistique", "pages": [
        {"slug": "planning-benevoles", "title": "Planning bénévoles", "by": "Logistique",
         "date": "28 oct. 2026", "body": _P_PLANNING, "files": []},
    ]},
]

SPACE_BY_KEY = {s["key"]: s for s in SPACES}
PAGE_BY_PATH = {(s["key"], p["slug"]): p for s in SPACES for p in s["pages"]}

MONTHS = {"janv.": 1, "févr.": 2, "mars": 3, "avr.": 4, "mai": 5, "juin": 6,
          "juil.": 7, "août": 8, "sept.": 9, "oct.": 10, "nov.": 11, "déc.": 12}


def date_key(ds):
    p = ds.split()
    try:
        return (int(p[2]), MONTHS.get(p[1], 0), int(p[0]))
    except (IndexError, ValueError):
        return (0, 0, 0)


def page_url(space_key, slug):
    return "/espace/" + space_key + "/" + slug


def space_url(space_key):
    return "/espace/" + space_key


def is_available(name):
    return os.path.isfile(os.path.join(HANDOUT_DIR, name))


def file_size(name):
    p = os.path.join(HANDOUT_DIR, name)
    return fr_size(os.path.getsize(p)) if os.path.isfile(p) else None


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def sidebar(cur_space="", cur_slug="", home=False):
    home_cls = "home active" if home else "home"
    out = ['<nav class="side">', '<a class="' + home_cls + '" href="/">Accueil</a>']
    for s in SPACES:
        out.append('<h4>' + esc(s["name"]) + '</h4><ul>')
        for p in s["pages"]:
            active = (s["key"] == cur_space and p["slug"] == cur_slug)
            cls = ' class="active"' if active else ""
            out.append('<li><a' + cls + ' href="' + page_url(s["key"], p["slug"]) + '">' +
                       PAGE_ICON + '<span class="nm">' + esc(p["title"]) + '</span></a></li>')
        out.append('</ul>')
    out.append('</nav>')
    return "".join(out)


def shell(title, cur_space="", cur_slug="", home=False, body=""):
    side = sidebar(cur_space, cur_slug, home)
    mnav = ('<details class="mnav"><summary>Espaces</summary>' + side + '</details>')
    return (head(title) + topbar() + '<div class="app">' + side +
            '<main class="main">' + mnav + '<div class="wrap">' + body + '</div></main></div></body></html>')


def topbar():
    user = esc(session.get("user", SHARE_USER))
    return ('<header class="top"><div class="brand"><span class="logo">' + LOGO + '</span>'
            '<span>Intranet DFlop<small>espace de travail interne</small></span></div>'
            '<div class="user"><span class="avatar">IT</span><span>' + user + '</span>'
            '<a class="logout" href="/logout">Déconnexion</a></div></header>')


def crumbs(*items):
    parts = []
    for href, label in items:
        if href:
            parts.append('<a href="' + href + '">' + esc(label) + '</a>')
        else:
            parts.append('<span class="cur">' + esc(label) + '</span>')
    return '<div class="crumb">' + '<span class="sep">/</span>'.join(parts) + '</div>'


def attachments_block(files):
    if not files:
        return ""
    items = []
    for name in files:
        badge, typ = FILES.get(name, ("txt", "Fichier"))
        size = file_size(name)
        if size is not None:
            meta = '<div class="am">' + esc(typ) + ' · ' + size + '</div>'
            dl = ('<a class="dl" href="/telecharger/' + name + '" download>' + DL + ' Télécharger</a>')
        else:
            meta = '<div class="am na">' + esc(typ) + ' · pas encore disponible</div>'
            dl = ''
        items.append(
            '<li class="att"><span class="ai">' + FILE_BIG + '</span>'
            '<div><span class="badge b-' + badge + '">' + esc(badge) + '</span> '
            '<span class="an">' + esc(name) + '</span>' + meta + '</div>' + dl + '</li>')
    return ('<section class="attach"><h2>Pièces jointes</h2>'
            '<ul class="atts">' + "".join(items) + '</ul></section>')


# --------------------------------------------------------------------------
# Auth (unchanged: the login is handed out by the challenge-01 staff portal)
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


@app.before_request
def require_login():
    if request.endpoint in ("login", "logout", "static"):
        return None
    if not session.get("ok"):
        return redirect("/login")
    return None


def login_page(error="", status=200):
    err = '<p class="loginerr" role="alert">' + esc(error) + '</p>' if error else ''
    body = (head("Connexion · Intranet DFlop") +
            '<div class="login-wrap"><div class="login-card">'
            '<div class="brand"><span class="logo">' + LOGO + '</span><span>Intranet DFlop</span></div>'
            '<p class="tag">espace de travail interne</p>'
            '<form method="post" action="/login">' + err +
            '<div class="fld"><label for="u">Identifiant</label>'
            '<input id="u" name="identifiant" placeholder="equipe-it" autocomplete="username"></div>'
            '<div class="fld"><label for="p">Mot de passe</label>'
            '<input id="p" name="motdepasse" type="password" autocomplete="current-password"></div>'
            '<button class="btn" type="submit">Se connecter</button></form>'
            '<p class="note">Accès réservé au personnel DécaFlop et à l\'équipe IT d\'urgence. '
            'Identifiants fournis par le portail staff du site DécaFlop.</p>'
            '</div></div></body></html>')
    return html(body, status)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("ok"):
            return redirect("/")
        return login_page()
    ip = request.remote_addr or "?"
    if _too_many(ip):
        return login_page("Trop de tentatives. Patientez quelques instants avant de réessayer.", 429)
    u = request.form.get("identifiant", "")
    p = request.form.get("motdepasse", "")
    if hmac.compare_digest(u, SHARE_USER) and hmac.compare_digest(p, SHARE_PASSWORD):
        session.clear()
        session["ok"] = True
        session["user"] = SHARE_USER
        _FAILS.pop(ip, None)
        return redirect("/")
    _record_fail(ip)
    return login_page("Identifiant ou mot de passe incorrect.", 401)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
@app.get("/")
def home():
    cards = []
    for s in SPACES:
        n = len(s["pages"])
        cards.append('<a class="sp" href="' + space_url(s["key"]) + '">'
                     '<div class="spn">' + esc(s["name"]) + '</div>'
                     '<div class="spm">' + str(n) + (" pages" if n > 1 else " page") + '</div></a>')
    recent_pages = sorted(
        ((p, s) for s in SPACES for p in s["pages"]),
        key=lambda ps: date_key(ps[0]["date"]), reverse=True)[:5]
    rec = []
    for p, s in recent_pages:
        rec.append('<li><a class="rt" href="' + page_url(s["key"], p["slug"]) + '">' + esc(p["title"]) + '</a>'
                   '<span class="rm">' + esc(s["name"]) + ' · modifié par ' + esc(p["by"]) +
                   ' · ' + esc(p["date"]) + '</span></li>')
    body = fr(
        '<section class="banner"><span class="tag">Incident</span>'
        '<h1>Liste de départ de la finale falsifiée</h1>'
        '<p><span class="ref">INC-2026-11-01</span> · ouvert la veille de la finale. '
        'Parcourez les espaces des services pour rassembler les pièces de l\'enquête ; '
        'les fichiers sont joints aux pages concernées.</p></section>'
        '<p class="sec">Espaces</p><div class="spaces">' + "".join(cards) + '</div>'
        '<p class="sec">Activité récente</p><ul class="recent">' + "".join(rec) + '</ul>')
    return html(shell("Intranet DFlop", home=True, body=body))


@app.get("/espace/<space_key>")
def space(space_key):
    s = SPACE_BY_KEY.get(space_key)
    if s is None:
        abort(404)
    items = []
    for p in s["pages"]:
        items.append('<li><a class="rt" href="' + page_url(s["key"], p["slug"]) + '">' + esc(p["title"]) + '</a>'
                     '<span class="rm">modifié par ' + esc(p["by"]) + ' · ' + esc(p["date"]) + '</span></li>')
    body = (crumbs(("/", "Accueil"), (None, s["name"])) +
            '<h1 class="title">' + esc(s["name"]) + '</h1>'
            '<p class="meta">Espace de l\'équipe · ' + str(len(s["pages"])) +
            (" pages" if len(s["pages"]) > 1 else " page") + '</p>'
            '<ul class="recent">' + "".join(items) + '</ul>')
    return html(shell(s["name"] + " · Intranet DFlop", cur_space=space_key, body=body))


@app.get("/espace/<space_key>/<slug>")
def wiki_page(space_key, slug):
    p = PAGE_BY_PATH.get((space_key, slug))
    if p is None:
        abort(404)
    s = SPACE_BY_KEY[space_key]
    body = (crumbs(("/", "Accueil"), (space_url(space_key), s["name"]), (None, p["title"])) +
            '<h1 class="title">' + esc(p["title"]) + '</h1>'
            '<p class="meta">modifié par ' + esc(p["by"]) + ' · ' + esc(p["date"]) + '</p>'
            '<div class="body">' + fr(p["body"]) + '</div>' +
            attachments_block(p["files"]))
    return html(shell(p["title"] + " · Intranet DFlop", cur_space=space_key, cur_slug=slug, body=body))


@app.get("/telecharger/<name>")
def download(name):
    # Serve ONLY whitelisted attachment names, byte-for-byte. Anything else, a
    # traversal attempt, or a file that isn't built yet -> 404.
    if name not in FILES or not is_available(name):
        abort(404)
    return send_from_directory(HANDOUT_DIR, name, as_attachment=True)


@app.errorhandler(404)
def not_found(_e):
    if not session.get("ok"):
        return redirect("/login")
    body = ('<div class="center"><h1 class="title">Introuvable</h1>'
            '<p>Cette page ou ce fichier n\'existe pas.</p>'
            '<a class="dl" href="/">Retour à l\'accueil</a></div>')
    return html(shell("Introuvable · Intranet DFlop", body=body), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
