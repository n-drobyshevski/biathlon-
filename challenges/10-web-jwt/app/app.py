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
import sys
from html import escape

from flask import Flask, Response, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import intranet  # noqa: E402

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


def home_page(base):
    base = escape(base)
    body = f"""<h1 class="h1">Results API · documentation</h1>
<p class="lead">API interne des résultats de la finale. Elle remplace l'ancienne admin résultats web
 (ChronoRésultats). Les intégrations doivent basculer avant la saison 2027.</p>
<div class="cols"><div>
 <section class="wp"><h2>Authentification</h2>
  <p>Chaque appel aux données porte un jeton JWT signé (HS256) dans l'en-tête
   <code>Authorization: Bearer &lt;token&gt;</code>. Le paramètre <code>?token=</code> reste accepté
   pour les anciens clients.</p>
 </section>
 <section class="wp"><h2>Points d'accès</h2>
  <table class="list data"><thead><tr><th style="width:70px">Méthode</th><th style="width:150px">Chemin</th>
   <th>Description</th><th style="width:90px">Jeton</th></tr></thead><tbody>
  <tr><td><span class="verb">GET</span></td><td><code>/api/token</code></td>
   <td class="wrap">Délivre un jeton invité (<code>role: viewer</code>).</td><td>non</td></tr>
  <tr><td><span class="verb">GET</span></td><td><code>/api/results</code></td>
   <td class="wrap">Classement. Résultats publics pour <code>viewer</code>, données officielles pour
    <code>admin</code>.</td><td>oui</td></tr>
  </tbody></table>
 </section>
 <section class="wp"><h2>Exemple</h2>
<pre class="block">curl {base}api/token
curl -H "Authorization: Bearer &lt;token&gt;" {base}api/results</pre>
 </section>
</div><div>
 <section class="wp"><h2>Rôles</h2><dl class="kv">
  <dt><code>viewer</code></dt><dd>Résultats publics (compte invité)</dd>
  <dt><code>admin</code></dt><dd>Données officielles (équipe résultats)</dd></dl></section>
 <section class="wp"><h2>Version</h2><dl class="kv">
  <dt>API</dt><dd>v2.0.3</dd><dt>Format</dt><dd>JSON (UTF-8)</dd><dt>Statut</dt><dd>Production</dd></dl></section>
 <section class="wp"><h2>Support</h2><p>Équipe résultats · astreinte IT (poste 300).</p></section>
</div></div>"""
    return intranet.page("Results API - documentation", body, app="api", site_title="Results API",
                         site_href="/", logo="API", topnav=[("/", "Documentation", True)],
                         product="Results API v2.0.3", foot_extra="Base URL\u00a0: " + base + "api/")


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
