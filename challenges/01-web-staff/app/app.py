#!/usr/bin/env python3
"""
01 · Web · EASY
DécaFlop sponsor microsite. There is a 'hidden' staff portal — but it is
listed in robots.txt, which anyone can read.

Teaches: robots.txt recon, that "hidden" != "secret".
"""
import os
from flask import Flask, Response

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>"""

# Simple line pictograms for the product grid (no external assets: the Pi
# has no internet).
ICON = {
    "ski": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"><path d="M18 80 74 14M30 84 84 22M70 12c6-4 10 0 8 4M80 20c6-4 10 0 8 4"/></svg>',
    "goggle": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><path d="M14 38h68v18c0 8-6 12-14 12-6 0-10-6-20-6s-14 6-20 6c-8 0-14-4-14-12z"/><path d="M8 46h6M82 46h6"/></svg>',
    "flask": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><rect x="34" y="12" width="28" height="10" rx="2"/><path d="M36 22h24v62H36z"/><path d="M36 44h24"/></svg>',
    "bib": '<svg width="96" height="96" viewBox="0 0 96 96" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round"><path d="M26 16h44l6 66H20z"/><circle cx="36" cy="26" r="2"/><circle cx="60" cy="26" r="2"/><path d="M38 52h20M38 62h12"/></svg>',
}

PRODUCTS = [
    ("ski", "Skiflop", "Skate skis Race 900, carbon-ish", "349", "399", "4.1 · 212 reviews"),
    ("goggle", "Nordik'O", "Anti-fog goggles (fog sold separately)", "24", "", "3.2 · 1 048 reviews"),
    ("flask", "Bofbof", "Insulated bottle 0.5 L, keeps tea warm-ish", "9", "12", "3.9 · 87 reviews"),
    ("bib", "DécaFlop", "Official 2026 race bib, replica", "15", "", "4.6 · 33 reviews"),
]

def product(icon, brand, title, price, was, rate):
    old = f"<s>{was} €</s>" if was else ""
    return f"""<a class="prod" href="#shop"><div class="ph">{ICON[icon]}</div>
<div class="b"><div class="brand">{brand}</div><div class="t">{title}</div>
<span class="price">{price} €{old}</span><div class="rate">★ {rate}</div></div></a>"""

PAGE = HEAD.replace("{title}", "DécaFlop · Official Sponsor of the Regional Biathlon Championship") + """
<div class="strip"><div class="in"><span>Free click &amp; collect in all 3 stores</span>
<span>30-day returns*  ·  *conditions apply, mostly</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>sport pour (presque) tous</small></a>
 <form class="search" action="/" role="search"><input name="q" aria-label="Search"
   placeholder="Search 40 000 products and 3 sports"><button>Search</button></form>
 <nav class="acct"><a class="opt" href="#help">Help</a><a href="#help">Stores</a></nav>
</div></header>
<nav class="cats" aria-label="Departments"><ul>
 <li><a href="#race" aria-current="page">Biathlon</a></li>
 <li><a href="#shop">Cross-country ski</a></li><li><a href="#shop">Shooting</a></li>
 <li><a href="#shop">Clothing</a></li><li><a href="#shop">Outlet</a></li>
 <li><a href="#careers">Careers</a></li></ul></nav>

<section class="banner" id="race"><div class="in">
 <div>
  <span class="tagline">Title sponsor · Regional Biathlon Championship</span>
  <h1 class="h">The Final Race<br>is <em>tomorrow</em></h1>
  <p>Welcome to the official site of <b>DécaFlop</b>, proud title sponsor of the
     Regional Biathlon Championship. Skis, rifles, questionable returns policy.</p>
  <a class="btn" href="#shop">Shop the race kit</a><a class="btn line" href="#race">Race info</a>
 </div>
 <div class="sched">
  <h2 class="h">Race day schedule</h2>
  <table><tr><td>08:30</td><td>Zeroing</td><td>Range</td></tr>
   <tr><td>10:00</td><td>Women's final</td><td>Stadium</td></tr>
   <tr><td>12:30</td><td>Men's final</td><td>Stadium</td></tr>
   <tr><td>15:00</td><td>Podium</td><td>Big tent</td></tr></table>
  <p class="small mute" style="margin:10px 0 0">Start lists, timing and results are
   managed by our event crew. Public visitors can view the schedule soon.</p>
 </div>
</div></section>

<section class="sec" id="shop"><div class="in">
 <div class="row"><h2 class="h">Race-week deals</h2><a href="#shop">See all</a></div>
 <div class="grid">""" + "".join(product(*p) for p in PRODUCTS) + """</div>
</div></section>

<section class="sec grey"><div class="in two">
 <div class="tile"><h3 class="h">Ski rental</h3>
  <p>Race-tuned skate skis for the weekend. Wax included, dignity not.</p>
  <a class="btn blue" href="#help">Find a store</a></div>
 <div class="tile dark" id="careers"><h3 class="h">Careers</h3>
  <p>DécaFlop is always hiring. We definitely do not have an internal-only
     area on this very website. Please do not look for it.</p>
  <a href="#careers">Open positions (0)</a></div>
</div></section>

<footer class="foot" id="help"><div class="in">
 <div><b>Help</b><ul><li><a href="#help">Order tracking</a></li><li><a href="#help">Returns</a></li><li><a href="#help">Warranty</a></li></ul></div>
 <div><b>Stores</b><ul><li>DécaFlop Stadium</li><li>DécaFlop Centre-ville</li><li>DécaFlop Outlet (parking lot)</li></ul></div>
 <div><b>Company</b><ul><li><a href="#careers">Careers</a></li><li><a href="#race">Sponsoring</a></li></ul></div>
 <div><b>Hotline</b>0 800 FLOP FLOP<br><span class="small">Mon–Fri, when someone answers</span></div>
</div>
<div class="legal"><div class="in"><span>© DécaFlop. All flops reserved.</span>
<span>Crawlers welcome — see <a href="/robots.txt">/robots.txt</a></span></div></div>
</footer></body></html>"""

STAFF = HEAD.replace("{title}", "DécaFlop — Staff Portal") + """
<div class="strip"><div class="in"><span>INTERNAL · DécaFlop staff network</span>
<span>Do not share links from this area</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Staff portal</small></a>
 <nav class="acct"><span class="mute">Event crew</span></nav>
</div></header>
<main class="page">
 <div class="crumb"><a href="/">decaflop</a> / staff-portal (internal)</div>
 <div class="panel">
  <h1 class="h">Staff portal</h1>
  <p>You found the "hidden" area. It was in <code>/robots.txt</code> the whole time.</p>
  <div class="flag"><span>Flag</span><code id="flag">{flag}</code>
   <button type="button" onclick="copyFlag(this)">Copy</button></div>
 </div>
 <div class="panel grey">
  <h2 class="h">Crew note</h2>
  <p style="margin:0">All staff accounts follow the convention
   <code>first-initial + lastname</code> and are mirrored into our
   <b>SAP DFlop ERP</b> system as the matching SAP user. Remember this —
   it matters for the results system.</p>
 </div>
</main>{copyjs}</body></html>"""

# Copy button: falls back to execCommand because the Pi is served over plain
# HTTP on a LAN IP, where navigator.clipboard is unavailable.
COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copied \u2713';setTimeout(function(){b.textContent='Copy'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

ROBOTS = """User-agent: *
Disallow: /staff-portal-7f3a9
# internal only — do not index the results tooling
Disallow: /sap/
"""

@app.get("/")
def home():
    return Response(PAGE, mimetype="text/html")

@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")

@app.get("/staff-portal-7f3a9")
def staff():
    return Response(STAFF.replace("{copyjs}", COPY_JS).replace("{flag}", FLAG), mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
