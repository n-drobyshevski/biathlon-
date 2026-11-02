#!/usr/bin/env python3
"""
06 · Web · MEDIUM (SQL injection — auth bypass)
DécaFlop Results Admin. The login builds its SQL by string concatenation, so a
classic injection logs you in without a password.

Example:  username =  ' OR '1'='1' --        password = anything
Teaches: SQL injection, auth bypass, why you parameterize queries.
"""
import os, sqlite3
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
 font-weight:700;cursor:pointer}pre{white-space:pre-wrap;color:#e9d7ff}"""

def FORM(msg=""):
    return f"""<!doctype html><meta charset="utf-8"><title>DécaFlop Results Admin</title>
<style>{CSS}</style>
<header><h1>🎯 DécaFlop · Results Admin</h1></header>
<main><div class="card">
<p>Official results management. Authorized crew only.</p>
<form method="post" action="/login">
 <label>Username</label><input name="username" autofocus>
 <label>Password</label><input name="password" type="password">
 <button>Sign in</button>
</form>
{msg}
</div></main>"""

def ok_page():
    return f"""<!doctype html><meta charset="utf-8"><title>Results Admin</title>
<style>{CSS}</style><header><h1>🎯 Results Admin — signed in</h1></header>
<main><div class="card">
<h2>✅ Authenticated</h2>
<pre>FLAG: {FLAG}

RESULTS SYSTEM NOTICE
---------------------
The authoritative results live in the SAP DFlop ERP (table ZRACE_RESULT).
The web admin is only a front-end. To find WHO altered the final standings,
pull the SAP user table (USR02) from the ERP host.</pre>
</div></main>"""

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
        return Response(FORM(msg=f"<pre>SQL error: {e}</pre>"),
                        mimetype="text/html")
    if row:
        return Response(ok_page(), mimetype="text/html")
    return Response(FORM(msg="<pre>Invalid credentials.</pre>"),
                    mimetype="text/html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
