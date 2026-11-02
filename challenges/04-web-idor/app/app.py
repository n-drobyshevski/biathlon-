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
    me = (f'<span><span class="mute">Signed in as</span> <b>bib {escape(signed_in)}</b></span>'
          if signed_in else '<span class="mute">Not signed in</span>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<div class="strip"><div class="in"><span>Regional Biathlon Championship · Athlete portal</span>
<span>Race office opens 07:30</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Athlete portal</small></a>
 <nav class="acct">{me}</nav>
</div></header>
<main class="page">{body}</main></body></html>"""

LOGIN = """<div class="panel">
 <h1 class="h">Welcome, competitor</h1>
 <p>Check your start time, lane and race notes before the final.</p>
 <p class="note db" style="margin:0 0 18px">For the demo, sign-in is disabled.
  Continue as the guest competitor.</p>
 <a class="btn blue" href="/login">Continue as bib #1042</a>
</div>"""

def page(aid):
    if aid not in ATHLETES:
        return shell("Athlete not found", f"""<div class="crumb">profiles / #{aid}</div>
<div class="panel"><h1 class="h">No athlete #{aid}</h1>
 <p class="mute">There is no profile with that number.</p>
 <a class="btn blue" href="/profile/1042">Back to my profile</a></div>"""), 404
    name, role, note = ATHLETES[aid]
    flag = (f"""<div class="flag"><span>Flag</span><code id="flag">{FLAG}</code>
 <button type="button" onclick="copyFlag(this)">Copy</button></div>{COPY_JS}"""
            if aid == 1000 else "")
    ink = " ink" if role != "athlete" else ""
    return shell(f"Profile #{aid}", f"""<div class="crumb">profiles / #{aid}</div>
<div class="panel">
 <div class="who"><div class="bib{ink}">{aid}</div>
  <div><h1 class="h">{name}</h1><span class="tag {role}">{role}</span></div></div>
 {flag}
 <div class="log"><pre>{note}</pre></div>
</div>
<p class="small mute">You are viewing <code>/profile/{aid}</code>.
  Your bib is <b>1042</b>. (Crew/admin accounts use lower numbers.)</p>"""), 200

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
