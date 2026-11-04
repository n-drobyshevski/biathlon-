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

Player isolation: SSTI is code execution inside the app, and one instance is
shared by every team. So each certificate is rendered in a throwaway child
process (fork): whatever a payload changes (config.update(FLAG=...), swapped
view functions, monkeypatched modules) dies with that child, and the next
request starts from the pristine parent again. The child gets a CPU limit, a
wall-clock timeout and its whole process group is killed afterwards, so a busy
loop or a background `yes` cannot pin the Pi either. At most RENDER_SLOTS
renders run at once (RENDER_PER_CLIENT per client address), and every child
volunteers as the out-of-memory killer's first victim: a flood of heavy
payloads costs its sender a "busy" page, never the app itself.
"""
import os
import resource
import select
import signal
import sys
import threading
import time
import warnings
from html import escape

from flask import Flask, Response, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402
import fab  # noqa: E402

app = Flask(__name__)
app.config["FLAG"] = os.environ.get("FLAG", "TRIATHLON{placeholder}")


# Out of the story: the game's floating shortcuts (fab.py) on every HTML page
# (cellule de crise, Outils, and the intranet once the player has logged in to it).
@app.after_request
def shortcuts(resp):
    return fab.add(resp, "challenge")

RENDER_TIMEOUT = 3.0          # seconds of wall clock per certificate
RENDER_CPU = 2                # seconds of CPU per certificate (RLIMIT_CPU)
RENDER_MAX = 2 * 1024 * 1024  # bytes of rendered output kept
RENDER_SLOTS = 4              # children alive at once (each copies ~20 MB on write)
RENDER_PER_CLIENT = 2         # of which one client address may hold

_slots = threading.BoundedSemaphore(RENDER_SLOTS)
_per_client, _per_client_lock = {}, threading.Lock()

# The child only renders and exits, so forking from the threaded dev server is
# fine here; silence Python 3.12's generic "multi-threaded fork" warning.
warnings.filterwarnings("ignore", message=r".*use of fork\(\) may lead to deadlocks.*",
                        category=DeprecationWarning)

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


def _render_isolated(source):
    """Render `source` in a forked child; return (ok, text).

    Runs inside the request context (the forked thread keeps it), so the
    template sees the same `config`, `request`, ... as before. Nothing the
    template does can outlive the child.
    """
    rfd, wfd = os.pipe()
    try:
        pid = os.fork()
    except OSError:                                       # pids cap reached: just "busy"
        os.close(rfd)
        os.close(wfd)
        return False, "busy"
    if pid == 0:                                          # ---- child
        try:
            os.close(rfd)
            os.setsid()                                   # own process group, killed below
            try:                                          # under memory pressure, kill me,
                with open("/proc/self/oom_score_adj", "w") as fh:   # never the app
                    fh.write("1000")
            except OSError:
                pass
            resource.setrlimit(resource.RLIMIT_CPU, (RENDER_CPU, RENDER_CPU))
            try:
                out = b"\x00" + render_template_string(source).encode("utf-8", "replace")
            except Exception as e:                        # template error: report it, no traceback
                out = b"\x01" + type(e).__name__.encode()
            with os.fdopen(wfd, "wb") as w:
                w.write(out[:RENDER_MAX + 1])
        finally:
            os._exit(0)
    # ---- parent
    os.close(wfd)
    chunks, size, deadline = [], 0, time.monotonic() + RENDER_TIMEOUT
    try:
        while size <= RENDER_MAX:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([rfd], [], [], left)[0]:
                break                                     # timed out
            b = os.read(rfd, 65536)
            if not b:
                break                                     # child done
            chunks.append(b)
            size += len(b)
    finally:
        os.close(rfd)
        try:
            os.killpg(pid, signal.SIGKILL)                # the child and anything it spawned
        except (ProcessLookupError, PermissionError):
            pass
        os.waitpid(pid, 0)
    data = b"".join(chunks)
    if not data:
        return False, "timeout"
    if data[:1] == b"\x01":
        return False, data[1:].decode("utf-8", "replace")
    return True, data[1:RENDER_MAX + 1].decode("utf-8", "replace")


def _take_slot(client):
    with _per_client_lock:
        if _per_client.get(client, 0) >= RENDER_PER_CLIENT:
            return False
        _per_client[client] = _per_client.get(client, 0) + 1
    if _slots.acquire(timeout=RENDER_TIMEOUT):
        return True
    _give_slot(client, release=False)
    return False


def _give_slot(client, release=True):
    if release:
        _slots.release()
    with _per_client_lock:
        n = _per_client.get(client, 1) - 1
        if n > 0:
            _per_client[client] = n
        else:
            _per_client.pop(client, None)


def _busy():
    return Response(page('<p class="status err" role="alert">Le générateur est occupé. '
                         'Réessayez dans quelques secondes.</p>'), status=503, mimetype="text/html")


@app.post("/generate")
def generate():
    name = request.form.get("name", "")
    client = request.remote_addr or "?"
    if not _take_slot(client):
        return _busy()
    try:
        return _generate(name)
    finally:
        _give_slot(client)


def _generate(name):
    # VULN: user input becomes part of the template source (SSTI), instead of
    # being passed as a value to a fixed template.
    ok, cert = _render_isolated(
        '<div class="cert"><div class="in-cert"><div class="org">DÉCA<i>FLOP</i></div>'
        '<h3>Certificat de finaliste</h3><p>Le Championnat régional de triathlon certifie que</p>'
        '<div class="name">' + name + '</div>'
        '<p>a terminé la finale régionale 2026.</p>'
        '<div class="sig"><span>Direction de course</span><span>Partenaire titre DécaFlop</span></div>'
        '</div></div>')
    if not ok:
        if cert == "busy":
            return _busy()
        msg = ("La génération a pris trop de temps et a été interrompue." if cert == "timeout"
               else f"Le modèle du certificat n'a pas pu être généré ({escape(cert)}).")
        return Response(page(f'<p class="status err" role="alert">{msg}</p>'), status=500,
                        mimetype="text/html")
    return Response(page('<h2 class="h2">Aperçu</h2>' + cert +
                         '<div class="btns noprint"><button class="btn sec" type="button" '
                         'onclick="window.print()">Imprimer</button></div>'), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
