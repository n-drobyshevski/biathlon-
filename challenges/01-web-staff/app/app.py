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

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DécaFlop · Official Sponsor of the Regional Biathlon Championship</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:0;background:#0b3d2e;color:#eafff5}}
 header{{background:#07291f;padding:28px 40px;border-bottom:4px solid #19c37d}}
 h1{{margin:0;font-size:28px;letter-spacing:1px}}
 .tag{{color:#8fe9c4}}
 main{{max-width:720px;margin:40px auto;padding:0 20px;line-height:1.6}}
 .card{{background:#0f4a39;border:1px solid #19704f;border-radius:10px;padding:20px;margin:16px 0}}
 footer{{color:#5fae8f;padding:30px 40px;font-size:13px}}
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
<footer>© DécaFlop. All flops reserved. Crawlers welcome — see /robots.txt</footer>
</body></html>"""

STAFF = """<!doctype html><html><head><meta charset="utf-8">
<title>DécaFlop — Staff Portal</title>
<style>body{{font-family:monospace;background:#071f17;color:#b9ffe0;padding:40px}}
.box{{border:1px dashed #19c37d;padding:20px;border-radius:8px;max-width:680px}}</style>
</head><body>
<h2>🔒 DÉCAFLOP STAFF PORTAL (internal)</h2>
<div class="box">
<p>You found the "hidden" area. It was in <code>/robots.txt</code> the whole time.</p>
<p><b>Flag:</b> <code>{flag}</code></p>
<hr>
<p>📎 <b>Crew note:</b> All staff accounts follow the convention
   <code>first-initial + lastname</code> and are mirrored into our
   <b>SAP DFlop ERP</b> system as the matching SAP user. Remember this —
   it matters for the results system.</p>
</div></body></html>"""

ROBOTS = """User-agent: *
Disallow: /staff-portal-7f3a9
# internal only — do not index the results tooling
Disallow: /sap/
"""

@app.get("/")
def home():
    return Response(PAGE.format(), mimetype="text/html")

@app.get("/robots.txt")
def robots():
    return Response(ROBOTS, mimetype="text/plain")

@app.get("/staff-portal-7f3a9")
def staff():
    return Response(STAFF.format(flag=FLAG), mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
