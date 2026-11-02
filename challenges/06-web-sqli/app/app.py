#!/usr/bin/env python3
"""
06 · Web · MEDIUM (SQL injection — auth bypass)
DécaFlop Results Admin. The login builds its SQL by string concatenation, so a
classic injection logs you in without a password.

Example:  username =  ' OR '1'='1' --        password = anything
Teaches: SQL injection, auth bypass, why you parameterize queries.
"""
import os, sqlite3
from html import escape
from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "BIATHLON{placeholder}")

def db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users(username TEXT, password TEXT, role TEXT)")
    con.executemany(
        "INSERT INTO users VALUES(?,?,?)",
        [("results_admin", "s3cr3t-do-not-share-9912", "admin"),
         ("v.lindqvist",   "Lane7Lane7!",             "results_operator")],
    )
    con.commit()
    return con

CSS = """body{font-family:system-ui,sans-serif;background:#1a1420;color:#f3e9ff;margin:0}
header{background:#120d18;padding:22px 36px;border-bottom:3px solid #c77dff}
main{max-width:520px;margin:48px auto;padding:0 18px}
.card{background:#2a2033;border:1px solid #5a3f73;border-radius:10px;padding:22px}
input{width:100%;padding:10px;margin:6px 0 14px;border-radius:6px;border:1px solid #5a3f73;
 background:#17121d;color:#f3e9ff;box-sizing:border-box}
button{background:#c77dff;color:#120d18;border:0;padding:10px 18px;border-radius:6px;
 font-weight:700;cursor:pointer}pre{white-space:pre-wrap;color:#e9d7ff}
*{box-sizing:border-box}body{line-height:1.55}
header{padding:18px 20px}header .in{max-width:520px;margin:0 auto;display:flex;
 flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
header h1{margin:0;font-size:22px}header a{color:#e9d7ff;font-size:14px}
label{display:block;font-weight:600;font-size:14px}
input:focus{outline:none;border-color:#c77dff;box-shadow:0 0 0 3px rgba(199,125,255,.35)}
button{width:100%;font-size:15px}button:hover{filter:brightness(1.1)}
a:focus-visible,button:focus-visible{outline:3px solid #ffd166;outline-offset:2px}
.alert{margin-top:16px;border-radius:6px;padding:10px 12px;font-size:14px}
.alert pre{margin:6px 0 0;font-size:13px;overflow-wrap:anywhere}
.alert.err{background:#3d1622;border:1px solid #a33a55;color:#ffc9d6}
.alert.db{background:#3a2c10;border:1px solid #a07a22;color:#ffe2a3}
.flag{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0;
 background:#17121d;border:1px solid #c77dff;border-radius:8px;padding:10px 12px}
.flag code{flex:1;min-width:0;overflow-wrap:anywhere;user-select:all;color:#fff}
.flag button{width:auto;font-size:13px;padding:6px 12px}
.ok{color:#9ff0c0;margin-top:0}"""

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

def FORM(msg="", username=""):
    # The typed username is kept (HTML-escaped) so players can tweak a payload
    # instead of retyping it. The SQL itself is still built from raw input.
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">{VP}
<title>DécaFlop Results Admin</title>
<style>{CSS}</style>
<header><div class="in"><h1>🎯 DécaFlop · Results Admin</h1></div></header>
<main><div class="card">
<p style="margin-top:0">Official results management. Authorized crew only.</p>
<form method="post" action="/login">
 <label for="u">Username</label>
 <input id="u" name="username" value="{escape(username)}" autofocus
  autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false">
 <label for="p">Password</label>
 <input id="p" name="password" type="password" autocomplete="off">
 <button>Sign in</button>
</form>
{msg}
</div></main>"""

def ok_page():
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">{VP}
<title>Results Admin</title>
<style>{CSS}</style><header><div class="in"><h1>🎯 Results Admin — signed in</h1>
<a href="/">Sign out</a></div></header>
<main><div class="card">
<h2 class="ok">✅ Authenticated</h2>
<div class="flag"><b>FLAG</b> <code id="flag">{FLAG}</code>
 <button type="button" onclick="copyFlag(this)">Copy</button></div>
<pre>RESULTS SYSTEM NOTICE
---------------------
The authoritative results live in the SAP DFlop ERP (table ZRACE_RESULT).
The web admin is only a front-end. To find WHO altered the final standings,
pull the SAP user table (USR02) from the ERP host.</pre>
</div></main>{COPY_JS}"""

@app.get("/")
def home():
    return Response(FORM(msg=""), mimetype="text/html")

@app.post("/login")
def login():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    # VULN: raw string interpolation -> SQL injection
    q = f"SELECT role FROM users WHERE username = '{u}' AND password = '{p}'"
    try:
        row = db().execute(q).fetchone()
    except sqlite3.Error as e:
        return Response(FORM(msg=f'<div class="alert db" role="alert"><b>Database error</b>'
                             f'<pre>SQL error: {escape(str(e))}</pre></div>',
                             username=u),
                        mimetype="text/html")
    if row:
        return Response(ok_page(), mimetype="text/html")
    return Response(FORM(msg='<div class="alert err" role="alert">Invalid credentials.</div>',
                         username=u),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
