"""
Intranet DécaFlop — shared page chrome for every internal tool.

IDENTICAL copies live next to app.py in share/app and in challenges 01, 04, 06,
10, 12 and 14 (each Docker build only sees its own app/ folder). The stylesheet
is static/intranet.css. tests/test_intranet_assets.py fails if any copy drifts:
edit one, then copy it to the others.

Links to the other tools reuse the host the player typed, with each tool's
fixed port (same rule as the hub). The Applications menu lists the regular
internal tools only. It never links the staff portal or the hub.

Online (Cloudflare Tunnel, see CLOUDFLARE.md) every tool has its own
subdomain instead of a port: when the player's host is <lab-label>.<domain>
(e.g. share.ctf.example.com), links go to <tool's subdomain>.<domain> on the
same scheme. An IP or any other host keeps the host:port rule, so the offline
Pi is unaffected.
"""
from html import escape as esc

from flask import request

# key: (port, label, one-line description)
APPS = {
    "intranet": (8020, "Intranet DécaFlop", "Actualités, documents, annuaire"),
    "athletes": (8004, "Espace athlètes", "Dossards, vagues, parc à vélos"),
    "resultats": (8006, "Admin résultats", "Saisie et validation des classements"),
    "api": (8010, "Results API", "API des résultats (JSON, v2)"),
    "chrono": (8011, "Chronométrage", "Temps intermédiaires de la finale"),
    "certificats": (8012, "Certificats de finaliste", "Génération et impression"),
    "sapgw": (8014, "Gateway SAP (SMGW)", "Moniteur du gateway DFL"),
}
# Online subdomain of each tool (same names as the hub's links and CLOUDFLARE.md)
SUBDOMAIN = {"intranet": "share", "athletes": "idor", "resultats": "sqli", "api": "jwt",
             "chrono": "git", "certificats": "ssti", "sapgw": "sapgw"}
LAB_LABELS = {"site", "share", "idor", "sqli", "jwt", "git", "ssti", "sapgw",
              "hub", "ctfd", "cyberchef", "terminal"}
ORDER = ["intranet", "athletes", "resultats", "api", "chrono", "certificats", "sapgw"]
CUR = ' aria-current="page"'

_I = {
    "folder": '<path d="M1 3.5h5l1.5 1.5H15v8.5H1z" fill="#f2c55c" stroke="#c9952b" stroke-width=".8"/>'
              '<path d="M1 6.2h14" stroke="#dca63a" stroke-width=".8"/>',
    "txt": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#8a8a8a" stroke-width=".8"/>'
           '<path d="M9.5 1.5V5H13" fill="#e9e9e9" stroke="#8a8a8a" stroke-width=".8"/>'
           '<path d="M5 7.5h6M5 9.5h6M5 11.5h4" stroke="#9a9a9a" stroke-width=".8"/>',
    "csv": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#1d6f42" stroke-width=".8"/>'
           '<path d="M9.5 1.5V5H13" fill="#d6eadf" stroke="#1d6f42" stroke-width=".8"/>'
           '<rect x="4.5" y="7" width="7" height="5.5" fill="none" stroke="#1d6f42" stroke-width=".7"/>'
           '<path d="M4.5 8.8h7M4.5 10.6h7M7 7v5.5" stroke="#1d6f42" stroke-width=".7"/>',
    "zip": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#8a6d1f" stroke-width=".8"/>'
           '<path d="M9.5 1.5V5H13" fill="#f3e6c2" stroke="#8a6d1f" stroke-width=".8"/>'
           '<path d="M7 2v1.2h1.2v1.2H7v1.2h1.2v1.2H7v1.2" fill="none" stroke="#8a6d1f" stroke-width=".9"/>'
           '<rect x="6.4" y="9" width="2.4" height="3" fill="#f2c55c" stroke="#8a6d1f" stroke-width=".7"/>',
    "img": '<rect x="1.5" y="2.5" width="13" height="11" fill="#fff" stroke="#6b3fa0" stroke-width=".8"/>'
           '<rect x="3.5" y="5" width="9" height="4.2" fill="#e5dcf2" stroke="#6b3fa0" stroke-width=".6"/>'
           '<path d="M3.5 11h9" stroke="#6b3fa0" stroke-width=".8"/><circle cx="11.6" cy="11" r=".7" fill="#6b3fa0"/>',
    "pcap": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#0f6b73" stroke-width=".8"/>'
            '<path d="M9.5 1.5V5H13" fill="#d3ecee" stroke="#0f6b73" stroke-width=".8"/>'
            '<path d="M4.5 11.5l1.5-3 1.5 2 1.5-4 1.5 5" fill="none" stroke="#0f6b73" stroke-width=".9"/>',
    "sap": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#2a52be" stroke-width=".8"/>'
           '<path d="M9.5 1.5V5H13" fill="#dbe4f8" stroke="#2a52be" stroke-width=".8"/>'
           '<rect x="4.3" y="7.3" width="7.4" height="4.6" fill="#2a52be"/>'
           '<path d="M5.4 9.6h2.2M8.6 8.6l1.4 1-1.4 1" fill="none" stroke="#fff" stroke-width=".8"/>',
    "abap": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#9a4a24" stroke-width=".8"/>'
            '<path d="M9.5 1.5V5H13" fill="#f3e1d6" stroke="#9a4a24" stroke-width=".8"/>'
            '<path d="M6.6 7.6 5 9.6l1.6 2M9.4 7.6l1.6 2-1.6 2" fill="none" stroke="#9a4a24" stroke-width=".9"/>',
    "page": '<path d="M3 1.5h6.5L13 5v9.5H3z" fill="#fff" stroke="#0072c6" stroke-width=".8"/>'
            '<path d="M9.5 1.5V5H13" fill="#deecf9" stroke="#0072c6" stroke-width=".8"/>'
            '<path d="M5 8h6M5 10h6M5 12h3" stroke="#0072c6" stroke-width=".8"/>',
    "user": '<circle cx="8" cy="5.4" r="2.9" fill="#deecf9" stroke="#0072c6" stroke-width=".9"/>'
            '<path d="M2.5 14.2c.6-3 2.8-4.6 5.5-4.6s4.9 1.6 5.5 4.6z" fill="#deecf9" stroke="#0072c6" stroke-width=".9"/>',
    "search": '<circle cx="6.5" cy="6.5" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/>'
              '<path d="M10 10l4.5 4.5" stroke="currentColor" stroke-width="1.7"/>',
}
SPRITE = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">' +
          "".join(f'<symbol id="i-{k}" viewBox="0 0 16 16">{v}</symbol>' for k, v in _I.items()) +
          '</svg>')


def icon(name, label=""):
    aria = f' role="img" aria-label="{esc(label)}"' if label else ' aria-hidden="true"'
    return f'<svg width="16" height="16"{aria}><use href="#i-{name}"/></svg>'


def host():
    h = request.host
    return h.rsplit(":", 1)[0] if not h.endswith("]") else h


def lab_domain():
    """The online base domain if the player came in via <lab-label>.<domain>, else ""."""
    labels = host().lower().split(".")
    if len(labels) >= 3 and labels[0] in LAB_LABELS and not labels[-1].isdigit():
        return ".".join(labels[1:])
    return ""


def app_url(key, path="/", current=None):
    """Link to another tool on the player's host; relative inside the current one."""
    if key == current:
        return path
    domain = lab_domain()
    if domain:                      # online: one subdomain per tool, behind the tunnel
        proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip()
        scheme = proto if proto in ("http", "https") else request.scheme
        return f"{scheme}://{SUBDOMAIN[key]}.{domain}{path}"
    return f"http://{host()}:{APPS[key][0]}{path}"


def head(title):
    return ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><link rel="stylesheet" href="/static/intranet.css">'
            '</head><body>')


def _apps_menu(current):
    items = []
    for key in ORDER:
        _port, label, desc = APPS[key]
        items.append(f'<li><a href="{esc(app_url(key, "/", current))}"><b>{esc(label)}</b>'
                     f'<small>{esc(desc)}</small></a></li>')
        if key == "intranet":
            items.append('<li class="sep"></li>')
    return ('<details class="apps"><summary>Applications</summary><ul>' + "".join(items) +
            '</ul></details>')


def suite(current, suite_on=None, user=None, logout=None):
    def link(path, label, key):
        cur = CUR if suite_on == key else ""
        return f'<a href="{esc(app_url("intranet", path, current))}"{cur}>{label}</a>'
    if user:
        words = [w for w in user.replace("-", " ").replace(".", " ").split() if w[0].isalpha()]
        ini = "".join(w[0] for w in words[:2]).upper() or "?"
        out = f'<a href="{esc(logout)}">Déconnexion</a>' if logout else ""
        me = (f'<span class="me"><span class="ini" aria-hidden="true">{esc(ini)}</span>'
              f'<span class="nm">{esc(user)}</span>{out}</span>')
    else:
        me = (f'<span class="me"><a href="{esc(app_url("intranet", "/login", current))}">'
              'Se connecter</a></span>')
    return ('<div class="suite"><a class="brand" href="' + esc(app_url("intranet", "/", current)) +
            '">DécaFlop <span>Intranet</span></a><nav class="suite-nav" aria-label="Intranet">' +
            link("/", "Actualités", "news") + link("/documents", "Partage", "docs") +
            link("/annuaire", "Annuaire", "dir") +
            link("/wiki", "Documentation Technique", "wiki") + _apps_menu(current) + '</nav>' + me +
            f'<a class="ic" href="{esc(app_url("intranet", "/aide", current))}" title="Aide">?</a></div>')


def ribbon(tabs, on=0, right=()):
    t = "".join(f'<span class="on">{esc(x)}</span>' if i == on else f'<span>{esc(x)}</span>'
                for i, x in enumerate(tabs))
    r = "".join(f'<span>{x}</span>' for x in right)
    return f'<div class="ribbon" aria-hidden="true">{t}<span class="r">{r}</span></div>'


def site(title, href="/", logo="DF", topnav=(), search=None):
    nav = "".join(f'<a href="{esc(h)}"{CUR if cur else ""}>{esc(lbl)}</a>' for h, lbl, cur in topnav)
    nav = f'<nav class="topnav" aria-label="Site">{nav}</nav>' if nav else ""
    return (f'<header class="site"><a class="site-logo" href="{esc(href)}" aria-hidden="true" tabindex="-1">'
            f'{esc(logo)}</a><div><div class="site-title"><a href="{esc(href)}">{esc(title)}</a></div>{nav}</div>'
            f'{search or ""}</header>')


def search_box(action, placeholder, value="", name="q", cls="sitesearch"):
    return (f'<form class="{cls}" role="search" method="get" action="{esc(action)}">'
            f'<label class="sr" for="{cls}-q">{esc(placeholder)}</label>'
            f'<input id="{cls}-q" name="{esc(name)}" value="{esc(value)}" placeholder="{esc(placeholder)}">'
            f'<button type="submit" title="Rechercher">{icon("search")}</button></form>')


def footer(product, extra=""):
    bits = ["Direction des Systèmes d'Information", "Assistance au poste 300"]
    if extra:
        bits.append(extra)
    return ('<footer class="foot">' + "".join(f"<span>{b}</span>" for b in bits) +
            f'<span class="ver">{esc(product)}</span></footer>')


def page(title, body, *, app, site_title, site_href="/", logo="DF", topnav=(), quick=None,
         tabs=None, tab_on=0, tabs_right=(), search=None, user=None, logout=None, suite_on=None,
         product="", foot_extra="", scripts=""):
    """A full intranet page. `quick` is the quick-launch <ul> (also shown as a
    collapsible menu on phones); without it the body uses the full width."""
    if quick:
        side = (f'<nav class="ql" aria-label="Navigation">{quick}</nav>')
        mnav = f'<details class="mnav"><summary>Navigation</summary>{quick}</details>'
        bodyhtml = f'<div class="body">{side}<main class="main" id="main">{mnav}{body}</main></div>'
    else:
        bodyhtml = f'<div class="body wide"><main class="main" id="main">{body}</main></div>'
    rib = ribbon(tabs, tab_on, tabs_right) if tabs else ""
    return (head(title) + SPRITE + suite(app, suite_on, user, logout) + rib +
            site(site_title, site_href, logo, topnav, search) + bodyhtml +
            footer(product, foot_extra) + scripts + '</body></html>')


# Copy button for codes shown on a page. Falls back to execCommand because the
# Pi is served over plain HTTP on a LAN IP, where navigator.clipboard is off.
COPY_JS = """<script>
function copyCode(b){var t=b.parentNode.querySelector('code').textContent.trim();
 function ok(){b.textContent='Copié';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""


def codebox(value, code_id="flag"):
    """A read-only value (escaped) with a Copier button."""
    return (f'<div class="codebox"><code id="{esc(code_id)}">{esc(value)}</code>'
            '<button type="button" onclick="copyCode(this)">Copier</button></div>')
