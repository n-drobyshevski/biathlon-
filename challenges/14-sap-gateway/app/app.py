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
import hmac
import os
import sys
import time
import zlib
from html import escape

from flask import Flask, Response, redirect, render_template, request, session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("SAP_SECRET_KEY") or os.urandom(32)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# Level 3 (Basis Admin) SAP logon. These Basis credentials are intentionally
# discoverable by players: softly via the Intranet "Documentation Technique"
# wiki (the password-policy / legacy-account notes), and concretely via the
# .git leak in challenge 11. The logon is a narrative gate, not a brute-force
# puzzle, so the defaults below ship as-is and are read from env in production.
SAP_BASIS_USER = os.environ.get("SAP_BASIS_USER", "basis_dflop")
SAP_BASIS_PASS = os.environ.get("SAP_BASIS_PASS", "Trans1tion!2026")

PRODUCT = "SAP DFlop ERP, système DFL, noyau 753"


def sap_render(template, status=200, **ctx):
    """Render a SAP-shell template, injecting the clock and the host-aware
    link to the Intranet wiki (works on raw IPs and online subdomains)."""
    ctx.setdefault("sap_time", time.strftime("%d.%m.%Y %H:%M:%S"))
    ctx.setdefault("wiki_url", intranet.app_url("intranet", "/wiki", "sapgw"))
    return Response(render_template(template, **ctx), status=status, mimetype="text/html")


# Paths under /sap/ that stay reachable without a SAP session.
SAP_OPEN_PREFIXES = ("/sap/static/",)
SAP_OPEN_EXACT = ("/sap/logon", "/sap/_preview")


@app.before_request
def sap_auth_gate():
    path = request.path
    if not path.startswith("/sap/"):
        return None
    if path in SAP_OPEN_EXACT or any(path.startswith(p) for p in SAP_OPEN_PREFIXES):
        return None
    if not session.get("sap_authenticated"):
        return redirect("/sap/logon")
    return None


def shell(title, body):
    return intranet.page(f"{title} - Gateway SAP DFL", body, app="sapgw",
                         site_title="Gateway SAP DFL", site_href="/", logo="GW",
                         topnav=[("/sap/gw/register", "Moniteur (SMGW)", True),
                                 ("/sap/gw/reginfo", "reginfo", False)],
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
def root():
    # The system root enters the SAP shell (which gates to the logon screen).
    return redirect("/sap/menu")


# --------------------------------------------------------------------------
# Level 3 logon (Basis Admin). Credentials above; gate is sap_auth_gate().
# --------------------------------------------------------------------------
@app.route("/sap/logon", methods=["GET", "POST"])
def sap_logon():
    if session.get("sap_authenticated"):
        return redirect("/sap/menu")
    if request.method == "POST":
        user = request.form.get("user", "")
        pw = request.form.get("pass", "")
        # Constant-time compare; never reveal which field was wrong.
        if hmac.compare_digest(user, SAP_BASIS_USER) and hmac.compare_digest(pw, SAP_BASIS_PASS):
            session["sap_authenticated"] = True
            session["sap_user"] = user
            return redirect("/sap/menu")
        return sap_render("sap_login.html", status=401, error=True)
    return sap_render("sap_login.html", error=False)


@app.get("/sap/menu")
def sap_menu():
    return sap_render("sap_menu.html", sap_user=session.get("sap_user", ""))


# Transaction codes a player can type in the command field.
TCODE_MAP = {
    "SMGW": "/sap/gw/reginfo",
    "SE16N": "/sap/se16n?table=USR02",
    "SM37": "/sap/sm37",
    "SU01": "/sap/se16n?table=USR02",
}


@app.get("/sap/cmd")
def sap_cmd():
    code = request.args.get("cmd", "").strip().lstrip("/").upper()
    dest = TCODE_MAP.get(code)
    if dest:
        return redirect(dest)
    return sap_render("sap_message.html", status=200,
                      status_class_val="sap-statusbar--error",
                      status_msg_val="La transaction n'existe pas.")


@app.get("/sap/se16n")
def sap_se16n():
    return sap_render("sap_se16n.html", table=request.args.get("table", ""))


@app.get("/sap/sm37")
def sap_sm37():
    return sap_render("sap_sm37.html")


@app.get("/sap/gw/reginfo")
def reginfo():
    return Response(REGINFO, mimetype="text/plain")


@app.route("/sap/gw/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        # The gateway monitor (SMGW): status, security state, reginfo link
        # and the registration form that posts back here.
        return Response(monitor_page(), mimetype="text/html")
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
<p><a href="/sap/gw/register">Retour au moniteur</a></p>
</div></div>""")
    return Response(page, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
