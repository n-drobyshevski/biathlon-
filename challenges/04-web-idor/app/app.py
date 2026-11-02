#!/usr/bin/env python3
"""
04 · Web · MEDIUM (IDOR)
DécaFlop Athlete Portal. You are logged in as bib #1042. The profile page is
/profile/<id> and does NOT check that the id belongs to you. Walk the ids
(crew/admin accounts have low numbers) to read someone else's profile.

Teaches: Insecure Direct Object Reference, horizontal privilege escalation.
"""
import os
from flask import Flask, Response, redirect, make_response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

# id -> (name, role, note)
ATHLETES = {
    1000: ("DécaFlop Event Admin", "admin",
           f"FLAG: {FLAG}\n\n"
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
pre{white-space:pre-wrap;color:#bfe3ff}a{color:#7cc5ff}"""

LOGIN = f"""<!doctype html><meta charset="utf-8"><title>DécaFlop Athlete Portal</title>
<style>{CSS}</style>
<header><h1>🎿 DécaFlop Athlete Portal</h1></header>
<main>
<div class="card">
<p>For the demo, sign-in is disabled. Continue as the guest competitor.</p>
<p><a href="/login">➡ Continue as bib #1042</a></p>
</div></main>"""

def page(aid):
    if aid not in ATHLETES:
        return f"<style>{CSS}</style><main><div class='card'>No athlete #{aid}.</div></main>"
    name, role, note = ATHLETES[aid]
    return f"""<!doctype html><meta charset="utf-8"><title>Profile #{aid}</title>
<style>{CSS}</style>
<header><h1>🎿 DécaFlop Athlete Portal</h1></header>
<main>
<div class="card">
  <h2>Profile #{aid} — {name}</h2>
  <p>Role: <b>{role}</b></p>
  <pre>{note}</pre>
</div>
<div class="card">You are viewing <code>/profile/{aid}</code>.
  Your bib is <b>1042</b>. (Crew/admin accounts use lower numbers.)</div>
</main>"""

@app.get("/")
def home():
    return Response(LOGIN, mimetype="text/html")

@app.get("/login")
def login():
    r = make_response(redirect("/profile/1042"))
    r.set_cookie("bib", "1042")
    return r

@app.get("/profile/<int:aid>")
def profile(aid):
    # VULN: trusts the URL id, never compares to the signed-in bib cookie.
    return Response(page(aid), mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
