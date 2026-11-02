#!/usr/bin/env python3
"""
12 · Web · HARD (Server-Side Template Injection)
DécaFlop's finisher-certificate generator drops the name you type straight into
a Jinja2 template string, so template syntax in the name is evaluated on the
server. Inject an expression to read the app's config, where the flag lives.

Teaches: SSTI, confirming it (`{{7*7}}`), reaching objects through the template
engine (`{{config}}`), the difference between rendering data and rendering a
template built from user input.

Self-contained training app — intentionally vulnerable. The flag sits in
app.config; the container is the sandbox.
"""
import os

from flask import Flask, Response, render_template_string, request

app = Flask(__name__)
app.config["FLAG"] = os.environ.get("FLAG", "TRIATHLON{placeholder}")

CSS = """body{font-family:system-ui,sans-serif;background:#f4f6f8;color:#1b2733;margin:0;line-height:1.6}
header{background:#143d2b;color:#eafff3;padding:20px 24px;border-bottom:4px solid #19c37d}
main{max-width:640px;margin:32px auto;padding:0 18px}
.card{background:#fff;border:1px solid #d7dde3;border-radius:10px;padding:22px;margin:14px 0}
input{width:100%;padding:10px;border:1px solid #9aa6b2;border-radius:6px;box-sizing:border-box;font:inherit}
button{margin-top:12px;background:#19c37d;color:#04281c;border:0;padding:10px 18px;border-radius:6px;font-weight:700;cursor:pointer}
.cert{border:3px double #143d2b;border-radius:8px;padding:28px;text-align:center;margin-top:8px;background:#fbfdfb}
.cert h2{margin:0 0 6px;color:#143d2b}.cert .big{font-size:26px;font-weight:800;margin:10px 0;color:#0b6e4f}
code{font-family:ui-monospace,Menlo,Consolas,monospace}h1{margin:0;font-size:22px}"""

FORM = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DécaFlop · Certificat de finaliste</title><style>{css}</style></head><body>
<header><h1>🏅 DécaFlop · Certificat de finaliste</h1></header>
<main><div class="card">
<p>Générez votre certificat de finaliste de la finale 2026. Entrez votre nom
tel qu'il doit apparaître sur le certificat.</p>
<form method="post" action="/generate">
 <label for="n">Nom du finaliste</label>
 <input id="n" name="name" value="Astrid Bjornsen" autofocus>
 <button>Générer le certificat</button>
</form></div>{result}</main></body></html>"""


def page(result=""):
    return FORM.replace("{css}", CSS).replace("{result}", result)


@app.get("/")
def home():
    return Response(page(), mimetype="text/html")


@app.post("/generate")
def generate():
    name = request.form.get("name", "")
    # VULN: user input becomes part of the template source (SSTI), instead of
    # being passed as a value to a fixed template.
    cert = render_template_string(
        '<div class="cert"><h2>Certificat de finaliste</h2>'
        '<div class="big">' + name + '</div>'
        '<p>a terminé le Championnat régional de triathlon · DécaFlop 2026</p></div>')
    return Response(page(f'<div class="card">{cert}</div>'), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
