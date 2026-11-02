#!/usr/bin/env python3
"""
10 · Web · HARD (JWT — weak HMAC secret)
DécaFlop Results API. Session tokens are JSON Web Tokens signed HS256 with a
weak, guessable secret. Crack the secret offline, forge a token with
role="admin", and the /api/results endpoint returns the flag.

Teaches: JWT structure, why HS256 needs a strong secret, offline token
cracking (jwt_tool / hashcat -m 16500), forging a token.

Self-contained training app — intentionally vulnerable. JWT is implemented by
hand (hmac/hashlib) so the image needs only Flask.
"""
import base64
import hashlib
import hmac
import json
import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "TRIATHLON{placeholder}")

# VULN: a short, guessable HMAC secret (hint 3 reveals it; see README).
SECRET = os.environ.get("JWT_SECRET", "DecaFlop2026").encode()


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def b64url_decode(s):
    s = s.encode() if isinstance(s, str) else s
    return base64.urlsafe_b64decode(s + b"=" * (-len(s) % 4))


def sign(header_b64, payload_b64):
    return b64url(hmac.new(SECRET, header_b64 + b"." + payload_b64, hashlib.sha256).digest())


def make_token(payload):
    h = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    p = b64url(json.dumps(payload, separators=(",", ":")).encode())
    return (h + b"." + p + b"." + sign(h, p)).decode()


def verify(token):
    try:
        h, p, s = token.strip().split(".")
        hb, pb, sb = h.encode(), p.encode(), s.encode()
        if not hmac.compare_digest(sb, sign(hb, pb)):
            return None
        header = json.loads(b64url_decode(hb))
        if header.get("alg") != "HS256":        # no alg:none / no alg confusion shortcut
            return None
        return json.loads(b64url_decode(pb))
    except Exception:
        return None


CSS = """body{font-family:system-ui,sans-serif;background:#0f1a24;color:#e6f0f7;margin:0;line-height:1.6}
header{background:#0a1118;padding:20px 24px;border-bottom:3px solid #2dd4bf}
main{max-width:720px;margin:32px auto;padding:0 18px}
.card{background:#162430;border:1px solid #28506a;border-radius:10px;padding:18px;margin:14px 0}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b141c;padding:14px;border-radius:6px;color:#9fe0c8}
a{color:#2dd4bf}h1{margin:0;font-size:22px}"""

def home_page(base):
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DécaFlop · Results API</title><style>{CSS}</style></head><body>
<header><h1>🔑 DécaFlop · Results API</h1></header>
<main>
<div class="card"><p>API interne des résultats. L'authentification se fait par
<b>jeton JWT</b> (en-tête <code>Authorization: Bearer &lt;token&gt;</code>).</p>
<p>Récupérez un jeton d'invité : <code>GET /api/token</code></p>
<p>Consultez les résultats : <code>GET /api/results</code> (jeton requis)</p></div>
<div class="card"><h3>Démo</h3>
<pre>curl {base}api/token
curl -H "Authorization: Bearer &lt;token&gt;" {base}api/results</pre>
<p>Le compte invité (<code>role: viewer</code>) ne voit que les résultats publics.
Seul un jeton <code>role: admin</code> donne accès aux données officielles.</p></div>
</main></body></html>"""


@app.get("/")
def home():
    return Response(home_page(request.host_url), mimetype="text/html")


@app.get("/api/token")
def token():
    # a guest token: viewer only (the crackable sample for the attacker)
    t = make_token({"role": "viewer", "bib": 1042, "team": "guest"})
    return Response(json.dumps({"token": t, "note": "role=viewer. Les données officielles exigent role=admin."},
                               ensure_ascii=False, indent=1), mimetype="application/json")


@app.get("/api/results")
def results():
    auth = request.headers.get("Authorization", "")
    tok = auth[7:] if auth.lower().startswith("bearer ") else request.args.get("token", "")
    claims = verify(tok)
    if not claims:
        return Response(json.dumps({"error": "jeton manquant ou invalide"}, ensure_ascii=False),
                        status=401, mimetype="application/json")
    if claims.get("role") != "admin":
        return Response(json.dumps({"role": claims.get("role"),
                                    "public": [{"rang": 1, "athlete": "Astrid Bjornsen", "temps": "1:02:14"},
                                               {"rang": 2, "athlete": "Mikkel Haugen", "temps": "1:02:51"}],
                                    "note": "Résultats publics. role=admin requis pour les données officielles."},
                                   ensure_ascii=False, indent=1), mimetype="application/json")
    official = {"flag": FLAG,
                "note": ("Jeton admin accepté. Le secret HS256 était trop faible. "
                         "Signez toujours les JWT avec une clé longue et aléatoire.")}
    return Response(json.dumps(official, ensure_ascii=False, indent=1), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
