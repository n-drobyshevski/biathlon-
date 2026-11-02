#!/usr/bin/env python3
"""
14 · SAP · MEDIUM (Gateway reginfo/secinfo — missing ACL)
Simulated SAP Gateway monitor. Based on a real, well-known SAP exposure: when
the gateway's reginfo/secinfo access-control lists are left at their permissive
default, unauthorized external programs can REGISTER with the gateway.

This is a SIMULATION for a training CTF — it models only the information
disclosure and the "registration is open" check, NOT any real RFC/registration
protocol or code execution. Reading the exposed config (reginfo) tells you the
gateway accepts registrations; registering a program returns the flag.

Teaches: why gateway reginfo/secinfo ACLs matter, reading an exposed gateway
monitor, recognising a permissive ACL.
"""
import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

CSS = """body{font-family:'Segoe UI',system-ui,sans-serif;background:#f0f2f5;color:#1d2d3e;margin:0;line-height:1.55}
.bar{background:#0a6ed1;color:#fff;padding:14px 26px;font-weight:600;font-size:17px}
.wrap{max-width:760px;margin:28px auto;padding:0 18px}
.card{background:#fff;border:1px solid #d9dfe6;border-radius:8px;padding:18px 20px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
pre{background:#0b1b2b;color:#9fe0b0;padding:14px;border-radius:6px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;color:#556;border-bottom:1px solid #d9dfe6;padding:6px 8px}
td{border-bottom:1px solid #eef;padding:7px 8px}
.warn{color:#b00020;font-weight:600}.ok{color:#256f3a;font-weight:600}
input{padding:8px;border:1px solid #c3ccd6;border-radius:4px;font:inherit}
button{background:#0a6ed1;color:#fff;border:0;padding:9px 16px;border-radius:4px;font-weight:600;cursor:pointer}
a{color:#0a6ed1}code{font-family:ui-monospace,Menlo,Consolas,monospace}h1,h2{margin:.2em 0}"""

MONITOR = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SAP DFlop · Gateway Monitor</title><style>{CSS}</style></head><body>
<div class="bar">SAP&nbsp;DFlop&nbsp;ERP&nbsp;&middot;&nbsp;Gateway&nbsp;Monitor&nbsp;(SMGW)</div>
<div class="wrap">
<div class="card"><h2>État du gateway</h2>
<table><tr><th>SID</th><td>DFL</td></tr><tr><th>Gateway</th><td>sapgw00 (port 3300)</td></tr>
<tr><th>Version</th><td>753</td></tr><tr><th>Programmes externes enregistrés</th><td>0</td></tr></table></div>
<div class="card"><h2>Sécurité</h2>
<p><code>reg_info</code> / <code>sec_info</code> : <span class="warn">valeurs par défaut — aucune ACL.</span>
Les programmes externes peuvent s'enregistrer sans restriction.</p>
<p>Voir la configuration : <a href="/sap/gw/reginfo">/sap/gw/reginfo</a></p></div>
<div class="card"><h2>Enregistrer un programme (TP)</h2>
<form method="post" action="/sap/gw/register">
<input name="tp" placeholder="nom du programme (TP_NAME)" value="" aria-label="TP name" autofocus>
<button>Enregistrer</button></form>
<p style="font-size:12px;color:#889">Production DFL. Accès non autorisé interdit.</p></div>
</div></body></html>"""

REGINFO = """# reginfo — Gateway registration ACL (DFL / sapgw00)
#
# Format: P TP=<program> HOST=<host> ACCESS=<host> CANCEL=<host>
#
# (vide — aucune règle définie)
#
# NOTE Basis: ACL non configurée. Comportement par défaut = tout autorisé.
#   Tout programme externe peut s'enregistrer (P TP=* HOST=* ...).
#   À corriger: définir reginfo/secinfo (gw/reg_no_conn_info, gw/acl_mode=1).
"""


@app.get("/")
def monitor():
    return Response(MONITOR, mimetype="text/html")


@app.get("/sap/gw/reginfo")
def reginfo():
    return Response(REGINFO, mimetype="text/plain")


@app.post("/sap/gw/register")
def register():
    tp = request.form.get("tp", "").strip()
    if not tp:
        return Response(MONITOR, mimetype="text/html")
    # VULN (simulated): reginfo/secinfo are permissive, so any registration is
    # accepted. A real missing ACL would let an attacker register a malicious
    # RFC server; here it simply grants the flag.
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Enregistrement accepté</title><style>{CSS}</style></head><body>
<div class="bar">SAP DFlop ERP &middot; Gateway Monitor (SMGW)</div>
<div class="wrap"><div class="card"><h2 class="ok">✓ Programme « {tp} » enregistré</h2>
<p>Le gateway a accepté l'enregistrement car <code>reginfo</code>/<code>sec_info</code>
sont permissifs (aucune ACL). Un attaquant pourrait enregistrer un serveur RFC
malveillant. Ici, cela vous donne le drapeau.</p>
<pre>FLAG: {FLAG}

CORRECTIF: définir reginfo et secinfo, puis gw/acl_mode=1.
Sans ACL, le gateway fait confiance à tout programme qui s'enregistre.</pre>
</div></div></body></html>"""
    return Response(page, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
