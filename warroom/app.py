#!/usr/bin/env python3
"""
War Room: the finale of "Operation Derniere Transition".

Players pool what the Web, Forensics and SAP tracks found into one incident
report. Only when ALL four fields are right does the server reveal the
Grandmaster Flag (FLAG_FINALE, from the environment). A wrong report only says
HOW MANY fields are right, never which ones, so teams have to compare notes.

Answers are matched as whole answers (case-insensitive, trimmed, inner spaces
collapsed), never as "contains", so a long answer stuffed with keywords cannot
pass a field. Accepted answers come from the environment with defaults below.

The rogue device (MAC / IP of challenge 08) is read from the SAME env var names
with the SAME defaults as handouts/generate.py (ROGUE_MAC / ROGUE_IP). A
service cannot import another service's code (each Docker build only sees its
own folder), so tests/test_warroom.py fails if the two ever diverge.

Listens on port 8099. In production run it with gunicorn (see Dockerfile) using
ONE worker: the rate-limit counters live in memory and must be shared.
"""
import math
import os
import re
import threading
import time
from collections import deque

from flask import Flask, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024            # four short text fields
# Behind a reverse proxy / tunnel every player would share the proxy's address
# and one 5/minute budget. Set WARROOM_TRUST_PROXY=1 ONLY when a proxy you control
# sets X-Forwarded-For, otherwise the header can be forged to dodge the limit.
if os.environ.get("WARROOM_TRUST_PROXY") == "1":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)


# --------------------------------------------------------------------------
# Accepted answers (env overrides are comma-separated lists)
# --------------------------------------------------------------------------
def _env_list(name, default):
    raw = os.environ.get(name)
    items = [x.strip() for x in raw.split(",") if x.strip()] if raw else []
    return items or list(default)


# a) the saboteur: SAP user from challenge 09, name from 09 / 03
SABOTEUR_ANSWERS = _env_list("WARROOM_SABOTEUR", ["VLINDQVIST", "Viktor Lindqvist", "V.LINDQVIST"])
# b) the attack vector (challenges 14 / 09)
VECTOR_ANSWERS = _env_list("WARROOM_VECTOR", ["SAP Gateway", "Passerelle SAP", "reginfo", "USR02", "OData", "RFC"])
# c) the incident minute (challenge 03 EXIF is 18:42:11; any seconds are fine)
INCIDENT_DATE = os.environ.get("WARROOM_INCIDENT_DATE", "2026-11-01")
INCIDENT_TIME = os.environ.get("WARROOM_INCIDENT_TIME", "18:42")
# d) the phantom device (challenge 08): same names and defaults as handouts/generate.py
ROGUE_MAC = os.environ.get("ROGUE_MAC", "aa:bb:cc:dd:ee:42")
ROGUE_IP = os.environ.get("ROGUE_IP", "10.10.0.42")


def _norm(text):
    return " ".join(text.casefold().split())


def check_saboteur(value):
    return _norm(value) in {_norm(a) for a in SABOTEUR_ANSWERS}


def check_vector(value):
    return _norm(value) in {_norm(a) for a in VECTOR_ANSWERS}


def check_time(value):
    """18:42, 18:42:11, 18h42, 2026-11-01 18:42, 2026:11:01 18:42:11 (EXIF), 01/11/2026 18:42."""
    want_h, want_m = (int(x) for x in INCIDENT_TIME.split(":")[:2])
    m = re.fullmatch(r"(?:(?P<date>[0-9/:.\-]{8,10})[ t]+)?(?P<h>\d{1,2})[:h](?P<m>\d{2})"
                     r"(?::\d{2}(?:[.,]\d+)?)?", _norm(value))
    if not m or (int(m["h"]), int(m["m"])) != (want_h, want_m):
        return False
    if m["date"]:
        y, mo, d = (int(x) for x in INCIDENT_DATE.split("-"))
        got = tuple(int(x) for x in re.findall(r"\d+", m["date"]))
        return got in {(y, mo, d), (d, mo, y)}            # 2026-11-01 or 01/11/2026
    return True


def _mac_digits(text):
    return re.sub(r"[\s:.\-]", "", text).lower()


def check_device(value):
    v = value.strip()
    if v == ROGUE_IP:
        return True
    digits = _mac_digits(v)                               # aa:bb:.., AA-BB-.., aabbccddeeff
    return len(digits) == 12 and digits == _mac_digits(ROGUE_MAC)


# (form key, French label, checker)
FIELDS = [
    ("saboteur", "Identité du saboteur", check_saboteur),
    ("vector", "Vecteur d'attaque", check_vector),
    ("time", "Heure de l'incident", check_time),
    ("device", "Équipement fantôme (MAC ou IP)", check_device),
]
MAX_FIELD_LEN = 200


# --------------------------------------------------------------------------
# Per-IP cooldown: N submissions per window (sliding), in memory
# --------------------------------------------------------------------------
RATE_LIMIT = int(os.environ.get("WARROOM_RATE_LIMIT", "5"))
RATE_WINDOW = float(os.environ.get("WARROOM_RATE_WINDOW", "60"))
_now = time.monotonic                                      # replaced in tests
_hits = {}                                                 # ip -> deque of submission times
_lock = threading.Lock()


def rate_check(ip):
    """Record this submission and return 0, or return the seconds to wait (not recorded)."""
    now = _now()
    with _lock:
        if len(_hits) > 5000:                              # keep memory bounded
            for k in [k for k, q in _hits.items() if not q or now - q[-1] >= RATE_WINDOW]:
                del _hits[k]
        q = _hits.setdefault(ip, deque())
        while q and now - q[0] >= RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return max(1, math.ceil(RATE_WINDOW - (now - q[0])))
        q.append(now)
        return 0


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
def page(status=200, **ctx):
    ctx.setdefault("values", {})
    html = render_template("index.html", fields=[(k, label) for k, label, _ in FIELDS], **ctx)
    return html, status


@app.after_request
def no_store(resp):
    resp.headers["Cache-Control"] = "no-store"             # the success page carries the flag
    return resp


@app.get("/")
def index():
    return page()


@app.post("/submit")
def submit():
    values = {k: request.form.get(k, "")[:MAX_FIELD_LEN] for k, _, _ in FIELDS}
    wait = rate_check(request.remote_addr or "?")
    if wait:
        resp = page(429, values=values,
                    error=f"Trop de tentatives. Patientez {wait} seconde(s) avant de soumettre à nouveau.")
        return resp[0], 429, {"Retry-After": str(wait)}

    correct = sum(1 for k, _, check in FIELDS if check(values[k]))
    if correct == len(FIELDS):
        flag = os.environ.get("FLAG_FINALE", "")
        if not flag:                                       # never hand out a placeholder
            app.logger.error("FLAG_FINALE is not set: cannot reveal the Grandmaster Flag")
            return page(500, values=values,
                        error="Le rapport est exact, mais le flag final n'est pas configuré. "
                              "Prévenez l'organisateur.")
        return page(values=values, flag=flag)
    return page(values=values, correct=correct, total=len(FIELDS),
                error=f"Erreur de corrélation : {correct} champ(s) correct(s) sur {len(FIELDS)}. "
                      "Vérifiez vos preuves avec les autres équipes.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099, threaded=True)      # local use only; production uses gunicorn
