"""
DécaFlop public storefront for challenge 01 (decor only: nothing here is part
of the challenge). Every page is static; no user input is echoed back, so the
storefront offers no rabbit holes. The challenge itself (robots.txt + the
staff portal) lives in app.py.
"""
from flask import Blueprint, Response, abort, request

shop = Blueprint("shop", __name__)

# --------------------------------------------------------------------------
# Line pictograms (inline SVG; the Pi has no internet, so no image assets)
# --------------------------------------------------------------------------
_SVG = ('<svg width="{s}" height="{s}" viewBox="0 0 96 96" fill="none" stroke="currentColor" '
        'stroke-width="5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">')
_PATHS = {
    "bike": '<circle cx="22" cy="62" r="15"/><circle cx="74" cy="62" r="15"/><path d="M22 62 40 36 48 62Z"/><path d="M40 36h24L48 62"/><path d="M64 36l10 26"/><path d="M64 36l3-9h9"/><path d="M33 31h13"/>',
    "goggle": '<rect x="12" y="38" width="30" height="20" rx="10"/><rect x="54" y="38" width="30" height="20" rx="10"/><path d="M42 46q6-5 12 0"/><path d="M12 48H5M84 48h7"/>',
    "bottle": '<path d="M44 9h8v9h-8z"/><path d="M38 18h20l4 9v53a5 5 0 0 1-5 5H39a5 5 0 0 1-5-5V27z"/><path d="M34 42h28M34 56h28"/>',
    "shoe": '<path d="M9 64c0-9 5-15 9-19l5-13 13 4c3 8 10 12 21 14l20 4c8 2 11 6 11 10v4H9z"/><path d="M9 72h79"/><path d="M29 40l7 4M34 33l7 4"/>',
    "cap": '<path d="M14 66c0-22 15-38 34-38s34 16 34 38z"/><path d="M14 66h68"/><path d="M48 30v36"/>',
    "wetsuit": '<path d="M36 12h24l14 12-8 10-6-6v58H50V58h-4v28H36V28l-6 6-8-10z"/><path d="M48 12v30"/>',
    "helmet": '<path d="M10 62c0-20 16-34 38-34 18 0 30 10 36 26l-22 10H10z"/><path d="M30 42h14M24 50h12"/><path d="M28 64v8h18"/>',
    "watch": '<rect x="30" y="30" width="36" height="36" rx="8"/><path d="M38 30l3-18h14l3 18M38 66l3 18h14l3-18"/><path d="M48 39v10l6 4"/>',
    "bib": '<path d="M26 22h44l4 56H22z"/><path d="M8 48h14M74 48h14"/><path d="M38 44h20M38 56h12"/>',
    "pin": '<path d="M48 86s26-26 26-46a26 26 0 0 0-52 0c0 20 26 46 26 46z"/><circle cx="48" cy="40" r="9"/>',
    "clock": '<circle cx="48" cy="48" r="34"/><path d="M48 28v20l12 8"/>',
    "wave": '<path d="M8 40q10-10 20 0t20 0 20 0 20 0M8 58q10-10 20 0t20 0 20 0 20 0"/>',
}

def icon(name, size=96):
    return _SVG.format(s=size) + _PATHS[name] + "</svg>"

# --------------------------------------------------------------------------
# Catalogue. Prices in euros; "was" is the crossed-out price ("" = none).
# --------------------------------------------------------------------------
CATEGORIES = {
    "natation": ("Natation", "Tout pour la première épreuve : lunettes, bonnets et "
                 "combinaisons pour l'eau libre."),
    "velo": ("Vélo", "Vélos de chrono, casques et bidons pour les 40 km de la "
             "deuxième épreuve."),
    "course-a-pied": ("Course à pied", "Chaussures, montres et accessoires pour "
                      "finir en courant les 10 derniers kilomètres."),
}

# slug: (category, icon, brand, title, price, was, rating, reviews, description, features)
PRODUCTS = {
    "lunettes-natation": ("natation", "goggle", "Nageflop",
        "Lunettes de natation anti-buée (buée vendue séparément)", "14", "", "3,2", "1 048",
        "Verres teintés pour nager face au soleil levant, joints souples et sangle "
        "double réglable en quelques secondes.",
        ["Verres anti-UV", "Sangle double en silicone", "Étui de rangement inclus"]),
    "bonnet-silicone": ("natation", "cap", "Nageflop",
        "Bonnet de bain en silicone, visible de loin", "6", "", "4,5", "212",
        "Un bonnet épais et coloré pour que les bateaux de sécurité vous repèrent "
        "facilement en eau libre.",
        ["Silicone 100 %", "Coloris jaune fluo", "Taille unique"]),
    "combinaison-tri-500": ("natation", "wetsuit", "Nageflop",
        "Combinaison néoprène Tri 500", "199", "249", "4,3", "96",
        "Néoprène 3/5 mm pour flotter sans effort et une fermeture dorsale "
        "pensée pour une transition rapide.",
        ["Néoprène 3/5 mm", "Fermeture dorsale à cordon", "Eau de 14 à 22 °C"]),
    "velo-chrono-race-900": ("velo", "bike", "Pédalo",
        "Vélo de chrono Race 900, presque carbone", "1 299", "1 499", "4,1", "212",
        "Cadre aluminium aux formes aéro, prolongateurs réglables et "
        "transmission 2 × 11 vitesses.",
        ["Cadre aluminium 6061", "Prolongateurs réglables", "Transmission 2 × 11"]),
    "casque-aero": ("velo", "helmet", "Pédalo",
        "Casque aéro de triathlon", "89", "", "4,0", "57",
        "Profil allongé pour gagner quelques secondes en position, visière "
        "magnétique amovible.",
        ["Visière magnétique", "Molette de réglage", "Normes EN 1078"]),
    "bidon-750": ("velo", "bottle", "Bofbof",
        "Bidon 750 mL, garde l'eau à peu près fraîche", "5", "7", "3,9", "87",
        "Bidon souple sans BPA, valve à débit rapide utilisable d'une main "
        "en roulant.",
        ["Sans BPA", "Valve anti-fuite", "Compatible lave-vaisselle"]),
    "chaussures-lacage-rapide": ("course-a-pied", "shoe", "Runflop",
        "Chaussures de course à laçage rapide (lacets lents)", "59", "", "4,6", "33",
        "Lacets élastiques à serrage rapide pour enfiler les chaussures en "
        "quelques secondes au parc de transition.",
        ["Lacets élastiques", "Drop 8 mm", "Semelle amortissante"]),
    "montre-gps": ("course-a-pied", "watch", "Runflop",
        "Montre GPS multisport", "79", "99", "4,2", "140",
        "Mode triathlon qui enchaîne natation, vélo et course d'une simple "
        "pression, autonomie de 12 h en GPS.",
        ["Mode multisport", "Étanche 50 m", "Autonomie 12 h en GPS"]),
    "ceinture-dossard": ("course-a-pied", "bib", "Runflop",
        "Ceinture porte-dossard élastique", "9", "", "4,7", "301",
        "Fixez votre dossard sans épingles et tournez-le dans le dos pour la "
        "partie vélo.",
        ["Élastique réglable", "Attaches pour gels", "Sans épingles"]),
}

HOME_DEALS = ["velo-chrono-race-900", "lunettes-natation", "bidon-750", "chaussures-lacage-rapide"]

STORES = [
    ("DécaFlop Stade", "2 allée du Stade", "Lun–sam 9 h – 20 h · dim 9 h – 13 h",
     ["Atelier vélo", "Location de vélos", "Retrait des commandes"]),
    ("DécaFlop Centre-ville", "14 rue du Port", "Lun–sam 10 h – 19 h",
     ["Retrait des commandes", "Essayage combinaisons"]),
    ("DécaFlop Déstockage", "Parking du Stade, entrée nord", "Ven–dim 9 h – 18 h",
     ["Fins de séries", "Matériel de location d'occasion"]),
]

# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
NAV = [("/triathlon", "Triathlon"), ("/natation", "Natation"), ("/velo", "Vélo"),
       ("/course-a-pied", "Course à pied"), ("/destockage", "Déstockage"),
       ("/recrutement", "Recrutement")]

def layout(title, body, current="", notice=""):
    here = ' aria-current="page"'
    cats = "".join(
        f'<li><a href="{href}"{here if href == current else ""}>{label}</a></li>'
        for href, label in NAV)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<a class="skip" href="#main">Aller au contenu</a>
<div class="strip"><div class="in"><span>Retrait gratuit dans nos 3 magasins</span>
<span>Retours sous 30 jours*  ·  *voir conditions, en gros</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>sport pour (presque) tous</small></a>
 <form class="search" action="/" role="search"><input name="q" aria-label="Rechercher"
   placeholder="Rechercher parmi 40 000 produits et 3 sports"><button>Rechercher</button></form>
 <nav class="acct"><a class="opt" href="/aide">Aide</a><a href="/magasins">Magasins</a></nav>
</div></header>
<nav class="cats" aria-label="Rayons"><ul>{cats}</ul></nav>
{notice}
<main id="main">{body}</main>
<footer class="foot"><div class="in">
 <div><b>Aide</b><ul><li><a href="/aide#commande">Suivi de commande</a></li><li><a href="/aide#retours">Retours</a></li><li><a href="/aide#garantie">Garantie</a></li></ul></div>
 <div><b>Magasins</b><ul><li><a href="/magasins">DécaFlop Stade</a></li><li><a href="/magasins">DécaFlop Centre-ville</a></li><li><a href="/magasins">DécaFlop Déstockage (sur le parking)</a></li></ul></div>
 <div><b>Entreprise</b><ul><li><a href="/recrutement">Recrutement</a></li><li><a href="/triathlon">Sponsoring</a></li></ul></div>
 <div><b>Service client</b>0 800 FLOP FLOP<br><span class="small">Du lundi au vendredi, 9 h – 18 h</span></div>
</div>
<div class="legal"><div class="in"><span>© DécaFlop. Tous flops réservés.</span>
<span>Robots d'indexation bienvenus — voir <a href="/robots.txt">/robots.txt</a></span></div></div>
</footer></body></html>"""

def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")

def price_tag(price, was):
    old = f"<s>{was} €</s>" if was else ""
    return f'<span class="price">{price} €{old}</span>'

def card(slug):
    cat, ic, brand, title, price, was, rating, reviews, _d, _f = PRODUCTS[slug]
    return f"""<a class="prod" href="/produit/{slug}"><div class="ph">{icon(ic)}</div>
<div class="b"><div class="brand">{brand}</div><div class="t">{title}</div>
{price_tag(price, was)}<div class="rate">★ {rating} · {reviews} avis</div></div></a>"""

def crumbs(*items):
    parts = [f'<a href="{h}">{t}</a>' if h else f"<span>{t}</span>" for h, t in items]
    return '<nav class="crumb" aria-label="Fil d\'Ariane">' + " / ".join(parts) + "</nav>"

# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
SEARCH_NOTICE = """<div class="in" style="padding-top:12px"><p class="note db" role="status"
 style="margin:0">La recherche en ligne est indisponible pendant la compétition.
 Nos vendeurs vous attendent en magasin.</p></div>"""

SPORT_ICON = {"natation": "goggle", "velo": "bike", "course-a-pied": "shoe"}
SPORT_DIST = {"natation": "1,5 km", "velo": "40 km", "course-a-pied": "10 km"}

@shop.get("/")
def home():
    notice = SEARCH_NOTICE if "q" in request.args else ""
    sports = "".join(
        f"""<a class="sport" href="/{slug}"><span class="ic">{icon(SPORT_ICON[slug], 56)}</span>
<span><b class="h">{name}</b><small>{SPORT_DIST[slug]} · voir le rayon</small></span></a>"""
        for slug, (name, _intro) in CATEGORIES.items())
    body = f"""<section class="banner"><div class="in">
 <div>
  <span class="tagline">Sponsor titre · Championnat régional de triathlon</span>
  <h1 class="h">La finale,<br>c'est <em>demain</em></h1>
  <p>Bienvenue sur le site officiel de <b>DécaFlop</b>, fier sponsor titre du
     Championnat régional de triathlon. Vélos, combinaisons, politique de retour discutable.</p>
  <a class="btn" href="#shop">L'équipement course</a><a class="btn line" href="/triathlon">Infos course</a>
 </div>
 <div class="sched">
  <h2 class="h">Programme du jour J</h2>
  <table><tr><td>7 h 00</td><td>Ouverture du parc à vélos</td><td>Transition</td></tr>
   <tr><td>8 h 30</td><td>Départ finale femmes</td><td>Plage</td></tr>
   <tr><td>10 h 30</td><td>Départ finale hommes</td><td>Plage</td></tr>
   <tr><td>15 h 00</td><td>Podium</td><td>Grand chapiteau</td></tr></table>
  <p class="small mute" style="margin:10px 0 0">Listes de départ, chronométrage et résultats
   sont gérés par notre équipe événement. Le programme public arrive bientôt.</p>
 </div>
</div></section>

<section class="sec"><div class="in">
 <h2 class="h">Nos rayons</h2>
 <div class="sports">{sports}</div>
</div></section>

<section class="sec grey" id="shop"><div class="in">
 <div class="row"><h2 class="h">Les bons plans de la semaine</h2><a href="/destockage">Tout voir</a></div>
 <div class="grid">{"".join(card(s) for s in HOME_DEALS)}</div>
</div></section>

<section class="sec"><div class="in two">
 <div class="tile"><h3 class="h">Location de vélos</h3>
  <p>Vélos de chrono réglés course pour le week-end. Casque inclus.</p>
  <a class="btn blue" href="/magasins">Trouver un magasin</a></div>
 <div class="tile dark"><h3 class="h">Recrutement</h3>
  <p>DécaFlop recrute toujours. Nous n'avons absolument pas d'espace réservé
     au personnel sur ce site. Merci de ne pas le chercher.</p>
  <a href="/recrutement">Offres d'emploi (0)</a></div>
</div></section>"""
    return html(layout("DécaFlop · Sponsor officiel du Championnat régional de triathlon",
                       body, notice=notice))

def listing(title, intro, slugs, current, crumb_label):
    count = f"{len(slugs)} produit{'s' if len(slugs) > 1 else ''}"
    body = f"""<section class="cathead"><div class="in">
 {crumbs(("/", "Accueil"), (None, crumb_label))}
 <h1 class="h">{title}</h1><p>{intro}</p>
</div></section>
<section class="sec"><div class="in">
 <p class="small mute" style="margin:0 0 14px">{count}</p>
 <div class="grid">{"".join(card(s) for s in slugs)}</div>
</div></section>"""
    return html(layout(f"{title} · DécaFlop", body, current=current))

@shop.get("/<any(natation, velo, 'course-a-pied'):cat>")
def category(cat):
    name, intro = CATEGORIES[cat]
    slugs = [s for s, p in PRODUCTS.items() if p[0] == cat]
    return listing(name, intro, slugs, f"/{cat}", name)

@shop.get("/destockage")
def clearance():
    slugs = [s for s, p in PRODUCTS.items() if p[5]]
    return listing("Déstockage", "Fins de séries et prix barrés, tant qu'il y en a.",
                   slugs, "/destockage", "Déstockage")

STOCK = [("DécaFlop Stade", "En stock", "ok"), ("DécaFlop Centre-ville", "Plus que 2", "low"),
         ("DécaFlop Déstockage", "Rupture", "out")]

@shop.get("/produit/<slug>")
def product(slug):
    if slug not in PRODUCTS:
        abort(404)
    cat, ic, brand, title, price, was, rating, reviews, desc, feats = PRODUCTS[slug]
    cat_name = CATEGORIES[cat][0]
    stock = "".join(f'<li><span>{s}</span><span class="st {k}">{t}</span></li>' for s, t, k in STOCK)
    related = [s for s, p in PRODUCTS.items() if p[0] == cat and s != slug]
    body = f"""<div class="in pdp-wrap">
 {crumbs(("/", "Accueil"), (f"/{cat}", cat_name), (None, title))}
 <div class="pdp">
  <div class="pdp-img">{icon(ic, 220)}</div>
  <div class="pdp-info">
   <div class="brand">{brand}</div>
   <h1>{title}</h1>
   <div class="rate">★ {rating} · {reviews} avis</div>
   <div class="pdp-price">{price_tag(price, was)}</div>
   <p>{desc}</p>
   <ul class="feats">{"".join(f"<li>{f}</li>" for f in feats)}</ul>
   <div class="instore"><b>Disponible en magasin uniquement</b>
    <p class="small">Pendant la compétition, la boutique en ligne est fermée.
     Réservez l'article à l'accueil de votre magasin.</p>
    <ul class="stock">{stock}</ul></div>
  </div>
 </div>
</div>
<section class="sec grey"><div class="in">
 <h2 class="h">Dans le même rayon</h2>
 <div class="grid">{"".join(card(s) for s in related)}</div>
</div></section>"""
    return html(layout(f"{title} · DécaFlop", body, current=f"/{cat}"))

@shop.get("/triathlon")
def championship():
    legs = "".join(
        f"""<div class="leg"><span class="ic">{icon(ic, 64)}</span><b class="h">{name}</b>
<span class="dist">{dist}</span><p>{text}</p></div>"""
        for ic, name, dist, text in [
            ("wave", "Natation", "1,5 km", "Départ en vagues depuis la plage, deux boucles balisées par des bouées jaunes."),
            ("bike", "Vélo", "40 km", "Quatre tours d'un circuit fermé à la circulation. Drafting interdit."),
            ("shoe", "Course à pied", "10 km", "Trois boucles le long du port, arrivée devant le grand chapiteau."),
        ])
    body = f"""<section class="banner slim"><div class="in">
 <div>{crumbs(("/", "Accueil"), (None, "Le championnat"))}
  <span class="tagline">Distance olympique</span>
  <h1 class="h">Championnat régional<br>de <em>triathlon</em></h1>
  <p>Deux finales, trois disciplines, un seul parc à vélos. DécaFlop est fier
     d'être sponsor titre de l'édition 2026.</p></div>
</div></section>
<section class="sec"><div class="in">
 <h2 class="h">Le format</h2>
 <div class="legs">{legs}</div>
</div></section>
<section class="sec grey"><div class="in two">
 <div class="panel">
  <h2 class="h">Programme complet</h2>
  <table class="std"><tbody>
   <tr><td>6 h 30</td><td>Retrait des dossards et des puces</td></tr>
   <tr><td>7 h 00</td><td>Ouverture du parc à vélos</td></tr>
   <tr><td>8 h 15</td><td>Briefing des athlètes</td></tr>
   <tr><td>8 h 30</td><td>Départ finale femmes</td></tr>
   <tr><td>10 h 30</td><td>Départ finale hommes</td></tr>
   <tr><td>13 h 30</td><td>Fermeture du parc à vélos</td></tr>
   <tr><td>15 h 00</td><td>Podium et remise des prix</td></tr>
  </tbody></table>
 </div>
 <div class="panel">
  <h2 class="h">Règlement en bref</h2>
  <ul class="feats">
   <li>Puce de chronométrage obligatoire, portée à la cheville gauche.</li>
   <li>Casque attaché avant de toucher le vélo, et jusqu'à l'avoir reposé.</li>
   <li>Drafting interdit sur la partie vélo : 1 minute de pénalité.</li>
   <li>Combinaison autorisée si l'eau est sous 22 °C.</li>
  </ul>
  <p class="small mute" style="margin:12px 0 0">Les résultats officiels seront
   publiés ici après la course.</p>
 </div>
</div></section>
<section class="sec"><div class="in">
 <h2 class="h">Venir en spectateur</h2>
 <div class="two">
  <div class="tile"><h3 class="h">Accès</h3><p>Navettes gratuites depuis le
   centre-ville toutes les 15 minutes. Parking vélo surveillé près du stade.</p></div>
  <div class="tile"><h3 class="h">Sur place</h3><p>Écran géant au grand chapiteau,
   village partenaires et stand de réparation DécaFlop ouvert toute la journée.</p></div>
 </div>
</div></section>"""
    return html(layout("Le championnat · DécaFlop", body, current="/triathlon"))

@shop.get("/magasins")
def stores():
    cards = "".join(
        f"""<div class="store"><h2 class="h">{name}</h2>
<p class="li">{icon("pin", 20)}<span>{addr}</span></p>
<p class="li">{icon("clock", 20)}<span>{hours}</span></p>
<ul class="chips">{"".join(f"<li>{s}</li>" for s in services)}</ul></div>"""
        for name, addr, hours, services in STORES)
    body = f"""<section class="cathead"><div class="in">
 {crumbs(("/", "Accueil"), (None, "Magasins"))}
 <h1 class="h">Nos magasins</h1>
 <p>Trois magasins autour du stade, tous ouverts pendant le week-end de course.</p>
</div></section>
<section class="sec"><div class="in"><div class="stores">{cards}</div></div></section>"""
    return html(layout("Magasins · DécaFlop", body))

FAQ = [
    ("commande", "Où en est ma commande ?",
     "Les commandes passées avant la compétition sont livrées en magasin. Vous "
     "recevez un SMS dès qu'elles sont prêtes, avec votre numéro de retrait."),
    ("retours", "Comment retourner un article ?",
     "Rapportez-le dans n'importe quel magasin sous 30 jours avec votre ticket. "
     "Les articles portés pendant une course ne sont pas repris."),
    ("garantie", "Que couvre la garantie ?",
     "Deux ans sur tout le matériel, cinq ans sur les cadres de vélo. L'usure "
     "normale (pneus, plaquettes, lacets) n'est pas couverte."),
    ("location", "Puis-je louer un vélo pour la course ?",
     "Oui, au magasin Stade, sur présentation d'une pièce d'identité. Le vélo est "
     "réglé à votre taille et le casque est inclus."),
]

@shop.get("/aide")
def help_page():
    items = "".join(f"""<details class="faq" id="{k}"><summary>{q}</summary><p>{a}</p></details>"""
                    for k, q, a in FAQ)
    body = f"""<section class="cathead"><div class="in">
 {crumbs(("/", "Accueil"), (None, "Aide"))}
 <h1 class="h">Aide et contact</h1>
 <p>Les réponses aux questions les plus fréquentes.</p>
</div></section>
<section class="sec"><div class="in two">
 <div>{items}</div>
 <div class="tile"><h3 class="h">Nous contacter</h3>
  <p><b>0 800 FLOP FLOP</b><br>Du lundi au vendredi, 9 h – 18 h. Appel gratuit.</p>
  <a class="btn blue" href="/magasins">Trouver un magasin</a></div>
</div></section>"""
    return html(layout("Aide · DécaFlop", body))

@shop.get("/recrutement")
def careers():
    values = "".join(f"""<div class="tile"><h3 class="h">{t}</h3><p>{d}</p></div>""" for t, d in [
        ("Sport", "Une heure de sport offerte par semaine sur votre temps de travail."),
        ("Proximité", "Des conseils de pratiquant à pratiquant, en magasin comme au bord de la course."),
        ("Bonne humeur", "Une équipe qui préfère les solutions aux excuses."),
    ])
    body = f"""<section class="banner slim"><div class="in">
 <div>{crumbs(("/", "Accueil"), (None, "Recrutement"))}
  <h1 class="h">Rejoignez<br><em>l'équipe</em></h1>
  <p>DécaFlop recrute toujours. Nous n'avons absolument pas d'espace réservé
     au personnel sur ce site. Merci de ne pas le chercher.</p></div>
</div></section>
<section class="sec"><div class="in">
 <h2 class="h">Nos valeurs</h2>
 <div class="three">{values}</div>
</div></section>
<section class="sec grey"><div class="in">
 <div class="row"><h2 class="h">Offres d'emploi (0)</h2></div>
 <div class="panel"><p style="margin:0">Aucune offre ouverte pour le moment.
  Déposez une candidature spontanée à l'accueil de votre magasin.</p></div>
</div></section>"""
    return html(layout("Recrutement · DécaFlop", body, current="/recrutement"))
