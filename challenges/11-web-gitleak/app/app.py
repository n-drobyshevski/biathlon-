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

from flask import Flask, Response, abort, send_from_directory

app = Flask(__name__)
SITE = os.path.realpath(os.environ.get("SITE_DIR", "/srv/site"))


def autoindex(urlpath, fsdir):
    entries = sorted(os.listdir(fsdir))
    rows = ['<li><a href="../">../</a></li>'] if urlpath.strip("/") else []
    for name in entries:
        slash = "/" if os.path.isdir(os.path.join(fsdir, name)) else ""
        rows.append(f'<li><a href="{html.escape(name)}{slash}">{html.escape(name)}{slash}</a></li>')
    body = (f"<!doctype html><meta charset='utf-8'><title>Index of /{html.escape(urlpath)}</title>"
            f"<h2>Index of /{html.escape(urlpath)}</h2><ul>{''.join(rows)}</ul>")
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
            return send_from_directory(SITE, "index.html")
        return autoindex(p.rstrip("/") + ("/" if p.strip("/") else ""), full)
    if os.path.isfile(full):
        return send_from_directory(SITE, os.path.relpath(full, SITE))
    abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
