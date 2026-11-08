#!/usr/bin/env python3
"""
verify-finale-loop.py: play the finale like a team would, against a LIVE deployment.

  1. log in to the Intranet share, download phantom_signal.zip, unzip it
     (password: infected), read the capture, extract the rogue device's MAC / IP
     and the flag of mission 08 (the HTTP 200 the gateway sent back);
  2. open the War Room, check a wrong report only gets a count, then file the
     report with the four answers (device from the capture) and read the
     Grandmaster Flag;
  3. submit both flags to CTFd (mission 08 and the capstone), plus a wrong one.

Fields (a) saboteur, (b) vector and (c) time come from other missions, so this
organiser smoke test takes them as arguments (defaults = the shipped answers).
It spends 2 of the War Room's 5 submissions per minute for this machine's IP.
Standard library only, so it runs with the Pi's system python3:

    python3 scripts/verify-finale-loop.py --host 192.168.8.2
    python3 scripts/verify-finale-loop.py --host 192.168.8.2 --skip-ctfd
"""
import argparse
import http.cookiejar
import io
import json
import os
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_PATH = "/telecharger/" + urllib.parse.quote("Réseau/Captures terrain/phantom_signal.zip")
FLAG_RE = re.compile(rb"TRIATHLON\{[^}\r\n]+\}")
failures = []


def step(ok, text, detail=""):
    print(f"{'OK  ' if ok else 'FAIL'} {text}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(text)
    return ok


def read_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v.strip('"').strip("'")
    return env


def frames(pcap):
    off = 24
    while off < len(pcap):
        n = struct.unpack("!I", pcap[off + 8:off + 12])[0]
        yield pcap[off + 16:off + 16 + n]
        off += 16 + n


def tcp_data(frame):
    """(src_mac, src_ip, payload) for an Ethernet/IPv4/TCP frame, else None."""
    if len(frame) < 54 or frame[12:14] != b"\x08\x00" or frame[23] != 6:
        return None
    tcp = 14 + (frame[14] & 0x0F) * 4
    return (":".join(f"{b:02x}" for b in frame[6:12]), ".".join(str(b) for b in frame[26:30]),
            frame[tcp + (frame[tcp + 12] >> 4) * 4:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--share-url"), ap.add_argument("--warroom-url"), ap.add_argument("--ctfd-url")
    ap.add_argument("--share-user", default="equipe-it")
    ap.add_argument("--share-password", default="transition2026")
    ap.add_argument("--saboteur", default="VLINDQVIST")
    ap.add_argument("--vector", default="Passerelle SAP")
    ap.add_argument("--time", default="2026-11-01 18:42")
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"), help="for CTFD_TOKEN / CTFD_URL")
    ap.add_argument("--skip-ctfd", action="store_true")
    a = ap.parse_args()
    env = read_env(a.env)
    share = (a.share_url or f"http://{a.host}:8020").rstrip("/")
    warroom = (a.warroom_url or f"http://{a.host}:8099").rstrip("/")
    ctfd = (a.ctfd_url or env.get("CTFD_URL") or f"http://{a.host}:8000").rstrip("/")

    jar = http.cookiejar.CookieJar()
    web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def call(opener, url, data=None, headers=None, method=None):
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with opener.open(req, timeout=20) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except urllib.error.URLError as e:
            raise SystemExit(f"cannot reach {url}: {e.reason}")

    # ---- 1. solve 08 ---------------------------------------------------------
    print("== 1. Mission 08: the capture")
    st, _ = call(web, share + "/login", urllib.parse.urlencode(
        {"identifiant": a.share_user, "motdepasse": a.share_password}).encode())
    step(st == 200 and any(c.name == "intranet_session" for c in jar), "log in to the Intranet share")
    st, blob = call(web, share + ZIP_PATH)
    if not step(st == 200 and blob[:2] == b"PK", "download phantom_signal.zip from Réseau / Captures terrain", f"HTTP {st}"):
        return finish()
    try:
        pcap = zipfile.ZipFile(io.BytesIO(blob)).read("phantom_signal.pcap", pwd=b"infected")
        step(True, "unzip with the password 'infected'", f"{len(pcap)} bytes")
    except (RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        step(False, "unzip with the password 'infected'", str(exc))
        return finish()
    posts = [d for d in map(tcp_data, frames(pcap)) if d and d[2].startswith(b"POST /sap/gw/register")]
    resp = [d for d in map(tcp_data, frames(pcap)) if d and d[2].startswith(b"HTTP/1.1 200")]
    if not step(len(posts) == 1 and len(resp) == 1, "find the POST /sap/gw/register and its 200 OK"):
        return finish()
    mac, ip, _ = posts[0]
    flag08 = (FLAG_RE.search(resp[0][2]) or [b""])[0].decode()
    step(bool(flag08), "read the mission-08 flag from the HTTP response")
    print(f"     rogue device: {mac} / {ip}")

    # ---- 2. the War Room ---------------------------------------------------------
    print("== 2. War Room")
    def report(**fields):
        st, body = call(urllib.request.build_opener(), warroom + "/submit", urllib.parse.urlencode(fields).encode())
        return st, body.decode("utf-8", "replace")
    st, page = report(saboteur="x", vector="x", time="x", device="x")
    step("0 champ(s) correct(s) sur 4" in page and "TRIATHLON{" not in page, "a wrong report only gets a count, no flag", f"HTTP {st}")
    st, page = report(saboteur=a.saboteur, vector=a.vector, time=a.time, device=mac)
    m = re.search(r'id="flag"[^>]*>\s*(TRIATHLON\{[^<]+\})', page)
    finale = m.group(1) if m else ""
    step(st == 200 and bool(finale), "the complete report (device taken from the capture) reveals the Grandmaster Flag",
         f"HTTP {st}" + ("" if finale else "; " + (re.search(r'class="err-msg">([^<]+)', page) or [0, "no flag in the page"])[1]))

    # ---- 3. CTFd -------------------------------------------------------------------
    if a.skip_ctfd:
        print("== 3. CTFd: skipped")
        return finish()
    print("== 3. CTFd")
    token = env.get("CTFD_TOKEN") or os.environ.get("CTFD_TOKEN")
    if not step(bool(token), "CTFD_TOKEN is available (.env or environment)"):
        return finish()
    api = urllib.request.build_opener()
    hdr = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    _, raw = call(api, ctfd + "/api/v1/challenges?view=admin", headers=hdr)
    ids = {c["name"]: c["id"] for c in json.loads(raw).get("data", [])}

    def attempt(name, submission):
        cid = ids.get(name)
        if cid is None:
            return None
        _, body = call(api, ctfd + "/api/v1/challenges/attempt", json.dumps(
            {"challenge_id": cid, "submission": submission}).encode(), hdr, "POST")
        return json.loads(body).get("data", {}).get("status")
    for name, good in (("Le Signal Fantôme", flag08), ("Rapport d'Incident Final", finale)):
        step(name in ids, f"challenge '{name}' is registered in CTFd")
        step(bool(good) and attempt(name, good) == "correct", f"CTFd accepts the flag of '{name}'")
        step(attempt(name, "TRIATHLON{not_the_flag}") == "incorrect", f"CTFd rejects a wrong flag for '{name}'")
    return finish()


def finish():
    print("\n" + ("LOOP COMPLETE" if not failures else f"{len(failures)} STEP(S) FAILED"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
