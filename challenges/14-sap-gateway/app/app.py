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
import sys
import time
import zlib
from html import escape

from flask import Flask, Response, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

PRODUCT = "SAP DFlop ERP, système DFL, noyau 753"


def shell(title, body):
    return intranet.page(f"{title} - Gateway SAP DFL", body, app="sapgw",
                         site_title="Gateway SAP DFL", site_href="/", logo="GW",
                         topnav=[("/", "Moniteur (SMGW)", True), ("/sap/gw/reginfo", "reginfo", False)],
                         product=PRODUCT, foot_extra="Production DFL. Accès non autorisé interdit.",
                         scripts=intranet.COPY_JS)


STATUS = """<section class="wp"><h2>État du gateway</h2>
<table class="list data"><tbody>
<tr><td style="width:240px" class="mute">SID</td><td>DFL</td></tr>
<tr><td class="mute">Gateway</td><td>sapgw00 (port 3300)</td></tr>
<tr><td class="mute">Version du noyau</td><td>753</td></tr>
<tr><td class="mute">Démarré le</td><td class="num">12/10/2026 06:02:41</td></tr>
<tr><td class="mute">Programmes externes enregistrés</td><td class="num">{count}</td></tr>
</tbody></table></section>"""

MONITOR_BODY = """<h1 class="h1">Moniteur du gateway (SMGW)</h1>
<div class="cols"><div>
""" + STATUS.replace("{count}", "0") + """
<section class="wp"><h2>Sécurité</h2>
<table class="list data"><tbody>
<tr><td style="width:240px"><code>reg_info</code> / <code>sec_info</code></td>
 <td><span class="pill warn">valeurs par défaut, aucune ACL</span></td></tr>
<tr><td><code>gw/acl_mode</code></td><td>0</td></tr>
</tbody></table>
<p style="margin-top:8px">Les programmes externes peuvent s'enregistrer sans restriction.
 Voir la configuration dans <a href="/sap/gw/reginfo">/sap/gw/reginfo</a>.</p></section>
</div><div>
<section class="wp"><h2>Enregistrer un programme (TP)</h2>
<form class="form" method="post" action="/sap/gw/register">
 <div class="field"><label for="tp">Nom du programme (TP_NAME)</label>
  <input class="in" id="tp" name="tp" placeholder="ex. Z_RFC_EXPORT" value="" autofocus></div>
 <div class="btns"><button class="btn" type="submit">Enregistrer</button></div>
</form></section>
</div></div>"""


def monitor_page():
    return shell("Moniteur", MONITOR_BODY)

REGINFO = """# reginfo, Gateway registration ACL (DFL / sapgw00)
#
# Format: P TP=<program> HOST=<host> ACCESS=<host> CANCEL=<host>
#
# (vide, aucune règle définie)
#
# NOTE Basis: ACL non configurée. Comportement par défaut = tout autorisé.
#   Tout programme externe peut s'enregistrer (P TP=* HOST=* ...).
#   À corriger: définir reginfo/secinfo (gw/reg_no_conn_info, gw/acl_mode=1).
"""


@app.get("/")
def monitor():
    return Response(monitor_page(), mimetype="text/html")


@app.get("/sap/gw/reginfo")
def reginfo():
    return Response(REGINFO, mimetype="text/plain")


@app.post("/sap/gw/register")
def register():
    tp = request.form.get("tp", "").strip()
    if not tp:
        return Response(monitor_page(), mimetype="text/html")
    # VULN (simulated): reginfo/secinfo are permissive, so any registration is
    # accepted. A real missing ACL would let an attacker register a malicious
    # RFC server; here it simply grants the flag.
    host = request.remote_addr or "0.0.0.0"
    conv = zlib.crc32((tp + host).encode()) % 90000000 + 10000000
    stamp = time.strftime("%d/%m/%Y %H:%M:%S")
    log = (f"{stamp}  GW REGISTER  TP={tp}  HOST={host}  CONV_ID={conv}\n"
           f"{stamp}  reg_info: aucune règle (gw/acl_mode=0) -> accepté\n"
           f"{stamp}  TP={tp}  STATE=REGISTERED  SNC=off")
    page = shell("Programme enregistré", f"""<h1 class="h1">Moniteur du gateway (SMGW)</h1>
<p class="status ok">Le programme <b>{escape(tp)}</b> est enregistré.</p>
<div class="cols"><div>
<section class="wp"><h2>Programmes externes enregistrés</h2>
<table class="list data"><thead><tr><th>TP_NAME</th><th style="width:130px">Hôte</th>
 <th style="width:110px">CONV_ID</th><th style="width:110px">État</th></tr></thead>
<tbody><tr><td>{escape(tp)}</td><td>{escape(host)}</td><td class="num">{conv}</td>
 <td><span class="pill ok">REGISTERED</span></td></tr></tbody></table></section>
<section class="wp"><h2>Trace du gateway (dev_rd)</h2><div class="log"><pre>{escape(log)}</pre></div></section>
</div><div>
<section class="wp"><h2>Clé d'enregistrement</h2>
<p class="mute" style="font-size:12px">Clé de session remise au programme enregistré.</p>
{intranet.codebox(FLAG)}</section>
<p><a href="/">Retour au moniteur</a></p>
</div></div>""")
    return Response(page, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
