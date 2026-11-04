#!/usr/bin/env python3
"""
11 · Web · HARD (source disclosure via exposed .git)
DécaFlop's timing site was deployed with its whole ".git" directory served to
the web. Dump it, read the history, and recover a secret (the flag) that was
removed in a later commit — git keeps the old version.

Teaches: .git exposure, dumping it (wget -r / git-dumper), reading history
(git log / git show), that deleting a secret in a new commit doesn't erase it.

Self-contained training app. The repo (with the flag in an old commit) is built
at startup by entrypoint.sh; this app just serves the webroot — INCLUDING the
.git directory and with directory listing, which is the vulnerability.
"""
import html
import os
import sys
import time
from urllib.parse import quote

from flask import Flask, Response, abort, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling fab.py
import fab  # noqa: E402

app = Flask(__name__)
SITE = os.path.realpath(os.environ.get("SITE_DIR", "/srv/site"))


def autoindex(urlpath, fsdir):
    """Directory listing in the format of nginx's autoindex (name, date, size)."""
    title = f"Index of /{html.escape(urlpath)}"
    lines = ['<a href="../">../</a>'] if urlpath.strip("/") else []
    names = sorted(os.listdir(fsdir))
    dirs = [n for n in names if os.path.isdir(os.path.join(fsdir, n))]
    files = [n for n in names if n not in dirs]
    for name in dirs + files:
        full = os.path.join(fsdir, name)
        is_dir = name in dirs
        shown = name + ("/" if is_dir else "")
        label = shown if len(shown) <= 50 else shown[:47] + "..>"
        pad = " " * (51 - len(label))
        st = os.stat(full)
        date = time.strftime("%d-%b-%Y %H:%M", time.gmtime(st.st_mtime))
        size = "-" if is_dir else str(st.st_size)
        lines.append(f'<a href="{html.escape(quote(shown))}">{html.escape(label)}</a>{pad}{date} {size:>19}')
    body = (f"<html>\r\n<head><title>{title}</title></head>\r\n<body>\r\n"
            f"<h1>{title}</h1><hr><pre>" + "\r\n".join(lines) + "\r\n</pre><hr></body>\r\n</html>\r\n")
    return Response(body, mimetype="text/html")


@app.get("/")
@app.get("/<path:p>")
def serve(p="index.html"):
    full = os.path.realpath(os.path.join(SITE, p))
    if full != SITE and not full.startswith(SITE + os.sep):   # no traversal outside the webroot
        abort(404)
    if os.path.isdir(full):
        idx = os.path.join(full, "index.html")
        if os.path.isfile(idx) and p in ("", "index.html"):
            return site_page(idx)
        return autoindex(p.rstrip("/") + ("/" if p.strip("/") else ""), full)
    if full == os.path.join(SITE, "index.html"):
        return site_page(full)
    if os.path.isfile(full):
        return send_from_directory(SITE, os.path.relpath(full, SITE))
    abort(404)


def site_page(path):
    """The timing site's home page, with the game's floating shortcuts (fab.py:
    cellule de crise, Outils, intranet once unlocked). Only this page: the .git
    files and listings players dump are served exactly as they are."""
    with open(path, encoding="utf-8") as fh:
        page = fh.read()
    return Response(fab.inject(page, fab.render("challenge", fab.default_urls())), mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
