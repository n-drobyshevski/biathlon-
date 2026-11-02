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

COPY_JS = """<script>
function copyFlag(b){var t=document.getElementById('flag').textContent.trim();
 function ok(){b.textContent='Copied \u2713';setTimeout(function(){b.textContent='Copy'},1500)}
 function legacy(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';
  a.style.opacity='0';document.body.appendChild(a);a.select();
  try{document.execCommand('copy');ok()}catch(e){}a.remove()}
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(ok,legacy)}
 else{legacy()}}
</script>"""

def shell(title, body, right=""):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<div class="strip"><div class="in"><span>Results Admin · authorized crew only</span>
<span>Final race — results lock at 16:00</span></div></div>
<header class="top"><div class="in">
 <a class="mark" href="/">DÉCA<i>FLOP</i><small>Results admin</small></a>
 <nav class="acct">{right}</nav>
</div></header>
{body}</body></html>"""

def FORM(msg="", username=""):
    # The typed username is kept (HTML-escaped) so players can tweak a payload
    # instead of retyping it. The SQL itself is still built from raw input.
    return shell("DécaFlop Results Admin", f"""<main class="page" style="max-width:460px">
<div class="panel">
 <h1 class="h">Sign in</h1>
 <p class="mute small" style="margin:0 0 18px">Official results management. Authorized crew only.</p>
 {msg}
 <form method="post" action="/login">
  <div class="field"><label for="u">Username</label>
   <input id="u" name="username" value="{escape(username)}" autofocus
    autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false"></div>
  <div class="field"><label for="p">Password</label>
   <input id="p" name="password" type="password" autocomplete="off"></div>
  <button class="btn blue wide">Sign in</button>
 </form>
</div>
<p class="small mute">Lost access? Ask the race office. Do not share crew accounts.</p>
</main>""")

STANDINGS = [("1", "Astrid Bjornsen", "0", "38:12.4"),
             ("2", "Mikkel Haugen", "2", "38:40.9"),
             ("3", "—", "—", "pending")]

def ok_page():
    rows = "".join(f"<tr><td>{r}</td><td>{n}</td><td>{m}</td><td>{t}</td></tr>"
                   for r, n, m, t in STANDINGS)
    return shell("Results Admin", f"""<main class="page">
<div class="crumb">results / dashboard</div>
<div class="panel">
 <h1 class="h">Signed in</h1>
 <p class="mute" style="margin:0">Results Admin dashboard.</p>
 <div class="flag"><span>Flag</span><code id="flag">{FLAG}</code>
  <button type="button" onclick="copyFlag(this)">Copy</button></div>
 <div class="log"><pre>RESULTS SYSTEM NOTICE
---------------------
The authoritative results live in the SAP DFlop ERP (table ZRACE_RESULT).
The web admin is only a front-end. To find WHO altered the final standings,
pull the SAP user table (USR02) from the ERP host.</pre></div>
</div>
<div class="panel">
 <h2 class="h">Final race · provisional</h2>
 <p class="small mute" style="margin:0 0 10px">Read-only mirror of SAP table ZRACE_RESULT.</p>
 <table class="std"><thead><tr><th>Rank</th><th>Athlete</th><th>Misses</th><th>Time</th></tr></thead>
 <tbody>{rows}</tbody></table>
</div>
</main>{COPY_JS}""", right='<a href="/">Sign out</a>')

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
        return Response(FORM(msg=f'<div class="note db" role="alert"><b>Database error</b>'
                             f'<pre>SQL error: {escape(str(e))}</pre></div>',
                             username=u),
                        mimetype="text/html")
    if row:
        return Response(ok_page(), mimetype="text/html")
    return Response(FORM(msg='<div class="note err" role="alert">Invalid credentials.</div>',
                         username=u),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
