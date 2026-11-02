#!/usr/bin/env python3
"""
08 · SAP · HARD   (simulated — real SAP NetWeaver won't fit on a Pi)
"SAP DFlop ERP" — a mock SAP NetWeaver / Fiori launchpad.

Two intended steps, both based on REAL SAP misconfigurations:

  1. The ICF service /sap/public/info is reachable WITHOUT authentication and
     leaks system details (this is a genuine SAP information-disclosure class).
     It hints that the SAP* emergency user still exists in client 001.

  2. The infamous SAP* backdoor: when the SAP* user record is missing, SAP
     accepts the hard-coded default password  06071992  for client 001.
     Logging in as  SAP*  /  06071992  (client 001) grants admin -> flag.

Teaches: SAP default/backdoor accounts, unauthenticated ICF endpoints,
reading system-info disclosure to pivot. HARD = you must know/look up the
SAP* default behaviour.
"""
import os
from html import escape
from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

CSS = """body{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f2f5;color:#1d2d3e;margin:0}
.bar{background:#0a6ed1;color:#fff;padding:14px 28px;font-weight:600;font-size:18px}
.wrap{max-width:460px;margin:60px auto;background:#fff;border:1px solid #d9dfe6;
 border-radius:8px;padding:28px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
label{font-size:13px;color:#556;display:block;margin-top:12px}
input{width:100%;padding:9px;margin-top:4px;border:1px solid #c3ccd6;border-radius:4px;box-sizing:border-box}
button{margin-top:18px;background:#0a6ed1;color:#fff;border:0;padding:10px 20px;border-radius:4px;
 font-weight:600;cursor:pointer}
.msg{margin-top:14px;color:#b00020;font-size:14px}
pre{background:#0b1b2b;color:#9fe0b0;padding:16px;border-radius:6px;white-space:pre-wrap;
 overflow-wrap:anywhere;font-size:13px}
a{color:#0a6ed1}
*{box-sizing:border-box}
.wrap{margin:40px 16px}@media(min-width:500px){.wrap{margin:60px auto}}
.wrap h3{margin-top:0}
input:focus{outline:none;border-color:#0a6ed1;box-shadow:0 0 0 2px rgba(10,110,209,.3)}
button{width:100%;font-size:15px}button:hover{background:#0854a0}
button:focus-visible,a:focus-visible{outline:2px solid #1d2d3e;outline-offset:2px}
.msg:empty{display:none}
.msg{background:#ffebeb;border-left:4px solid #bb0000;color:#8a0000;padding:8px 12px;border-radius:4px}
.flag{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0;
 background:#e8f2fc;border:1px solid #0a6ed1;border-radius:6px;padding:10px 12px}
.flag code{flex:1;min-width:0;overflow-wrap:anywhere;user-select:all;font-size:15px}
.flag button{width:auto;margin:0;font-size:13px;padding:6px 12px}"""

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

def launchpad(form_msg="", client="001", user=""):
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">{VP}
<title>SAP DFlop ERP — Logon</title>
<style>{CSS}</style>
<div class="bar">SAP DFlop ERP &middot; NetWeaver Fiori Launchpad</div>
<div class="wrap">
 <h3>SAP System Logon</h3>
 <form method="post" action="/sap/bc/ui2/logon">
   <label for="c">Client</label>
   <input id="c" name="client" value="{escape(client)}" inputmode="numeric" autocomplete="off">
   <label for="u">User</label>
   <input id="u" name="user" value="{escape(user)}" autofocus autocomplete="off"
    autocapitalize="characters" autocorrect="off" spellcheck="false">
   <label for="p">Password</label>
   <input id="p" name="password" type="password" autocomplete="off">
   <button>Log On</button>
 </form>
 <div class="msg" role="alert">{form_msg}</div>
 <p style="margin-top:20px;font-size:12px;color:#889">
   Production system DFL. Unauthorized access prohibited.</p>
</div>"""

INFO = """HTTP/1.1 200 OK
Server: SAP NetWeaver Application Server / ABAP

<SAP:SYSINFO>
  SID               = DFL
  INSTANCE          = DVEBMGS00
  DB                = HANA 2.0
  KERNEL            = 753
  CLIENTS           = 000 (SAP master), 001 (DFLOP PROD), 066 (EarlyWatch)
  ICF_SERVICES      = /sap/public/info [PUBLIC], /sap/bc/ui2/logon,
                      /sap/bc/soap/rfc [restricted], /sap/public/icman
  NOTE_FROM_BASIS   = "Audit finding: the emergency user SAP* was DELETED from
                       client 001 last week and never recreated. Until Basis
                       recreates it, logons as SAP* fall back to the kernel
                       default. Fix ASAP (login/no_automatic_user_sapstar=1)."
</SAP:SYSINFO>
"""

def admin_page():
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">{VP}
<title>DFL — SAP GUI</title>
<style>{CSS}</style>
<div class="bar">SAP DFlop ERP &middot; Easy Access (SAP*)</div>
<div class="wrap" style="max-width:720px">
<h3>✅ Logged on to client 001 as SAP*</h3>
<div class="flag"><b>FLAG</b> <code id="flag">{FLAG}</code>
 <button type="button" onclick="copyFlag(this)">Copy</button></div>
<pre>You used the SAP* kernel backdoor (default password 06071992) because the
SAP* user record was deleted from client 001 and never recreated.

TRANSACTION SU01 — relevant users in client 001:
  RESULTS_ADMIN   locked, service account
  VLINDQVIST      Viktor Lindqvist  (results_operator, created 3 days ago)
  MSORENSEN       Maria Sorensen    (read-only)

NEXT: the authoritative results table ZRACE_RESULT was changed by one of
these users. To prove who, export the password/user table USR02 and check
the last-logon + change records. (That export is handed out separately.)</pre>
</div>{COPY_JS}"""

@app.get("/")
def root():
    return Response(launchpad(), mimetype="text/html")

@app.get("/sap/public/info")
def public_info():
    # VULN 1: unauthenticated ICF info disclosure
    return Response(INFO, mimetype="text/plain")

@app.get("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /sap/public/\nDisallow: /sap/bc/\n",
                    mimetype="text/plain")

@app.post("/sap/bc/ui2/logon")
def logon():
    user = request.form.get("user", "").strip().upper()
    pw = request.form.get("password", "")
    client = request.form.get("client", "").strip()
    # VULN 2: SAP* backdoor active (SAP* missing in client 001)
    if client == "001" and user == "SAP*" and pw == "06071992":
        return Response(admin_page(), mimetype="text/html")
    return Response(launchpad("Name or password is incorrect. Logon failed.",
                              client=request.form.get("client", "001"),
                              user=request.form.get("user", "")),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
