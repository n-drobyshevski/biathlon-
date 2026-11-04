#!/usr/bin/env python3
"""
ctfd-users.py — create the players' CTFd accounts in advance, so nobody has to
fill in CTFd's registration form (which insists on an e-mail address).

Each account gets an easy password made of two short words and a number
(e.g. "bike-beach-42") and a placeholder e-mail (<pseudo>@ctf.lan: CTFd needs
one, nothing is ever sent and nobody has to type it). Players sign in to CTFd
AND to the hub with the pseudo + password from their card.

Usage (on the Pi, after the CTFd setup wizard; same .env as ctfd-setup.py):
    python3 scripts/ctfd-users.py alice bob carla        # named players
    python3 scripts/ctfd-users.py --count 7              # player01 .. player07 (6 + a spare)
    python3 scripts/ctfd-users.py --count 7 --test       # + a hidden "test" account
    python3 scripts/ctfd-users.py --count 7 --close-registration

Options:
    --prefix WORD          name of the numbered accounts (default "player")
    --test                 also create "test" (hidden: never on the scoreboard),
                           for the organizer's dry run
    --close-registration   turn off CTFd's public sign-up form (only these
                           accounts can play)
    --reset                give a NEW password to accounts that already exist
                           (default: leave them untouched)
    --out PATH             where to write the pseudo/password list
                           (default WRITEUPS/ctfd-comptes.txt, git-ignored)
    --dry-run              print what would be created, change nothing

Needs in .env:  CTFD_TOKEN=ctfd_...   (optional CTFD_URL, default http://localhost:8000)
Standard library only.
"""
import argparse
import json
import os
import re
import secrets
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL_DOMAIN = "ctf.lan"
PREFIX = "player"           # --count N creates player01 .. playerNN
TEST_NAME = "test"

# Short, common English words (no l/1 or o/0 lookalike pitfalls in
# the number part either): easy to read off a card and type on a phone.
WORDS = ["bike", "beach", "swim", "race", "chip", "wave", "helmet", "medal",
         "sprint", "track", "bottle", "jersey", "pedal", "start", "finish", "sand",
         "lighthouse", "harbor", "sail", "paddle", "seagull", "sunny", "wind", "river",
         "lake", "forest", "rocket", "tiger", "panda", "falcon", "orange", "silver"]


def read_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def make_password(rng=secrets):
    """Two different words and a two-digit number, e.g. "bike-beach-42"."""
    a = rng.choice(WORDS)
    b = rng.choice([w for w in WORDS if w != a])
    return f"{a}-{b}-{rng.randbelow(90) + 10}"


def slug(name):
    """ASCII local part for the placeholder e-mail."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9._-]+", "-", s).strip("-.") or "player"


def plan(names, count, test, prefix=PREFIX):
    """[(name, email, hidden)] in creation order; e-mails are made unique."""
    names = list(names) + [f"{prefix}{i:02d}" for i in range(1, count + 1)]
    seen, out = set(), []   # e-mails used / pseudos kept
    for name in names:
        name = name.strip()
        if not name or name.lower() in {n.lower() for n in out}:
            continue
        out.append(name)
    rows = [(n, False) for n in out]
    if test and TEST_NAME not in {n.lower() for n in out}:
        rows.append((TEST_NAME, True))
    result = []
    for name, hidden in rows:
        local, k = slug(name), 1
        while f"{local}@{EMAIL_DOMAIN}" in seen:
            k += 1
            local = f"{slug(name)}{k}"
        email = f"{local}@{EMAIL_DOMAIN}"
        seen.add(email)
        result.append((name, email, hidden))
    return result


class CTFd:
    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token

    def call(self, method, path, data=None):
        req = urllib.request.Request(
            self.url + "/api/v1" + path, method=method,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Authorization": f"Token {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"CTFd {method} {path} failed: HTTP {e.code} {e.read()[:300]!r}")
        except urllib.error.URLError as e:
            raise SystemExit(f"Cannot reach CTFd at {self.url}: {e.reason}")
        out = json.loads(body) if body else {}
        if out.get("success") is False:
            raise SystemExit(f"CTFd {method} {path} refused: {out}")
        return out.get("data")


def find_user(api, name):
    """The existing account with exactly this name (case-insensitive), or None."""
    q = urllib.parse.urlencode({"field": "name", "q": name, "view": "admin"})
    for u in api.call("GET", f"/users?{q}") or []:
        if str(u.get("name", "")).lower() == name.lower():
            return u
    return None


def apply(api, rows, reset=False, rng=secrets):
    """Create (or, with reset, re-password) each account.
    Returns [(name, password or None, status)]."""
    results = []
    for name, email, hidden in rows:
        existing = find_user(api, name)
        if existing:
            if not reset:
                results.append((name, None, "existe déjà (mot de passe inchangé)"))
                continue
            pw = make_password(rng)
            api.call("PATCH", f"/users/{existing['id']}", {"password": pw, "verified": True})
            results.append((name, pw, "mot de passe réinitialisé"))
            continue
        pw = make_password(rng)
        api.call("POST", "/users?notify=false",
                 {"name": name, "email": email, "password": pw, "type": "user",
                  "verified": True, "hidden": hidden, "banned": False})
        results.append((name, pw, "créé (caché, hors classement)" if hidden else "créé"))
    return results


def read_list(path):
    """{pseudo: password} from a list written earlier (missing file: empty)."""
    known = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8").read().splitlines()[3:]:
            parts = line.split()
            if len(parts) == 2:
                known[parts[0]] = parts[1]
    return known


def write_list(path, results, board_url=""):
    """Pseudo / password list for the organizer (0600, git-ignored folder).
    Accounts left untouched this run keep the password noted the last time."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    known = read_list(path)
    for n, p, _s in results:
        if p:
            known[n] = p
    width = max([len(n) for n in known] + [6])
    lines = ["Comptes du tableau des scores (CTFd) et de la cellule de crise",
             "Même pseudo et même mot de passe pour les deux." + (f"  Tableau : {board_url}" if board_url else ""),
             ""]
    lines += [f"{n:<{width}}  {p}" for n, p in known.items()]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="player pseudos")
    ap.add_argument("--count", type=int, default=0, help="also create player01..playerNN")
    ap.add_argument("--prefix", default=PREFIX, help="name of the numbered accounts (default player)")
    ap.add_argument("--test", action="store_true", help='also create a hidden "test" account')
    ap.add_argument("--close-registration", action="store_true", help="turn off CTFd's public sign-up")
    ap.add_argument("--reset", action="store_true", help="new password for accounts that already exist")
    ap.add_argument("--out", default=os.path.join(ROOT, "WRITEUPS", "ctfd-comptes.txt"))
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    rows = plan(args.names, args.count, args.test, args.prefix)
    if not rows:
        ap.error("give player pseudos and/or --count N (and optionally --test)")
    if args.dry_run:
        for name, email, hidden in rows:
            print(f"{name:<20} {email:<28} {'caché' if hidden else ''}")
        print(f"\n{len(rows)} account(s); nothing changed (--dry-run).")
        return 0

    env = read_env(args.env)
    token = env.get("CTFD_TOKEN") or os.environ.get("CTFD_TOKEN")
    if not token:
        raise SystemExit("Set CTFD_TOKEN in .env (CTFd: Settings > Access Tokens, as the admin).")
    api = CTFd(env.get("CTFD_URL", "http://localhost:8000"), token)

    results = apply(api, rows, reset=args.reset)
    for name, pw, status in results:
        print(f"  {name:<20} {pw or '-':<22} {status}")
    kept = [n for n, p, _s in results if p is None]
    if kept:
        print(f"\n{len(kept)} compte(s) existaient déjà et gardent leur mot de passe "
              f"({', '.join(kept)}). Pour leur en donner un nouveau : relancez avec --reset.")
    if args.close_registration:
        api.call("PATCH", "/configs", {"registration_visibility": "private"})
        print("CTFd sign-up form closed (registration_visibility = private).")

    host = env.get("CTF_HOST", "")
    write_list(args.out, results, f"http://{host}:8000" if host else "")
    print(f"\nPseudo / password list written to {os.path.relpath(args.out, ROOT)} (chmod 600, git-ignored).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
