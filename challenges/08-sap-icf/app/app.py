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
pre{background:#0b1b2b;color:#9fe0b0;padding:16px;border-radius:6px;white-space:pre-wrap}
a{color:#0a6ed1}"""

def launchpad(form_msg=""):
    return f"""<!doctype html><meta charset="utf-8"><title>SAP DFlop ERP — Logon</title>
<style>{CSS}</style>
<div class="bar">SAP&nbsp;DFlop&nbsp;ERP&nbsp;&middot;&nbsp;NetWeaver&nbsp;Fiori&nbsp;Launchpad</div>
<div class="wrap">
 <h3>SAP System Logon</h3>
 <form method="post" action="/sap/bc/ui2/logon">
   <label>Client</label><input name="client" value="001">
   <label>User</label><input name="user" autofocus>
   <label>Password</label><input name="password" type="password">
   <button>Log On</button>
 </form>
 <div class="msg">{form_msg}</div>
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
    return f"""<!doctype html><meta charset="utf-8"><title>DFL — SAP GUI</title>
<style>{CSS}</style>
<div class="bar">SAP DFlop ERP &middot; Easy Access (SAP*)</div>
<div class="wrap" style="max-width:720px">
<h3>✅ Logged on to client 001 as SAP*</h3>
<pre>FLAG: {FLAG}

You used the SAP* kernel backdoor (default password 06071992) because the
SAP* user record was deleted from client 001 and never recreated.

TRANSACTION SU01 — relevant users in client 001:
  RESULTS_ADMIN   locked, service account
  VLINDQVIST      Viktor Lindqvist  (results_operator, created 3 days ago)
  MSORENSEN       Maria Sorensen    (read-only)

NEXT: the authoritative results table ZRACE_RESULT was changed by one of
these users. To prove who, export the password/user table USR02 and check
the last-logon + change records. (That export is handed out separately.)</pre>
</div>"""

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
    return Response(launchpad("Name or password is incorrect. Logon failed."),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
