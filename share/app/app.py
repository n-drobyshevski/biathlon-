#!/usr/bin/env python3
"""
Partage DFlop — DécaFlop's internal document share ("espace documentaire
interne"). Its own container, not a challenge: players log in with the crew
account the cellule de crise hands out, then browse department folders to find
the evidence files instead of downloading them from the hub.

- Files are read from HANDOUT_DIR (docker-compose mounts handouts/dist there,
  read-only) and served byte-for-byte through an explicit path -> filename map.
  Nothing outside that map is downloadable; there is no path traversal and no
  user input is echoed back (no search box).
- A few mundane text files are generated inline as decoys; they are clearly
  boring and hold no clues.
"""
import hmac
import os
import time
from html import escape as esc
from urllib.parse import quote

from flask import Flask, Response, abort, redirect, request, send_from_directory, session

HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

app = Flask(__name__)
app.secret_key = os.environ.get("SHARE_SECRET_KEY") or os.urandom(32)

# --------------------------------------------------------------------------
# Inline SVG icons (no external assets — the Pi is offline)
# --------------------------------------------------------------------------
FOLDER = ('<svg class="ic" width="20" height="20" viewBox="0 0 24 24" fill="none" '
          'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
          'stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v7'
          'a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>')
FOLDER_BIG = FOLDER.replace('width="20" height="20"', 'width="26" height="26"').replace('class="ic"', 'class="fic"')
FILE_BIG = ('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M6 2h7l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>'
            '<path d="M13 2v5h5"/></svg>')
DL = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
      '<path d="M12 3v12"/><path d="M7 11l5 5 5-5"/><path d="M5 21h14"/></svg>')
LOGO = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>')

CSS = """
*{box-sizing:border-box}
:root{--bg:#f6f4f1;--panel:#fff;--line:#e6e1da;--accent:#c2410c;--ink:#2b2724;
 --mute:#8a8178;--soft:#faf8f5}
html{-webkit-text-size-adjust:100%}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
svg{display:block}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;background:var(--panel);
 border-bottom:1px solid var(--line);padding:0 20px;height:58px}
.brand{display:flex;align-items:center;gap:11px;font-weight:700;letter-spacing:-.01em;font-size:16px}
.brand .logo{display:grid;place-items:center;width:31px;height:31px;border-radius:8px;background:var(--accent);flex:none}
.brand small{display:block;font-weight:500;color:var(--mute);font-size:11.5px}
.top-right{display:flex;align-items:center;gap:22px}
.storage{display:flex;align-items:center;gap:9px;font-size:12.5px;color:var(--mute);white-space:nowrap}
.storage .bar{width:120px;height:7px;border-radius:4px;background:#ece7e0;overflow:hidden}
.storage .bar i{display:block;height:100%;background:var(--accent);opacity:.75}
.user{display:flex;align-items:center;gap:9px;font-size:13.5px;font-weight:600;white-space:nowrap}
.user .avatar{width:31px;height:31px;border-radius:50%;background:#efe9e2;color:var(--accent);
 display:grid;place-items:center;font-size:12px;font-weight:800;border:1px solid var(--line)}
.user .logout{color:var(--mute);font-size:12.5px;font-weight:600}
.user .logout:hover{color:var(--accent)}
.app{display:grid;grid-template-columns:252px 1fr;min-height:calc(100vh - 58px)}
.tree{border-right:1px solid var(--line);background:var(--soft);padding:16px 10px}
.tree h3{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--mute);margin:4px 10px 10px}
.tree ul{list-style:none;margin:0;padding:0}
.tree ul ul{margin-left:9px;padding-left:9px;border-left:1px solid var(--line)}
.tree .node{display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:8px;font-size:14px}
.tree .node:hover{background:#efe9e2}
.tree .chev{color:var(--mute);font-size:9px;width:9px;text-align:center;flex:none}
.tree .ic{color:#b7a690;flex:none}
.tree .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tree .active{background:#f6e7df;color:var(--accent);font-weight:700}
.tree .active .ic{color:var(--accent)}
.main{padding:22px 26px;min-width:0}
.crumb{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--mute);margin-bottom:16px;flex-wrap:wrap}
.crumb a:hover{color:var(--ink)}
.crumb .sep{opacity:.5}
.crumb .cur{color:var(--ink);font-weight:600}
h1.page{font-size:20px;margin:0 0 4px;font-weight:700;overflow-wrap:anywhere}
.psub{color:var(--mute);font-size:13px;margin:0 0 18px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.folder{display:block;background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:16px}
.folder:hover{border-color:#d9d0c4}
.folder .fic{color:var(--accent);margin-bottom:11px}
.folder .fn{font-weight:650;font-size:15px;overflow-wrap:anywhere}
.folder .fm{color:var(--mute);font-size:12.5px;margin-top:5px}
.list{background:var(--panel);border:1px solid var(--line);border-radius:11px;overflow:hidden}
.list .hd,.list .row{display:grid;grid-template-columns:1fr 120px 112px 168px;gap:12px;align-items:center;padding:11px 16px}
.list .hd{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);
 border-bottom:1px solid var(--line);background:var(--soft)}
.list .row{border-top:1px solid var(--line);color:var(--ink)}
.list .row:first-of-type{border-top:0}
.list .row:hover{background:var(--soft)}
.list .row.sel{background:#fbf1ea;box-shadow:inset 3px 0 0 var(--accent)}
.fname{display:flex;align-items:center;gap:10px;min-width:0}
.fname .ic{color:var(--accent);flex:none}
.fname .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.muted{color:var(--mute);font-size:13px;font-variant-numeric:tabular-nums}
.na{font-style:italic}
.rowmeta{display:none}
.badge{flex:none;font-size:10px;font-weight:800;letter-spacing:.03em;text-transform:uppercase;padding:3px 6px;border-radius:4px}
.b-csv{background:#e8f3ec;color:#1f7a4d}
.b-txt{background:#edeef1;color:#5a6472}
.b-pcap{background:#e2f1f2;color:#0f6b73}
.b-img{background:#efeaf7;color:#6b3fa0}
.b-zip{background:#f7eedd;color:#8a5a00}
.b-sap{background:#e7edfb;color:#2a52be}
.b-abap{background:#f3e9e3;color:#9a4a24}
.work{display:grid;grid-template-columns:1fr 320px;gap:18px;align-items:start}
.panelcard{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:18px}
.panelcard h2{font-size:12px;margin:0 0 15px;text-transform:uppercase;letter-spacing:.06em;color:var(--mute)}
.det-ic{display:flex;align-items:center;gap:13px;margin-bottom:17px}
.det-ic .big{width:48px;height:48px;border-radius:10px;display:grid;place-items:center;background:var(--soft);color:var(--accent);flex:none}
.det-name{font-weight:700;font-size:15px;overflow-wrap:anywhere;line-height:1.3}
dl.meta{display:grid;grid-template-columns:auto 1fr;gap:10px 14px;margin:0;font-size:13px}
dl.meta dt{color:var(--mute)}
dl.meta dd{margin:0;text-align:right;overflow-wrap:anywhere}
.pathv{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.btn{display:inline-flex;align-items:center;gap:8px;justify-content:center;width:100%;margin-top:17px;
 background:var(--accent);color:#fff;border:0;border-radius:9px;padding:12px;font:inherit;font-size:15px;font-weight:700;cursor:pointer}
.btn:hover{background:#a83809;color:#fff}
.btn.off{background:#cbbfb3;cursor:not-allowed;pointer-events:none}
.mtree{display:none}
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
.center{text-align:center}
.center h1{font-size:22px;margin:0 0 6px}
.center p{color:var(--mute);margin:0 0 16px}
@media (max-width:760px){
 .top{padding:0 14px;height:54px;gap:10px}
 .brand small{display:none}
 .storage{display:none}
 .app{grid-template-columns:1fr}
 .tree{display:none}
 .main{padding:14px}
 .cards{grid-template-columns:1fr 1fr}
 .mtree{display:block;margin-bottom:14px}
 .mtree summary{list-style:none;display:inline-flex;align-items:center;gap:8px;background:var(--panel);
  border:1px solid var(--line);border-radius:9px;padding:9px 13px;font-weight:650;font-size:13.5px;cursor:pointer}
 .mtree summary::-webkit-details-marker{display:none}
 .mtree .tree{display:block;border:0;background:transparent;padding:12px 2px 0}
 .work{grid-template-columns:1fr}
 .list .hd{display:none}
 .list .row{grid-template-columns:1fr;gap:5px;padding:13px 14px}
 .list .row .modif,.list .row .taille,.list .row .depose{display:none}
 .rowmeta{display:block;color:var(--mute);font-size:12.5px}
}
@media (max-width:420px){.cards{grid-template-columns:1fr}}
"""


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")


def head(title):
    return ("<!doctype html><html lang=fr><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>" + esc(title) + "</title><style>" + CSS + "</style></head><body>")


def fr_size(n):
    size = float(n)
    for unit in ("o", "Ko", "Mo"):
        if size < 1024 or unit == "Mo":
            return f"{size:.0f} {unit}" if unit == "o" else (f"{size:.1f} {unit}").replace(".", ",")
        size /= 1024


# --------------------------------------------------------------------------
# Content model. Each file: path (segments, last = filename), badge, type,
# uploader, date, time, and either a handout 'source' (served from HANDOUT_DIR)
# or decoy 'text' (generated inline).
# --------------------------------------------------------------------------
DEPT_ORDER = ["Direction de course", "Chronométrage", "Arbitrage", "Basis SAP", "IT", "Logistique"]


def ev(path, badge, typ, who, date, tm):
    return {"path": path, "name": path[-1], "source": path[-1], "badge": badge,
            "type": typ, "who": who, "date": date, "time": tm, "decoy": False}


def decoy(path, who, date, tm, text):
    return {"path": path, "name": path[-1], "source": None, "badge": "txt",
            "type": "Note interne", "who": who, "date": date, "time": tm, "decoy": True, "text": text}


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

FILES = [
    ev(("Chronométrage", "Captures", "timing_booth.pcap"), "pcap",
       "Capture réseau (PCAP)", "Équipe IT d'urgence", "1 nov. 2026", "22:14"),
    ev(("Arbitrage", "Pièces", "referee_usb.img"), "img",
       "Image disque brute", "Arbitrage", "1 nov. 2026", "20:03"),
    ev(("Basis SAP", "Exports", "SAP_USR02_export.csv"), "csv",
       "CSV · export de table", "Basis SAP", "1 nov. 2026", "09:12"),
    ev(("Basis SAP", "Exports", "sap_hint.txt"), "txt",
       "Note d'export", "Basis SAP", "1 nov. 2026", "09:15"),
    ev(("IT", "Outils", "wordlist.txt"), "txt",
       "Liste de mots", "Équipe IT d'urgence", "31 oct. 2026", "17:40"),
    ev(("Direction de course", "Dossier incident", "case_file.zip"), "zip",
       "Archive chiffrée", "Direction de course", "2 nov. 2026", "08:05"),
    ev(("IT", "Sauvegardes postes", "portable-equipe-03", "dflop_erp.sap"), "sap",
       "Raccourci SAP GUI", "Équipe IT d'urgence", "30 oct. 2026", "11:20"),
    ev(("Basis SAP", "Développements", "ZDFLOP_RESULT_EXPORT.abap"), "abap",
       "Source ABAP", "Basis SAP", "28 oct. 2026", "16:48"),
    # --- mundane decoys (generated text, no clues) ---
    decoy(("IT", "Outils", "LISEZ-MOI.txt"), "Équipe IT d'urgence", "31 oct. 2026", "17:41", _LISEZMOI),
    decoy(("Logistique", "Bénévoles", "planning_benevoles.txt"), "Logistique", "28 oct. 2026", "14:05", _PLANNING),
    decoy(("Direction de course", "Dossier incident", "note_parcours.txt"),
          "Direction de course", "30 oct. 2026", "10:22", _NOTE_PARCOURS),
    decoy(("Arbitrage", "Pièces", "consignes_jury.txt"), "Arbitrage", "29 oct. 2026", "09:30", _CONSIGNES),
]
FILES_BY_PATH = {f["path"]: f for f in FILES}

MONTHS = {"janv.": 1, "févr.": 2, "mars": 3, "avr.": 4, "mai": 5, "juin": 6,
          "juil.": 7, "août": 8, "sept.": 9, "oct.": 10, "nov.": 11, "déc.": 12}


def date_key(ds):
    p = ds.split()
    try:
        return (int(p[2]), MONTHS.get(p[1], 0), int(p[0]))
    except (IndexError, ValueError):
        return (0, 0, 0)


def build_tree():
    root = {"name": "Partage DFlop", "path": (), "children": {}, "files": []}
    for f in FILES:
        node = root
        for i, s in enumerate(f["path"][:-1]):
            node = node["children"].setdefault(
                s, {"name": s, "path": f["path"][:i + 1], "children": {}, "files": []})
        node["files"].append(f)
    return root


TREE = build_tree()


def child_folders(node):
    kids = list(node["children"].values())
    if node["path"] == ():
        kids.sort(key=lambda n: DEPT_ORDER.index(n["name"]) if n["name"] in DEPT_ORDER else 99)
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


def latest_date(node):
    fs = descendant_files(node)
    return max(fs, key=lambda f: date_key(f["date"]))["date"] if fs else ""


def folder_href(path):
    return "/" if not path else "/d/" + "/".join(quote(s) for s in path)


def is_available(f):
    if f["decoy"]:
        return True
    return os.path.isfile(os.path.join(HANDOUT_DIR, f["source"]))


def file_size(f):
    if f["decoy"]:
        return fr_size(len(f["text"].encode("utf-8")))
    p = os.path.join(HANDOUT_DIR, f["source"])
    return fr_size(os.path.getsize(p)) if os.path.isfile(p) else None


def elements_label(n):
    return str(n) + (" élément" if n == 1 else " éléments")


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def render_items(node, current):
    lis = []
    for f in child_folders(node):
        on_path = current[:len(f["path"])] == f["path"]
        active = f["path"] == current
        has_sub = bool(f["children"])
        if has_sub and on_path:
            chev = "&#9662;"
        elif has_sub:
            chev = "&#9656;"
        else:
            chev = "&nbsp;"
        cls = "node active" if active else "node"
        li = ('<li><a class="' + cls + '" href="' + folder_href(f["path"]) + '">'
              '<span class="chev">' + chev + '</span>' + FOLDER +
              '<span class="nm">' + esc(f["name"]) + '</span></a>')
        if on_path and has_sub:
            li += '<ul>' + render_items(f, current) + '</ul>'
        li += '</li>'
        lis.append(li)
    return "".join(lis)


def page(title, current, body):
    inner = '<ul>' + render_items(TREE, current) + '</ul>'
    sidebar = '<nav class="tree"><h3>Dossiers</h3>' + inner + '</nav>'
    mtree = ('<details class="mtree"><summary>' + FOLDER + 'Dossiers</summary>'
             '<nav class="tree">' + inner + '</nav></details>')
    return (head(title) + topbar() + '<div class="app">' + sidebar +
            '<main class="main">' + mtree + body + '</main></div></body></html>')


def topbar():
    total = 0
    for f in FILES:
        if f["decoy"]:
            total += len(f["text"].encode("utf-8"))
        else:
            p = os.path.join(HANDOUT_DIR, f["source"])
            if os.path.isfile(p):
                total += os.path.getsize(p)
    pct = max(3, min(100, round(total / (20 * 1024 * 1024) * 100)))
    user = esc(session.get("user", SHARE_USER))
    return ('<header class="top"><div class="brand"><span class="logo">' + LOGO + '</span>'
            '<span>Partage DFlop<small>espace documentaire interne</small></span></div>'
            '<div class="top-right"><div class="storage">'
            '<span class="bar"><i style="width:' + str(pct) + '%"></i></span>'
            '<span>' + fr_size(total) + ' utilisés</span></div>'
            '<div class="user"><span class="avatar">IT</span><span>' + user + '</span>'
            '<a class="logout" href="/logout">Déconnexion</a></div></div></header>')


def breadcrumbs(segs):
    parts = ['<a href="/">Partage DFlop</a>']
    for i, s in enumerate(segs):
        if i == len(segs) - 1:
            parts.append('<span class="cur">' + esc(s) + '</span>')
        else:
            parts.append('<a href="' + folder_href(segs[:i + 1]) + '">' + esc(s) + '</a>')
    return '<div class="crumb">' + '<span class="sep">/</span>'.join(parts) + '</div>'


def folder_row(sub):
    cnt = len(sub["children"]) + len(sub["files"])
    el = elements_label(cnt)
    d = latest_date(sub)
    return ('<a class="row" href="' + folder_href(sub["path"]) + '">'
            '<div class="fname">' + FOLDER + '<span class="nm">' + esc(sub["name"]) + '</span></div>'
            '<div class="muted modif">' + d + '</div>'
            '<div class="muted taille">' + el + '</div>'
            '<div class="muted depose"></div>'
            '<div class="rowmeta">' + el + ' · ' + d + '</div></a>')


def file_row(f, selected):
    cls = "row sel" if f["name"] == selected else "row"
    size = file_size(f)
    if size is not None:
        sizecell = '<div class="muted taille">' + size + '</div>'
        meta = size + ' · ' + esc(f["who"]) + ' · ' + f["date"]
    else:
        sizecell = '<div class="muted taille na">pas encore disponible</div>'
        meta = 'pas encore disponible · ' + esc(f["who"])
    return ('<a class="' + cls + '" href="?f=' + quote(f["name"]) + '">'
            '<div class="fname"><span class="badge b-' + f["badge"] + '">' + esc(f["badge"]) + '</span>'
            '<span class="nm">' + esc(f["name"]) + '</span></div>'
            '<div class="muted modif">' + f["date"] + '</div>' + sizecell +
            '<div class="muted depose">' + esc(f["who"]) + '</div>'
            '<div class="rowmeta">' + meta + '</div></a>')


def render_list(node, selected):
    rows = [folder_row(s) for s in child_folders(node)]
    rows += [file_row(f, selected) for f in node["files"]]
    hd = ('<div class="hd"><span>Nom</span><span>Modifié le</span><span>Taille</span>'
          '<span>Déposé par</span></div>')
    return '<div class="list">' + hd + "".join(rows) + '</div>'


def render_details(node, selected):
    if not node["files"]:
        return ""
    f = next((x for x in node["files"] if x["name"] == selected), node["files"][0])
    avail = is_available(f)
    size = file_size(f) or "—"
    pathstr = " / ".join(esc(s) for s in f["path"])
    date = f["date"] + (", " + f["time"] if f.get("time") else "")
    if avail:
        dlhref = "/telecharger/" + "/".join(quote(s) for s in f["path"])
        btn = '<a class="btn" href="' + dlhref + '">' + DL + ' Télécharger</a>'
    else:
        btn = '<span class="btn off">' + DL + ' Pas encore disponible</span>'
    meta = [("Type", esc(f["type"])), ("Taille", size), ("Déposé par", esc(f["who"])),
            ("Date", date), ("Chemin", '<span class="pathv">' + pathstr + '</span>')]
    dl = "".join('<dt>' + k + '</dt><dd>' + v + '</dd>' for k, v in meta)
    return ('<aside class="panelcard"><h2>Détails</h2>'
            '<div class="det-ic"><span class="big">' + FILE_BIG + '</span>'
            '<span class="det-name">' + esc(f["name"]) + '</span></div>'
            '<dl class="meta">' + dl + '</dl>' + btn + '</aside>')


# --------------------------------------------------------------------------
# Auth (the login is not a puzzle — the hub hands out the crew account)
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
    body = (head("Connexion · Partage DFlop") +
            '<div class="login-wrap"><div class="login-card">'
            '<div class="brand"><span class="logo">' + LOGO + '</span><span>Partage DFlop</span></div>'
            '<p class="tag">espace documentaire interne</p>'
            '<form method="post" action="/login">' + err +
            '<div class="fld"><label for="u">Identifiant</label>'
            '<input id="u" name="identifiant" placeholder="equipe-it" autocomplete="username"></div>'
            '<div class="fld"><label for="p">Mot de passe</label>'
            '<input id="p" name="motdepasse" type="password" autocomplete="current-password"></div>'
            '<button class="btn" type="submit">Se connecter</button></form>'
            '<p class="note">Accès réservé au personnel DécaFlop et à l\'équipe IT d\'urgence. '
            'Identifiants fournis par la cellule de crise.</p>'
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


@app.get("/")
def root():
    tiles = []
    for d in child_folders(TREE):
        cnt = len(d["children"]) + len(d["files"])
        tiles.append('<a class="folder" href="' + folder_href(d["path"]) + '">'
                     '<div class="fic">' + FOLDER_BIG + '</div>'
                     '<div class="fn">' + esc(d["name"]) + '</div>'
                     '<div class="fm">' + elements_label(cnt) + ' · modifié le ' + latest_date(d) + '</div></a>')
    n = len(child_folders(TREE))
    body = ('<div class="crumb"><span class="cur">Partage DFlop</span></div>'
            '<h1 class="page">Partage DFlop</h1>'
            '<p class="psub">Documents internes par service. ' + str(n) + ' services.</p>'
            '<div class="cards">' + "".join(tiles) + '</div>')
    return html(page("Partage DFlop", (), body))


@app.get("/d/<path:subpath>")
def folder(subpath):
    segs = tuple(s for s in subpath.split("/") if s)
    node = get_node(segs)
    if node is None or node["path"] == ():
        abort(404)
    selected = request.args.get("f", "")
    nd, nf = len(child_folders(node)), len(node["files"])
    bits = []
    if nd:
        bits.append(str(nd) + (" dossier" if nd == 1 else " dossiers"))
    if nf:
        bits.append(str(nf) + (" fichier" if nf == 1 else " fichiers"))
    psub = " · ".join(bits) if bits else "Dossier vide"
    listing = render_list(node, selected)
    details = render_details(node, selected)
    work = ('<div class="work">' + listing + details + '</div>') if details else listing
    body = (breadcrumbs(segs) + '<h1 class="page">' + esc(node["name"]) + '</h1>'
            '<p class="psub">' + psub + '</p>' + work)
    return html(page(node["name"] + " · Partage DFlop", node["path"], body))


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
    body = (head("Introuvable · Partage DFlop") + topbar() +
            '<div class="app"><nav class="tree"><h3>Dossiers</h3><ul>' +
            render_items(TREE, ()) + '</ul></nav>'
            '<main class="main"><div class="center" style="padding:48px 0">'
            '<h1 class="page">Introuvable</h1>'
            '<p class="psub">Ce dossier ou ce fichier n\'existe pas.</p>'
            '<a class="btn" style="max-width:220px" href="/">Retour à l\'accueil</a>'
            '</div></main></div></body></html>')
    return html(body, 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
