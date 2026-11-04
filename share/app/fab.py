"""
Floating shortcuts in the bottom-right corner of the hub, the DécaFlop site and
the Intranet DécaFlop share. They are a game layer on top of the story: the
same "dossard" (race bib) look on all three apps.

IDENTICAL copies live in hub/app, challenges/01-web-staff/app and share/app,
each with static/fab.css next to it (each Docker build only sees its own app/
folder). tests/test_fab.py fails if any copy drifts: edit one, then copy it to
the others.

What each app shows (round buttons, left to right, the main one last):
- hub:   [Intranet]  Outils  Site DécaFlop
- site:  [Intranet]  Outils  Cellule de crise
- share: Site DécaFlop  Outils  Cellule de crise
[Intranet] appears only once the player has logged in to the share: the share
sets COOKIE (mark_intranet). Cookies ignore ports, so offline the hub (:8080)
and the site (:8001) read the cookie the share (:8020) set on the same host.
Online (Cloudflare Tunnel) the share sets it on the parent domain, so
hub.<domain> and site.<domain> get it too. Logging out keeps it.

Outils opens a small menu: CyberChef, the team terminal and the hub's Outils
tab. Without JavaScript the button is a plain link to that tab.

Addresses follow the hub's rule: <KEY>_URL if set, else the player's host on
the service's port; online, <subdomain>.<domain> when the player came in on a
lab subdomain (same names as CLOUDFLARE.md).
"""
import os
from html import escape

from flask import request

COOKIE = "dflop_intranet"
MAX_AGE = 30 * 24 * 60 * 60
CSS = '<link rel="stylesheet" href="/static/fab.css">'

# key: (override env, offline port, online subdomain)
SERVICES = {
    "hub": ("HUB_URL", 8080, "hub"),
    "site": ("SITE_URL", 8001, "site"),
    "share": ("SHARE_URL", 8020, "share"),
    "cyberchef": ("CYBERCHEF_URL", 8090, "cyberchef"),
    "terminal": ("TERMINAL_URL", 8091, "terminal"),
}
LAB_LABELS = {"site", "share", "idor", "sqli", "jwt", "git", "ssti", "sapgw",
              "hub", "ctfd", "cyberchef", "terminal"}

_SVG = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{p}</svg>'
_PATHS = {
    "site": '<path d="M5 8h14l-1.2 12H6.2z" fill="none" stroke="currentColor" stroke-width="1.9" '
            'stroke-linejoin="round"/><path d="M9 10V7a3 3 0 0 1 6 0v3" fill="none" stroke="currentColor" '
            'stroke-width="1.9" stroke-linecap="round"/>',
    "hub": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5" fill="none" stroke="currentColor" '
           'stroke-width="1.9"/><path d="M3.5 9.5h17M3.5 14.5h17M9.5 4.5v15" stroke="currentColor" stroke-width="1.7"/>',
    "share": '<path d="M3 6.5h6l2 2h10v10.5H3z" fill="none" stroke="currentColor" stroke-width="1.9" '
             'stroke-linejoin="round"/><path d="M3 11h18" stroke="currentColor" stroke-width="1.7"/>',
    "tools": '<path d="M14.7 6.3a4 4 0 0 0-5.2 5.2L4 17v3h3l5.5-5.5a4 4 0 0 0 5.2-5.2l-2.4 2.4-2.6-.6-.6-2.6z" '
             'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/>',
    "cyberchef": '<path d="M7 14.5c-2.2 0-3.5-1.6-3.5-3.4 0-1.9 1.5-3.3 3.3-3.3.5-2.2 2.6-3.8 5.2-3.8s4.7 1.6 '
                 '5.2 3.8c1.8 0 3.3 1.4 3.3 3.3 0 1.8-1.3 3.4-3.5 3.4V19H7z" fill="none" stroke="currentColor" '
                 'stroke-width="1.9" stroke-linejoin="round"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="2" fill="none" stroke="currentColor" '
                'stroke-width="1.9"/><path d="M7 9.5l3 2.5-3 2.5M12 15h5" fill="none" stroke="currentColor" '
                'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>',
    "ext": '<path d="M9 4.5H4.5v15h15V15M13.5 3.8h6.7v6.7M20.2 3.8l-9 9" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
}

# key: (tooltip / name, aria-label)
LABELS = {
    "hub": ("Cellule de crise", "Ouvrir la cellule de crise"),
    "site": ("Site DécaFlop", "Ouvrir le site DécaFlop"),
    "share": ("Intranet DécaFlop", "Ouvrir l'Intranet DécaFlop"),
}
TOOLS = [("cyberchef", "CyberChef", "Décoder, convertir, analyser"),
         ("terminal", "Terminal d'équipe", "Shell Linux, outils installés")]
# here: (main button, small button, small button needs the intranet cookie)
LAYOUT = {"hub": ("site", "share", True), "site": ("hub", "share", True), "share": ("hub", "site", False)}


def _icon(name, size=20):
    return _SVG.format(s=size, p=_PATHS[name])


def _host():
    h = request.host
    return h.rsplit(":", 1)[0] if not h.endswith("]") else h


def lab_domain():
    """The online base domain if the player came in via <lab-label>.<domain>, else ""."""
    labels = _host().lower().split(".")
    if len(labels) >= 3 and labels[0] in LAB_LABELS and not labels[-1].isdigit():
        return ".".join(labels[1:])
    return ""


def url(key):
    """Address of a lab service as the player's browser reaches it."""
    env, port, sub = SERVICES[key]
    override = os.environ.get(env, "").strip()
    if override:
        return override.rstrip("/") + "/"
    domain = lab_domain()
    if domain:
        proto = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip()
        scheme = proto if proto in ("http", "https") else request.scheme
        return f"{scheme}://{sub}.{domain}/"
    return f"http://{_host()}:{port}/"


def default_urls():
    return {k: url(k) for k in SERVICES}


def intranet_unlocked():
    return request.cookies.get(COOKIE) == "1"


def mark_intranet(resp):
    """Remember (in the player's browser) that they have logged in to the share."""
    resp.set_cookie(COOKIE, "1", max_age=MAX_AGE, path="/", samesite="Lax", httponly=True,
                    domain=lab_domain() or None)
    return resp


def render(here, urls):
    """The shortcuts for app `here` ("hub", "site" or "share"). `urls` maps the
    SERVICES keys to addresses; an empty address leaves that entry out."""
    main_key, small_key, gated = LAYOUT[here]
    buttons = []
    small_url = urls.get(small_key, "")
    if small_url and (intranet_unlocked() or not gated):
        name, aria = LABELS[small_key]
        new = ' data-dfab-new="intranet"' if small_key == "share" else ""
        buttons.append(f'<a class="dfab-btn" href="{escape(small_url)}" aria-label="{escape(aria)}"{new}>'
                       f'{_icon(small_key, 18)}<span class="dfab-tip" aria-hidden="true">{escape(name)}</span></a>')
    all_tools = "/outils" if here == "hub" else (urls.get("hub", "") + "outils" if urls.get("hub") else "")
    items = "".join(
        f'<a href="{escape(urls[k])}" target="_blank" rel="noopener"><span class="dfab-mi">{_icon(k, 16)}</span>'
        f'<span class="dfab-mt">{escape(name)}<small>{escape(desc)}</small></span>{_icon("ext", 12)}</a>'
        for k, name, desc in TOOLS if urls.get(k))
    menu = ""
    if items or all_tools:
        if all_tools:
            items += ('<hr>' if items else "") + f'<a class="dfab-all" href="{escape(all_tools)}">Tous les outils</a>'
        menu = (f'<div class="dfab-menu" id="dfab-menu" hidden><span class="dfab-mh">Outils</span>{items}</div>')
        buttons.append(f'<a class="dfab-btn dfab-tools" href="{escape(all_tools or "#dfab-menu")}" aria-label="Outils">'
                       f'{_icon("tools", 18)}<span class="dfab-tip" aria-hidden="true">Outils</span></a>')
    main_url = urls.get(main_key, "")
    if main_url:
        name, aria = LABELS[main_key]
        buttons.append(f'<a class="dfab-btn dfab-main" href="{escape(main_url)}" aria-label="{escape(aria)}">'
                       f'{_icon(main_key, 22)}<span class="dfab-tip" aria-hidden="true">{escape(name)}</span></a>')
    if not buttons:
        return ""
    return f'<nav class="dfab" aria-label="Raccourcis">{"".join(buttons)}{menu}</nav>{JS}'


def inject(page, shortcuts):
    """Add the stylesheet and the shortcuts to a full HTML page."""
    if not shortcuts or "</body>" not in page:
        return page
    if "</head>" in page:
        page = page.replace("</head>", CSS + "</head>", 1)
    else:
        shortcuts = CSS + shortcuts
    head, _, tail = page.rpartition("</body>")
    return head + shortcuts + "</body>" + tail


# Outils menu (a menu button with JavaScript, a plain link without) and the
# one-time "Nouveau" marker on the intranet button, remembered per browser.
JS = """<script>
(function(){
 var nav=document.querySelector('.dfab');if(!nav)return;
 var btn=nav.querySelector('.dfab-tools'),menu=nav.querySelector('.dfab-menu');
 if(btn&&menu){
  btn.setAttribute('role','button');btn.setAttribute('aria-haspopup','true');
  btn.setAttribute('aria-expanded','false');btn.setAttribute('aria-controls','dfab-menu');
  var set=function(open){btn.setAttribute('aria-expanded',open?'true':'false');menu.hidden=!open};
  btn.addEventListener('click',function(e){e.preventDefault();set(menu.hidden);
   if(!menu.hidden){var f=menu.querySelector('a');if(f&&e.detail===0)f.focus()}});
  btn.addEventListener('keydown',function(e){if(e.key===' '){e.preventDefault();btn.click()}});
  document.addEventListener('click',function(e){if(!nav.contains(e.target))set(false)});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!menu.hidden){set(false);btn.focus()}});
 }
 var nw=nav.querySelector('[data-dfab-new]');
 if(nw){
  var k='dfab-seen-'+nw.dataset.dfabNew,store=null;
  try{store=window.localStorage}catch(e){}
  var seen=true;try{seen=!store||store.getItem(k)==='1'}catch(e){}
  if(!seen){
   nav.classList.add('dfab-is-new');
   nw.insertAdjacentHTML('beforeend','<span class="dfab-dot" aria-hidden="true"></span><span class="dfab-chip" aria-hidden="true">Nouveau</span>');
   nw.addEventListener('click',function(){try{store.setItem(k,'1')}catch(e){}});
  }
 }
})();
</script>"""
