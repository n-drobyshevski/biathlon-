#!/usr/bin/env python3
"""
ctfd-setup.py — load the challenges into CTFd from the challenge READMEs.

Creates (or updates, if a challenge with the same name exists) every challenge
with its category, points, description, connection info (the **Connect:** line —
every challenge is reached through a live service), flag (from .env) and
point-costed hints. Safe to re-run, e.g. after ./scripts/gen-flags.sh: flags are
replaced, hints and texts are updated in place. The hub serves no files any
more, so descriptions carry no download links.

Cross links with the cellule de crise (hub, port 8080):
- each challenge description links to its row in the hub (/#mission-NN);
- a "Cellule de crise" item is added to CTFd's top menu (needs --host);
- the CTFd id of each challenge is written to handouts/dist/ctfd_ids.json,
  which the hub reads to open the exact challenge from "Soumettre le flag".

Usage (on the Pi, after finishing the CTFd setup wizard in a browser):
    python3 scripts/ctfd-setup.py --host 192.168.8.2

Online (Cloudflare Tunnel, see CLOUDFLARE.md): pass the base domain instead.
Every **Connect:** line becomes that challenge's own subdomain
(https://site.<domain>, https://share.<domain>, ...), the hub links become
https://hub.<domain>. CTFd's own public URL comes from REVERSE_PROXY in
docker-compose.cloudflare.yml (it then trusts cloudflared's X-Forwarded-*
headers); there is no separate CTFd setting for it. CTFd publishes no host
port online, so reach it on its container IP:
    CTFD_URL=http://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
        $(docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml ps -q ctfd)):8000 \
    python3 scripts/ctfd-setup.py --base-domain ctf.example.com

Needs in .env:
    CTFD_TOKEN=ctfd_...        admin access token (CTFd: Settings > Access Tokens)
Optional:
    CTFD_URL=http://localhost:8000
    CTF_HOST=192.168.8.2       instead of --host
    CTF_DOMAIN=ctf.example.com instead of --base-domain (online mode)
CTFD_URL may also come from the shell environment.

Standard library only, so it runs with the Pi's system python3.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB_PORT = 8080

TITLE_RE = re.compile(r"^# (\d\d) · (.+?) — `([^`]+)` · \w+ · (\d+) pts", re.M)
HINT_RE = re.compile(r"<details><summary>Hint (\d+) \(−(\d+)\)</summary>(.*?)</details>", re.S)
CONNECT_RE = re.compile(r"^\*\*Connect:\*\* `([^`]+)`", re.M)
HOST_PORT_RE = re.compile(r"http://<CTF-HOST>:\d+")

# Online mode: the subdomain each challenge's **Connect:** line points at
# (same names as the hub's *_URL values in docker-compose.cloudflare.yml).
# In-story names on purpose: a subdomain must never name the vulnerability.
CONNECT_SUB = {"01": "site", "02": "site", "03": "site", "04": "athletes",
               "05": "share", "07": "share", "09": "share", "13": "share", "15": "share",
               "06": "resultats", "10": "api", "11": "chrono", "12": "certificats", "14": "sapgw"}


def read_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def hub_url(host, domain):
    """The cellule de crise's address: https://hub.<domain>/ online, else http://host:8080/."""
    return f"https://hub.{domain}/" if domain else f"http://{host}:{HUB_PORT}/"


def parse_readme(path, host, domain=None):
    text = open(path, encoding="utf-8").read()
    m = TITLE_RE.search(text)
    if not m:
        raise SystemExit(f"Unrecognised title line in {path}")
    num, name, category, value = m.group(1), m.group(2).strip(), m.group(3), int(m.group(4))
    if category.startswith("Forensics"):
        category = "Forensics"                     # "Forensics / Stego" -> one board column

    # description: everything after the title, up to the hints.
    # Evidence files are no longer handed out by the hub: each challenge is
    # reached through a live service (its **Connect:** line — the DécaFlop site
    # for 02/03, the internal share "Partage DFlop" :8020 for 05/07/09/13/15),
    # so there are no hub /fichiers download links to generate here.
    body = text[m.end():].split("<details>", 1)[0].strip()
    if domain:                                     # online: one subdomain per service
        body = HOST_PORT_RE.sub(f"https://{CONNECT_SUB[num]}.{domain}", body)
        body = body.replace("<CTF-HOST>", f"hub.{domain}")
        hub = hub_url(host, domain)
        body += (f"\n\n**Cellule de crise :** [fiche de la mission {num}]({hub}#mission-{num})"
                 f" · toutes les missions et liens : {hub}")
    else:
        host_s = host or "<CTF-HOST>"
        body = body.replace("<CTF-HOST>", host_s)

        body += (f"\n\n**Cellule de crise :** [fiche de la mission {num}](http://{host_s}:{HUB_PORT}/#mission-{num})"
                 f" · toutes les missions et liens : http://{host_s}:{HUB_PORT}")

    cm = CONNECT_RE.search(body)
    connection = cm.group(1) if cm else ""
    hints = [{"title": f"Indice {int(i)}", "cost": int(c), "content": h.strip()}
             for i, c, h in HINT_RE.findall(text)]
    return {"num": num, "name": name, "category": category, "value": value,
            "description": body, "connection_info": connection, "hints": hints}


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", help="address players use to reach the Pi (e.g. 192.168.8.2)")
    ap.add_argument("--base-domain", help="online mode (Cloudflare Tunnel): base domain of the lab "
                                          "subdomains, e.g. ctf.example.com (or CTF_DOMAIN in .env)")
    ap.add_argument("--env", default=os.path.join(ROOT, ".env"))
    ap.add_argument("--locale", default="fr", help="CTFd default interface language (default: fr)")
    ap.add_argument("--ids-file", default=os.path.join(ROOT, "handouts", "dist", "ctfd_ids.json"),
                    help="where to write the challenge ids for the hub's deep links")
    ap.add_argument("--dry-run", action="store_true", help="parse and print, change nothing")
    args = ap.parse_args()

    env = read_env(args.env)
    host = args.host or env.get("CTF_HOST", "")
    # online when --base-domain is given, or CTF_DOMAIN is set and no explicit --host
    domain = args.base_domain or ("" if args.host else env.get("CTF_DOMAIN") or os.environ.get("CTF_DOMAIN", ""))
    domain = domain.strip().strip("./")
    challenges = [parse_readme(os.path.join(ROOT, "challenges", d, "README.md"), host, domain or None)
                  for d in sorted(os.listdir(os.path.join(ROOT, "challenges")))
                  if os.path.exists(os.path.join(ROOT, "challenges", d, "README.md"))]

    for ch in challenges:                          # flag for mission NN = FLAG_NN_* in .env
        keys = [k for k in env if k.startswith(f"FLAG_{ch['num']}_")]
        ch["flag"] = env[keys[0]] if len(keys) == 1 else None

    if args.dry_run:
        for ch in challenges:
            print(f"{ch['num']} {ch['name']!r} [{ch['category']}] {ch['value']} pts, "
                  f"{len(ch['hints'])} hints, flag {'ok' if ch['flag'] else 'MISSING'}, "
                  f"connect={ch['connection_info'] or '-'}")
        return

    missing = [c["num"] for c in challenges if not c["flag"]]
    if missing:
        raise SystemExit(f"No flag in {args.env} for: {', '.join(missing)}. Run ./scripts/gen-flags.sh first.")
    token = env.get("CTFD_TOKEN") or os.environ.get("CTFD_TOKEN")
    if not token:
        raise SystemExit("Set CTFD_TOKEN in .env (CTFd admin: Settings > Access Tokens).")
    if domain:
        print(f"Online mode: Connect links on the subdomains of {domain}.")
    elif not host:
        print("Note: no --host given; descriptions will say <CTF-HOST> and skip download links.")

    api = CTFd(env.get("CTFD_URL") or os.environ.get("CTFD_URL") or "http://localhost:8000", token)
    existing = {c["name"]: c["id"] for c in api.call("GET", "/challenges?view=admin")}
    ids = {}

    for ch in challenges:
        fields = {k: ch[k] for k in ("name", "category", "value", "description", "connection_info")}
        if ch["name"] in existing:
            cid = existing[ch["name"]]
            api.call("PATCH", f"/challenges/{cid}", {**fields, "state": "visible"})
            action = "updated"
        else:
            cid = api.call("POST", "/challenges", {**fields, "type": "standard", "state": "visible"})["id"]
            action = "created"

        for f in api.call("GET", f"/challenges/{cid}/flags"):      # replace flags (handles rotation)
            api.call("DELETE", f"/flags/{f['id']}")
        api.call("POST", "/flags", {"challenge_id": cid, "type": "static", "content": ch["flag"], "data": ""})

        old = api.call("GET", f"/challenges/{cid}/hints")             # update hints in place, by order
        for i, h in enumerate(ch["hints"]):
            payload = {"challenge_id": cid, **h}
            if i < len(old):
                api.call("PATCH", f"/hints/{old[i]['id']}", payload)
            else:
                api.call("POST", "/hints", payload)
        for extra in old[len(ch["hints"]):]:
            api.call("DELETE", f"/hints/{extra['id']}")

        ids[ch["num"]] = {"id": cid, "name": ch["name"]}
        print(f"[{action}] {ch['num']} {ch['name']} — {ch['value']} pts, {len(ch['hints'])} hints, flag set")

    # CTFd top menu: a page whose route is a URL becomes an external link
    if host or domain:
        menu = {"title": "Cellule de crise", "route": hub_url(host, domain), "content": "",
                "format": "markdown", "draft": False, "hidden": False, "auth_required": False,
                "link_target": "_blank"}
        page = next((p for p in api.call("GET", "/pages") if p.get("title") == menu["title"]), None)
        if page:
            api.call("PATCH", f"/pages/{page['id']}", menu)
        else:
            api.call("POST", "/pages", menu)
        print(f"CTFd menu: 'Cellule de crise' -> {menu['route']}")
    else:
        print("Note: no --host given; skipped the 'Cellule de crise' item in CTFd's menu.")

    # challenge ids for the hub's "Soumettre le flag" deep links
    try:
        os.makedirs(os.path.dirname(args.ids_file), exist_ok=True)
        with open(args.ids_file, "w", encoding="utf-8") as fh:
            json.dump(ids, fh, ensure_ascii=False, indent=1)
        print(f"Challenge ids for the hub written to {os.path.relpath(args.ids_file, ROOT)}")
    except OSError as e:
        print(f"Warning: could not write {args.ids_file} ({e.strerror}). The hub will link to the "
              f"challenge list instead. Fix with: sudo chown -R $USER {os.path.dirname(args.ids_file)}")

    if args.locale:
        api.call("PATCH", "/configs", {"default_locale": args.locale})
        print(f"Default CTFd language set to '{args.locale}'.")
    print(f"\nDone: {len(challenges)} challenges in CTFd at {api.url}")


if __name__ == "__main__":
    main()
