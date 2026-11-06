#!/usr/bin/env python3
"""
14 · SAP · MEDIUM (Gateway reginfo/secinfo — missing ACL)
Simulated SAP Gateway monitor (transaction SMGW) inside a mock SAP GUI for HTML
shell. Based on a real, well-known SAP exposure: when the gateway's
reginfo/secinfo access-control lists are left at their permissive default,
unauthorized external programs can REGISTER with the gateway.

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

from flask import Flask, Response, redirect, render_template, request, session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("SAP_SECRET_KEY") or os.urandom(32)
# Flag comes from the environment only (set by scripts/gen-flags.sh through
# docker-compose as FLAG_14). Plain FLAG is kept as a fallback for older wiring.
FLAG = os.environ.get("FLAG_14") or os.environ.get("FLAG", "TRIATHLON{placeholder}")

# Level 3 (Basis Admin) SAP logon. These Basis credentials are intentionally
# discoverable by players: softly via the Intranet "Documentation Technique"
# wiki (the password-policy / legacy-account notes), and concretely via the
# .git leak in challenge 11. The logon is a narrative gate, not a brute-force
# puzzle, so the defaults below ship as-is and are read from env in production.
SAP_BASIS_USER = os.environ.get("SAP_BASIS_USER", "basis_dflop")
SAP_BASIS_PASS = os.environ.get("SAP_BASIS_PASS", "Trans1tion!2026")


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


# The gateway's registration ACL as exposed by the monitor. The single wildcard
# rule is the vulnerability: any host may register any program.
REGINFO = """# reginfo, Gateway registration ACL (DFL / sapgw00)
#
# Format: P TP=<program> HOST=<host> USER=<user> ACCESS=<host>
#
# NOTE Basis: ACL non configurée. Règle générique laissée par défaut.
#   Tout programme externe peut s'enregistrer depuis n'importe quel hôte.
#   À corriger: définir reginfo/secinfo (gw/reg_no_conn_info, gw/acl_mode=1).
#
P TP=* HOST=* USER=* ACCESS=*
"""

# Defaults shown in the registration form.
DEFAULT_TP = "Z_EXPLOIT_RFC"
DEFAULT_HOST = "10.0.0.42"


def smgw_page(**ctx):
    ctx.setdefault("reginfo", REGINFO)
    ctx.setdefault("tp", DEFAULT_TP)
    ctx.setdefault("host", DEFAULT_HOST)
    return sap_render("smgw.html", **ctx)


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
    "SMGW": "/sap/smgw",
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


# --------------------------------------------------------------------------
# SMGW: gateway monitor, ACL files and the (open) registration form.
# --------------------------------------------------------------------------
@app.get("/sap/smgw")
def smgw():
    return smgw_page()


@app.get("/sap/gw/reginfo")
def reginfo():
    # Raw ACL file, plain text (it never contains the flag).
    return Response(REGINFO, mimetype="text/plain")


@app.route("/sap/gw/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return redirect("/sap/smgw")
    tp = request.form.get("tp", "").strip()[:120]
    host = request.form.get("host", "").strip()[:120] or DEFAULT_HOST
    if not tp:
        return smgw_page(host=host, error_msg="Le nom du programme est obligatoire.")
    # VULN (simulated): reginfo is wide open, so ANY program name from ANY host
    # is accepted. A real missing ACL would let an attacker register a malicious
    # RFC server; here it simply reveals the flag.
    conv = zlib.crc32((tp + host).encode()) % 90000000 + 10000000
    stamp = time.strftime("%d.%m.%Y %H:%M:%S")
    log = (f"{stamp}  GW REGISTER  TP={tp}  HOST={host}  CONV_ID={conv}\n"
           f"{stamp}  reg_info: règle P TP=* HOST=* -> accepté\n"
           f"{stamp}  TP={tp}  STATE=REGISTERED  SNC=off")
    return smgw_page(tp=tp, host=host, registered=True, log=log, flag=FLAG)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
