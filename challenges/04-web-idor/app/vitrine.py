"""
The public DécaFlop look for the two athlete-facing apps: 04 (Espace athlètes)
and 12 (Certificats de finaliste). Competitors reach them from the DécaFlop
site's championship page, so they wear the site's own header and footer (the
staff intranet chrome, with its Partage / Annuaire / Applications bar, is for
the internal tools only). Every link in the header and the footer points back
to the DécaFlop site (:8001, or site.<domain> online, same rule as fab.py).

IDENTICAL copies live in challenges/04-web-idor/app and
challenges/12-web-ssti/app, each with static/decaflop.css (a copy of the
site's, challenges/01-web-staff/app/static/decaflop.css) and static/vitrine.css
next to it (each Docker build only sees its own app/ folder).
tests/test_vitrine.py fails if a copy drifts or the header stops matching the
site's (shop.NAV): edit one, then copy it to the other.
"""
from html import escape as esc

import fab

# Same sections, same order as the site's header (shop.NAV).
NAV = [("/natation", "Natation"), ("/velo", "Vélo"), ("/course-a-pied", "Course à pied"),
       ("/triathlon", "Triathlon"), ("/magasins", "Magasins"), ("/destockage", "Déstockage")]

_UI = {   # same strokes as the site's icons.py
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20.5 20.5 16 16"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.3 4.2-6.5 8-6.5s7 2.2 8 6.5"/>',
    "bag": '<path d="M5 8h14l-1 13H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
}


def ui(name, size=24):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
            f'focusable="false">{_UI[name]}</svg>')


def site(path="/"):
    """Address of a page of the DécaFlop site, as the player's browser reaches it."""
    return fab.url("site").rstrip("/") + path


def crumbs(*items):
    """Breadcrumb starting on the site (Accueil > Triathlon), then this app's items
    (href or None for the current page)."""
    items = ((site("/"), "Accueil"), (site("/triathlon"), "Triathlon")) + items
    parts = [f'<a href="{esc(h)}">{t}</a>' if h else f"<span>{t}</span>" for h, t in items]
    return ('<nav class="crumb" aria-label="Fil d\'Ariane">' +
            '<span class="sep" aria-hidden="true"></span>'.join(parts) + "</nav>")


def page_head(title, lead="", trail=(), crumb=None):
    """Breadcrumb + h1 (+ lead). `title` may hold markup (a tag); `crumb` is the
    plain label for the breadcrumb, `title` by default."""
    return (f'<section class="page-hd"><div class="in">{crumbs(*trail, (None, crumb or title))}'
            f'<h1>{title}</h1>{"<p>" + lead + "</p>" if lead else ""}</div></section>')


def footer():
    cols = [
        ("Aide", [("/aide#commande", "Suivi de commande"), ("/aide#retours", "Retours et échanges"),
                  ("/aide#garantie", "Garantie"), ("/aide#tailles", "Guide des tailles")]),
        ("Services", [("/aide#retrait", "Retrait en magasin"), ("/location", "Location de vélos"),
                      ("/atelier", "Atelier vélo"), ("/destockage", "Déstockage")]),
        ("Magasins", [("/magasins", "Tous nos magasins"), ("/magasins", "Horaires du week-end")]),
        ("Le championnat", [("/triathlon", "Programme de la course"), ("/triathlon#athletes", "Espace athlètes"),
                            ("/actualites", "Actualités"), ("/presse", "Espace presse")]),
    ]
    c = "".join(f'<div><h3>{t}</h3><ul>' + "".join(f'<li><a href="{esc(site(h))}">{x}</a></li>'
                                                    for h, x in items) + '</ul></div>' for t, items in cols)
    legal = "".join(f'<a href="{esc(site("/informations-legales#" + k))}">{x}</a>' for k, x in (
        ("mentions", "Mentions légales"), ("cgv", "Conditions générales de vente"), ("cookies", "Cookies"),
        ("accessibilite", "Accessibilité partiellement conforme")))
    return ('<footer class="foot"><div class="in cols">' + c +
            '<div><h3>Service client</h3><p class="tel">0 800 FLOP FLOP</p>'
            '<p>Du lundi au vendredi, de 9 h à 18 h. Service et appel gratuits.</p></div></div>'
            '<div class="in legal"><span>© 2026 DécaFlop SAS</span>'
            f'<nav aria-label="Informations légales">{legal}</nav></div></footer>')


def page(title, body, *, portal, tabs=(), user=None, logout=None, scripts=""):
    """A full page: the site's header (Triathlon highlighted), a bar naming this
    space (`portal`) with its `tabs` [(href, label, current)], `body`, the
    site's footer. `user`/`logout` show who is signed in (escaped)."""
    nav = "".join(f'<a href="{esc(site(h))}"{" aria-current=\"page\"" if h == "/triathlon" else ""}>{label}</a>'
                  for h, label in NAV)
    tabs_html = "".join(f'<a href="{esc(h)}"{" aria-current=\"page\"" if on else ""}>{esc(label)}</a>'
                        for h, label, on in tabs)
    who = ""
    if user:
        who = f'<span class="who">{esc(user)}'
        if logout:
            who += f' <a href="{esc(logout)}">Se déconnecter</a>'
        who += "</span>"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><link rel="stylesheet" href="/static/decaflop.css">
<link rel="stylesheet" href="/static/vitrine.css"></head><body>
<a class="skip" href="#main">Aller au contenu</a>
<header class="hd"><div class="in">
<a class="mark" href="{esc(site("/"))}">DÉCA<i>FLOP</i></a>
<nav class="nav" aria-label="Rayons">{nav}</nav>
<form class="search" action="{esc(site("/"))}" role="search">{ui("search", 18)}<input name="q"
 aria-label="Rechercher" placeholder="Rechercher"></form>
<nav class="acct" aria-label="Mon espace"><a href="{esc(site("/compte"))}">{ui("user", 20)}<span>Compte</span></a>
<a href="{esc(site("/panier"))}">{ui("bag", 20)}<span>Panier (0)</span></a></nav>
</div></header>
<div class="portal"><div class="in"><span class="pname">{esc(portal)}</span>
<nav aria-label="{esc(portal)}">{tabs_html}</nav>{who}</div></div>
<main id="main">{body}</main>
{footer()}
{scripts}
</body></html>"""


def codebox(value, code_id="flag"):
    """A read-only value (escaped) with a Copier button (needs COPY_JS)."""
    return (f'<div class="codebox"><code id="{esc(code_id)}">{esc(value)}</code>'
            '<button type="button" class="btn line" onclick="copyCode(this)">Copier</button></div>')


COPY_JS = """<script>
function copyCode(b){var t=b.parentNode.querySelector('code').textContent.trim();
 function ok(){b.textContent='Copié';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}document.body.removeChild(a)}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}else{legacy()}}
</script>"""
