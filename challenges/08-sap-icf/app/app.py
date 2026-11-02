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
from flask import Flask, Response, request, redirect

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f5f6f7;color:#1d2d3e;font:14px/1.45 "72","Segoe UI",Arial,system-ui,sans-serif}
a{color:#0064d9}
:focus-visible{outline:2px solid #0032a5;outline-offset:1px}
.shell{background:#fff;height:48px;display:flex;align-items:center;gap:12px;padding:0 16px;
 box-shadow:0 0 2px rgba(34,53,72,.2),0 2px 4px rgba(34,53,72,.2);position:relative;z-index:2}
.shell b{font-size:14px}.shell .sys{font-size:12px;color:#556b82}
.shell .av{margin-left:auto;width:32px;height:32px;border-radius:50%;background:#0070f2;
 color:#fff;display:grid;place-items:center;font-weight:700;font-size:12px}
.logon{max-width:400px;margin:56px auto;padding:0 16px}
.logon .box{background:#fff;border-radius:12px;padding:28px 28px 22px;
 box-shadow:0 0 0 1px rgba(34,53,72,.08),0 4px 16px rgba(34,53,72,.12)}
.logon h1{font-size:20px;font-weight:700;margin:0 0 2px}
.logon .sub{color:#556b82;margin:0 0 20px;font-size:13px}
label{display:block;font-size:13px;color:#556b82;margin:14px 0 4px}
input,select{width:100%;font:inherit;color:#131e29;background:#fff;border:1px solid #bcc3ca;
 border-bottom-color:#556b82;border-radius:4px;padding:7px 10px;height:36px}
input:focus,select:focus{outline:none;border-color:#0064d9;box-shadow:inset 0 -1px 0 #0064d9}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
button{font:inherit;font-weight:700;border:0;border-radius:8px;cursor:pointer}
.primary{width:100%;margin-top:22px;height:36px;background:#0070f2;color:#fff}
.primary:hover{background:#0064d9}
.msg{display:flex;gap:8px;align-items:flex-start;background:#ffeaf4;border:1px solid #ff8888;
 border-radius:8px;color:#aa0808;padding:8px 10px;margin-bottom:6px;font-size:13px}
.msg:empty{display:none}
.legal{color:#6a7d91;font-size:12px;text-align:center;margin-top:18px}
.layout{display:grid;grid-template-columns:240px 1fr;min-height:calc(100vh - 48px)}
.side{background:#fff;border-right:1px solid #e5e5e5;padding:12px 0;font-size:13px}
.side div{padding:6px 16px;color:#556b82}
.side div.on{background:#ebf8ff;color:#0064d9;font-weight:700;box-shadow:inset 3px 0 #0064d9}
.content{padding:20px 24px 48px;max-width:900px;min-width:0}
.content h1{font-size:20px;margin:0 0 4px}
.card{background:#fff;border-radius:12px;padding:18px 20px;margin:14px 0;
 box-shadow:0 0 0 1px rgba(34,53,72,.08),0 2px 4px rgba(34,53,72,.08)}
.card h2{font-size:15px;margin:0 0 10px}
.ok{display:inline-flex;gap:6px;align-items:center;background:#f5fae5;border:1px solid #30914c;
 color:#256f3a;border-radius:8px;padding:6px 10px;font-size:13px}
.flag{display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:#ebf8ff;
 border:1px solid #0070f2;border-radius:8px;padding:10px 12px}
.flag span{font-size:12px;font-weight:700;color:#0064d9;text-transform:uppercase}
.flag code{flex:1 1 220px;min-width:0;font-size:15px;font-weight:700;overflow-wrap:anywhere;user-select:all}
.flag button{background:#fff;color:#0064d9;border:1px solid #0064d9;padding:5px 12px;font-size:13px}
.tw{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:480px}
th{text-align:left;color:#556b82;font-weight:400;border-bottom:1px solid #e5e5e5;padding:8px 8px 8px 0}
td{border-bottom:1px solid #eee;padding:9px 8px 9px 0}
.st{font-size:12px;font-weight:700}.st.r{color:#aa0808}.st.g{color:#256f3a}.st.n{color:#556b82}
pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;font:12.5px/1.55 ui-monospace,Menlo,Consolas,monospace;color:#1d2d3e}
code{font-family:ui-monospace,Menlo,Consolas,monospace}
@media(max-width:720px){.layout{grid-template-columns:minmax(0,1fr)}.side{display:none}.content{padding:16px}}
"""

VP = '<meta name="viewport" content="width=device-width,initial-scale=1">'

COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copié \u2713';setTimeout(function(){b.textContent='Copier'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

def launchpad(form_msg="", client="001", user=""):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">{VP}
<title>SAP DFlop ERP — Connexion</title><style>{CSS}</style></head><body>
<div class="shell"><b>SAP DFlop ERP</b><span class="sys">NetWeaver Fiori Launchpad</span></div>
<main class="logon"><div class="box">
 <h1>Connexion</h1>
 <p class="sub">Système DFL · Production</p>
 <div class="msg" role="alert">{form_msg}</div>
 <form method="post" action="/sap/bc/ui2/logon">
   <div class="pair">
    <div><label for="c">Mandant</label>
     <input id="c" name="client" value="{escape(client)}" inputmode="numeric" autocomplete="off"></div>
    <div><label for="l">Langue</label>
     <select id="l" name="lang"><option>FR</option><option>EN</option><option>DE</option></select></div>
   </div>
   <label for="u">Utilisateur</label>
   <input id="u" name="user" value="{escape(user)}" autofocus autocomplete="off"
    autocapitalize="characters" autocorrect="off" spellcheck="false">
   <label for="p">Mot de passe</label>
   <input id="p" name="password" type="password" autocomplete="off">
   <button class="primary">Se connecter</button>
 </form>
</div>
<p class="legal">Système de production DFL. Tout accès non autorisé est interdit.</p>
</main></body></html>"""

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
  NOTE_FROM_BASIS   = "Constat d'audit : l'utilisateur d'urgence SAP* a été
                       SUPPRIMÉ du mandant 001 la semaine dernière et jamais
                       recréé. Tant que Basis ne l'a pas recréé, les connexions
                       en SAP* retombent sur le comportement par défaut du
                       noyau. À corriger d'urgence
                       (login/no_automatic_user_sapstar=1)."
</SAP:SYSINFO>
"""

def admin_page():
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">{VP}
<title>DFL — SAP GUI</title><style>{CSS}</style></head><body>
<div class="shell"><b>SAP Easy Access</b><span class="sys">DFL (001) · SAP*</span>
 <div class="av" aria-label="Utilisateur SAP*">S*</div></div>
<div class="layout">
 <nav class="side" aria-label="Menu"><div>Favoris</div><div>Bureautique</div>
  <div>Logistique</div><div>Ressources humaines</div><div>Outils</div>
  <div class="on">SU01 · Gestion des utilisateurs</div><div>SE16 · Navigateur de données</div></nav>
 <main class="content">
  <h1>Connecté au mandant 001 en tant que SAP*</h1>
  <span class="ok">✓ Connexion réussie</span>
  <div class="card"><div class="flag"><span>Flag</span><code id="flag">{FLAG}</code>
   <button type="button" onclick="copyFlag(this)">Copier</button></div>
   <p style="margin:12px 0 0">Vous avez utilisé la porte dérobée SAP* du noyau (mot de passe par défaut
   06071992), car l'utilisateur SAP* a été supprimé du mandant 001 et jamais recréé.</p></div>
  <div class="card"><h2>Transaction SU01 — utilisateurs concernés du mandant 001</h2>
   <div class="tw"><table><thead><tr><th>Utilisateur</th><th>Nom</th><th>Rôle</th><th>Statut</th></tr></thead><tbody>
    <tr><td><code>RESULTS_ADMIN</code></td><td>—</td><td>compte de service</td><td class="st r">Verrouillé</td></tr>
    <tr><td><code>VLINDQVIST</code></td><td>Viktor Lindqvist</td><td>results_operator, créé il y a 3 jours</td><td class="st g">Actif</td></tr>
    <tr><td><code>MSORENSEN</code></td><td>Maria Sorensen</td><td>lecture seule</td><td class="st n">Actif</td></tr>
   </tbody></table></div></div>
  <div class="card"><h2>Étape suivante</h2>
   <p style="margin:0">La table officielle des résultats <code>ZRACE_RESULT</code> a été modifiée par
   l'un de ces utilisateurs. Pour prouver lequel, exportez la table des utilisateurs et mots de passe
   <code>USR02</code> et vérifiez les dernières connexions et les modifications. (Cet export est
   distribué séparément.)</p></div>
 </main>
</div>{COPY_JS}</body></html>"""

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

@app.get("/sap/bc/ui2/logon")
def logon_get():
    return redirect("/")

@app.post("/sap/bc/ui2/logon")
def logon():
    user = request.form.get("user", "").strip().upper()
    pw = request.form.get("password", "")
    client = request.form.get("client", "").strip()
    # VULN 2: SAP* backdoor active (SAP* missing in client 001)
    if client == "001" and user == "SAP*" and pw == "06071992":
        return Response(admin_page(), mimetype="text/html")
    return Response(launchpad("Nom ou mot de passe incorrect. Échec de la connexion.",
                              client=request.form.get("client", "001"),
                              user=request.form.get("user", "")),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
