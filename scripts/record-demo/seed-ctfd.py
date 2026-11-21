#!/usr/bin/env python3
"""
seed-ctfd.py: prepare CTFd for the demo video (record.js).

DESTRUCTIVE: it deletes EVERY non-admin CTFd account (and their solves), then
creates five demo players (equipe-it-01, -02, -04, -05, -06) who submit real
flags through the CTFd API. Their solve times are then spread over the last
hour in CTFd's database, so the scoreboard graph looks like a game in progress.
These players are demo data: say so when you show the video.

The account the video creates on camera (equipe-it-03 by default) is removed
too, so record.js can register it again. --reset-terminal also deletes that
pseudo in the team terminal (toolbox), which the video logs into.

Never run it on the event's CTFd once players have signed up.

Usage (repo root, lab running, CTFd set up with scripts/ctfd-setup.py):
    python3 scripts/record-demo/seed-ctfd.py --yes [--reset-terminal]

Needs in .env: CTFD_TOKEN (admin token, see scripts/ctfd-setup.py) and the
flags from scripts/gen-flags.sh. Optional: CTFD_URL (default
http://localhost:8000), CTFD_CONTAINER / TOOLBOX_CONTAINER (default: found with
`docker compose ps -q ctfd|toolbox`).

Standard library only.
"""
import argparse
import http.cookiejar
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]

# pseudo -> missions solved, in order; minutes after the start, minutes per mission
TEAMS = {
    "equipe-it-01": (["01", "02", "03", "04", "06", "05", "07", "13"], 3, 7),
    "equipe-it-02": (["01", "03", "04", "06", "10", "11"], 6, 10),
    "equipe-it-04": (["01", "02", "13", "04"], 9, 13),
    "equipe-it-05": (["01", "03", "06"], 14, 17),
    "equipe-it-06": (["01"], 40, 0),
}
DEMO_PASSWORD = "Demo-2026!"


def load_env():
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line)
            if m:
                env[m.group(1)] = m.group(2)
    env.update({k: v for k, v in os.environ.items() if k.startswith(("CTFD_", "FLAG_", "TOOLBOX_"))})
    return env


def container(env, key, service):
    if env.get(key):
        return env[key]
    out = subprocess.run(["docker", "compose", "ps", "-q", service], cwd=ROOT, capture_output=True, text=True)
    cid = out.stdout.strip().splitlines()
    if not cid:
        sys.exit(f"No running '{service}' container (docker compose ps). Set {key}.")
    return cid[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--yes", action="store_true", help="really delete every non-admin CTFd account")
    ap.add_argument("--player", default="equipe-it-03", help="account record.js creates on camera")
    ap.add_argument("--reset-terminal", action="store_true", help="also delete --player in the team terminal")
    args = ap.parse_args()
    if not args.yes:
        sys.exit("This deletes every non-admin CTFd account. Re-run with --yes (never during the event).")

    env = load_env()
    base = env.get("CTFD_URL", "http://localhost:8000").rstrip("/")
    token = env.get("CTFD_TOKEN") or sys.exit("CTFD_TOKEN missing in .env (see scripts/ctfd-setup.py).")
    ids_file = ROOT / "handouts" / "dist" / "ctfd_ids.json"
    if not ids_file.exists():
        sys.exit("handouts/dist/ctfd_ids.json missing: run scripts/ctfd-setup.py first.")
    ids = {k: v["id"] for k, v in json.loads(ids_file.read_text()).items()}
    flag_key = {k[5:7]: k for k in env if re.match(r"FLAG_\d\d_", k)}

    def admin(method, path, body=None):
        req = urllib.request.Request(base + "/api/v1" + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Token {token}", "Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req))

    for u in admin("GET", "/users?per_page=100")["data"]:
        admin("DELETE", f"/users/{u['id']}")
    print("removed every non-admin account")

    uid = {}
    for name, (missions, _, _) in TEAMS.items():
        uid[name] = admin("POST", "/users", {"name": name, "email": f"{name}@decaflop.lan",
                                             "password": DEMO_PASSWORD})["data"]["id"]
        jar = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        page = op.open(base + "/login").read().decode()
        nonce = re.search(r'name="nonce"[^>]*value="([^"]+)"', page).group(1)
        op.open(base + "/login", urllib.parse.urlencode({"name": name, "password": DEMO_PASSWORD,
                                                         "nonce": nonce}).encode())
        csrf = re.search(r"'csrfNonce': \"([0-9a-f]+)\"", op.open(base + "/challenges").read().decode()).group(1)
        for m in missions:
            req = urllib.request.Request(base + "/api/v1/challenges/attempt", method="POST",
                                         data=json.dumps({"challenge_id": ids[m],
                                                          "submission": env[flag_key[m]]}).encode(),
                                         headers={"Content-Type": "application/json", "CSRF-Token": csrf})
            status = json.load(op.open(req))["data"]["status"]
            if status != "correct":
                sys.exit(f"{name}: mission {m} answered '{status}' (flags in .env out of sync with CTFd?)")
        print(f"{name}: {len(missions)} missions solved")

    # spread the solve times over the last hour (CTFd stores them in submissions.date, UTC)
    start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=72)
    rows = []
    for name, (missions, offset, pace) in TEAMS.items():
        for i, m in enumerate(missions):
            t = start + timedelta(minutes=offset + i * pace + (i % 3) * 1.7)
            rows.append((t.strftime("%Y-%m-%d %H:%M:%S.000000"), uid[name], ids[m]))
    script = ("import sqlite3,json,sys\nc=sqlite3.connect('/var/uploads/ctfd.db')\n"
              "for d,u,ch in json.loads(sys.argv[1]):\n"
              "    c.execute('UPDATE submissions SET date=? WHERE user_id=? AND challenge_id=?',(d,u,ch))\n"
              "c.commit()")
    ctfd = container(env, "CTFD_CONTAINER", "ctfd")
    subprocess.run(["docker", "exec", ctfd, "python", "-c", script, json.dumps(rows)], check=True)
    subprocess.run(["docker", "restart", ctfd], check=True, capture_output=True)   # clears the scoreboard cache
    print("solve times spread over the last hour; CTFd restarted")

    if args.reset_terminal:
        tb = container(env, "TOOLBOX_CONTAINER", "toolbox")
        r = subprocess.run(["docker", "exec", tb, "toolbox-admin", "supprimer", args.player],
                           capture_output=True, text=True)
        print((r.stdout or r.stderr).strip() or f"terminal: {args.player} not found (nothing to delete)")
    print(f"ready: record.js will create '{args.player}' on camera")


if __name__ == "__main__":
    main()
