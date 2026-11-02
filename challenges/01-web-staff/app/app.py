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

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DécaFlop · Official Sponsor of the Regional Biathlon Championship</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#0b3d2e;color:#eafff5}
 header{background:#07291f;padding:24px 20px;border-bottom:4px solid #19c37d}
 header h1{max-width:720px;margin:0 auto}
 h1{margin:0;font-size:28px;letter-spacing:1px}
 .tag{color:#8fe9c4}
 main{max-width:720px;margin:40px auto;padding:0 20px;line-height:1.6}
 .card{background:#0f4a39;border:1px solid #19704f;border-radius:10px;padding:20px;margin:16px 0}
 footer{color:#5fae8f;padding:30px 20px;font-size:13px;max-width:720px;margin:0 auto}
 a{color:#19c37d}
 @media(max-width:520px){h1{font-size:22px}.tag{display:block;font-size:15px}}
</style></head><body>
<header><h1>DÉCAFLOP <span class="tag">// sport pour (presque) tous</span></h1></header>
<main>
 <p>Welcome to the official site of <b>DécaFlop</b>, proud title sponsor of the
    Regional Biathlon Championship. Skis, rifles, questionable returns policy.</p>
 <div class="card">
   <h3>🎿 The Final Race is tomorrow!</h3>
   <p>Start lists, timing and results are managed by our event crew.
      Public visitors can view the schedule soon.</p>
 </div>
 <div class="card">
   <h3>Careers</h3>
   <p>DécaFlop is always hiring. We definitely do not have an internal-only
      area on this very website. Please do not look for it.</p>
 </div>
</main>
<footer>© DécaFlop. All flops reserved. Crawlers welcome — see <a href="/robots.txt">/robots.txt</a></footer>
</body></html>"""

STAFF = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DécaFlop — Staff Portal</title>
<style>body{font-family:ui-monospace,Menlo,Consolas,monospace;background:#071f17;color:#b9ffe0;padding:40px 20px;margin:0;line-height:1.6}
h2,.box{max-width:680px;margin-left:auto;margin-right:auto}
.box{border:1px dashed #19c37d;padding:20px;border-radius:8px}
hr{border:0;border-top:1px dashed #19704f;margin:18px 0}
.flag{display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:#0b2e22;
 border:1px solid #19c37d;border-radius:6px;padding:10px 12px}
.flag code{flex:1;min-width:0;overflow-wrap:anywhere;user-select:all;color:#fff}
.flag button{font:inherit;font-size:13px;background:#19c37d;color:#04281c;border:0;
 border-radius:4px;padding:6px 12px;cursor:pointer;font-weight:700}
.flag button:focus-visible{outline:3px solid #ffd23f;outline-offset:2px}</style>
</head><body>
<h2>🔒 DÉCAFLOP STAFF PORTAL (internal)</h2>
<div class="box">
<p>You found the "hidden" area. It was in <code>/robots.txt</code> the whole time.</p>
<p><b>Flag:</b></p>
<div class="flag"><code id="flag">{flag}</code>
 <button type="button" onclick="copyFlag(this)">Copy</button></div>
<hr>
<p>📎 <b>Crew note:</b> All staff accounts follow the convention
   <code>first-initial + lastname</code> and are mirrored into our
   <b>SAP DFlop ERP</b> system as the matching SAP user. Remember this —
   it matters for the results system.</p>
</div>{copyjs}</body></html>"""

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
