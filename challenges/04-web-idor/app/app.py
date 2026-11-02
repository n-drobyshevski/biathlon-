#!/usr/bin/env python3
"""
04 · Web · MEDIUM (IDOR)
DécaFlop Athlete Portal. You are logged in as bib #1042. The profile page is
/profile/<id> and does NOT check that the id belongs to you. Walk the ids
(crew/admin accounts have low numbers) to read someone else's profile.

Teaches: Insecure Direct Object Reference, horizontal privilege escalation.
"""
import os
from html import escape
from flask import Flask, Response, redirect, make_response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

# id -> (name, role, note)
ATHLETES = {
    1000: ("DécaFlop Event Admin", "admin",
           "AUDIT LOG — official start list 'FINAL_RACE':\n"
           "  last modified_by = staff account 'v.lindqvist' "
           "(mirrored SAP user: VLINDQVIST)\n"
           "  change: swapped shooting-lane assignments for 3 athletes.\n"
           "Escalate to the SAP results team — see the DFlop ERP system."),
    1001: ("Chief Timekeeper", "crew",
           "Timing booth is on the crew Wi-Fi 'DECAFLOP-TIMING'. "
           "Stop sending the booth login over plain HTTP!"),
    1042: ("You (guest bib)", "athlete",
           "Welcome, competitor. You can only see your own profile... right?"),
    1055: ("Astrid Bjornsen", "athlete", "Favourite for the sprint."),
    1071: ("Mikkel Haugen", "athlete", "Strong shooter, weak skier."),
}

CSS = """body{font-family:system-ui,sans-serif;background:#102a43;color:#e3f0ff;margin:0}
header{background:#0a1d33;padding:22px 36px;border-bottom:3px solid #4fb0ff}
main{max-width:640px;margin:36px auto;padding:0 18px}
.card{background:#163a5e;border:1px solid #2b5f8f;border-radius:10px;padding:18px;margin:14px 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#bfe3ff;margin:0}a{color:#7cc5ff}
*{box-sizing:border-box}body{line-height:1.55}
header{padding:18px 20px}header .in{max-width:640px;margin:0 auto;display:flex;
 flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
header h1{margin:0;font-size:22px}header h1 a{color:inherit;text-decoration:none}
.me{font-size:13px;background:#163a5e;border:1px solid #2b5f8f;border-radius:999px;padding:4px 12px}
.head{display:flex;gap:14px;align-items:center}
.av{flex:none;width:52px;height:52px;border-radius:50%;display:grid;place-items:center;
 font-weight:800;background:#0a1d33;border:2px solid #4fb0ff}
.head h2{margin:0;font-size:20px}.head p{margin:2px 0 0;color:#9cc3e6;font-size:14px}
.badge{display:inline-block;font-size:12px;font-weight:700;text-transform:uppercase;
 letter-spacing:.5px;padding:2px 8px;border-radius:4px}
.admin{background:#5c1f2a;color:#ffc2cc}.crew{background:#5a4512;color:#ffe3a3}
.athlete{background:#1d4d7a;color:#cfe8ff}
.note{background:#0f2c4a;border-radius:8px;padding:14px;margin-top:14px}
.flag{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:14px;
 background:#0a1d33;border:1px solid #4fb0ff;border-radius:8px;padding:10px 12px}
.flag code{flex:1;min-width:0;overflow-wrap:anywhere;user-select:all;color:#fff}
.btn,.flag button{display:inline-block;font:inherit;font-size:14px;font-weight:700;
 background:#4fb0ff;color:#0a1d33;border:0;border-radius:6px;padding:8px 14px;
 cursor:pointer;text-decoration:none}
a:focus-visible,button:focus-visible{outline:3px solid #ffd166;outline-offset:2px}
.hint{color:#9cc3e6;font-size:14px}"""

VP = '<meta name="viewport" content="width=device-width,initial-scale=1">'

COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copied \u2713';setTimeout(function(){b.textContent='Copy'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

def shell(title, body):
    signed_in = request.cookies.get("bib")
    me = (f'<span class="me">Signed in · bib #{escape(signed_in)}</span>'
          if signed_in else "")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">{VP}
<title>{title}</title><style>{CSS}</style>
<header><div class="in"><h1><a href="/">🎿 DécaFlop Athlete Portal</a></h1>{me}</div></header>
<main>{body}</main>"""

LOGIN = """<div class="card">
<h2 style="margin-top:0">Welcome, competitor</h2>
<p>For the demo, sign-in is disabled. Continue as the guest competitor.</p>
<p><a class="btn" href="/login">Continue as bib #1042 →</a></p>
</div>"""

def page(aid):
    if aid not in ATHLETES:
        return shell("Athlete not found", f"""<div class="card">
  <h2 style="margin-top:0">No athlete #{aid}</h2>
  <p class="hint">There is no profile with that number.</p>
  <p><a class="btn" href="/profile/1042">← Back to my profile</a></p>
</div>"""), 404
    name, role, note = ATHLETES[aid]
    initials = "".join(w[0] for w in name.replace("(", "").split()[:2]).upper()
    flag = (f"""<div class="flag"><b>FLAG</b> <code id="flag">{FLAG}</code>
  <button type="button" onclick="copyFlag(this)">Copy</button></div>{COPY_JS}"""
            if aid == 1000 else "")
    return shell(f"Profile #{aid}", f"""<div class="card">
  <div class="head"><div class="av" aria-hidden="true">{initials}</div>
    <div><h2>{name}</h2>
    <p>Profile #{aid} · <span class="badge {role}">{role}</span></p></div></div>
  {flag}
  <div class="note"><pre>{note}</pre></div>
</div>
<div class="card hint">You are viewing <code>/profile/{aid}</code>.
  Your bib is <b>1042</b>. (Crew/admin accounts use lower numbers.)</div>"""), 200

@app.get("/")
def home():
    return Response(shell("DécaFlop Athlete Portal", LOGIN), mimetype="text/html")

@app.get("/login")
def login():
    r = make_response(redirect("/profile/1042"))
    r.set_cookie("bib", "1042")
    return r

@app.get("/profile/<int:aid>")
def profile(aid):
    # VULN: trusts the URL id, never compares to the signed-in bib cookie.
    body, status = page(aid)
    return Response(body, status=status, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
