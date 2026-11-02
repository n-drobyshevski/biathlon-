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
import sys

from flask import Flask, Response, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

app = Flask(__name__)
app.config["FLAG"] = os.environ.get("FLAG", "TRIATHLON{placeholder}")

FORM = """<h1 class="h1">Certificat de finaliste</h1>
<p class="lead">Générez le certificat d'un finaliste de la finale 2026. Saisissez le nom tel qu'il doit
 apparaître sur le certificat (prénom puis nom).</p>
<form class="form noprint" method="post" action="/generate">
 <div class="field"><label for="n">Nom du finaliste</label>
  <input class="in" id="n" name="name" value="Astrid Bjornsen" autofocus>
  <span class="hint">Les certificats sont imprimés au village partenaires (imprimante PRN-VIL-02).</span></div>
 <div class="btns"><button class="btn" type="submit">Générer le certificat</button></div>
</form>"""


def page(result=""):
    # `result` is already-rendered HTML; it is concatenated, never re-templated.
    body = FORM + result
    return intranet.page("Certificat de finaliste - DécaFlop", body, app="certificats",
                         site_title="Certificats de finaliste", site_href="/", logo="CF",
                         topnav=[("/", "Nouveau certificat", True)],
                         product="Certificats 1.3.0", foot_extra="Finale 2026, village partenaires")


@app.get("/")
def home():
    return Response(page(), mimetype="text/html")


@app.post("/generate")
def generate():
    name = request.form.get("name", "")
    # VULN: user input becomes part of the template source (SSTI), instead of
    # being passed as a value to a fixed template.
    cert = render_template_string(
        '<div class="cert"><div class="in-cert"><div class="org">DÉCA<i>FLOP</i></div>'
        '<h3>Certificat de finaliste</h3><p>Le Championnat régional de triathlon certifie que</p>'
        '<div class="name">' + name + '</div>'
        '<p>a terminé la finale régionale 2026.</p>'
        '<div class="sig"><span>Direction de course</span><span>Partenaire titre DécaFlop</span></div>'
        '</div></div>')
    return Response(page('<h2 class="h2">Aperçu</h2>' + cert +
                         '<div class="btns noprint"><button class="btn sec" type="button" '
                         'onclick="window.print()">Imprimer</button></div>'), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
