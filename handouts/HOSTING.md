# Hosting on a Raspberry Pi 5 (4 GB) + travel router

This CTF is sized to run comfortably on a Pi 5 with 4 GB RAM on an **isolated,
offline** network created by a travel router (GL.iNet, TP-Link, etc.).

## Why offline

The web and SAP challenges are **deliberately vulnerable**. Keep them off the
public internet:

- Put the Pi and all players on the travel router's LAN/Wi-Fi.
- **Disable the router's WAN/uplink** (or just don't plug it in). Players don't
  need internet for any challenge — handouts and the scoreboard are local.
  No online tools are needed even for cracking: 09/10 are solvable fully offline
  with the provided `wordlist.txt` plus the on-Pi browser toolbox (see
  "Browser toolbox" below).
- Give the Pi a static lease, e.g. `192.168.8.2`. Players start at
  `http://192.168.8.2:8080` (the cellule de crise), which links every challenge
  (`:8001` … `:8014`) and serves the handouts. Replace `<CTF-HOST>` in the
  challenge READMEs / scoreboard with that IP.

> Players who can't join a local LAN (corporate laptops with always-on
> Zscaler, etc.): see [`../CLOUDFLARE.md`](../CLOUDFLARE.md) for the
> **optional** online mode. The vulnerable services stay off the open internet
> behind a Cloudflare Tunnel and a Cloudflare Access login, with no egress.

## Setup

```bash
# Raspberry Pi OS (64-bit) — confirm arm64
uname -m   # aarch64

# Docker
curl -fsSL https://get.docker.com | sh      # (do this once, with internet, BEFORE the event)
sudo usermod -aG docker "$USER" && newgrp docker

# then, on the event network (offline is fine once images are built):
cd biathlon-
./scripts/gen-flags.sh
docker compose up -d --build
./scripts/build-handouts.sh
# then the scoreboard: see scoreboard/README.md (setup wizard + ctfd-setup.py)
```

> Build the images **once while you still have internet** (the base
> `python:3.12-slim` and `pip`/`apt` packages download then). After that the
> whole thing runs offline.

## Browser toolbox (for locked-down / corporate laptops)

Players on managed laptops often can't install anything (no admin rights, EDR,
a blocked terminal, download scanning). They don't have to: two extra services
run **on the Pi** and are driven entirely from a browser.

- **CyberChef** — `http://<PiIP>:8090`. A static, 100% client-side app: base64,
  EXIF, unzip (including password-protected), file carving ("Extract Files"),
  MD5, and JWT decode/sign/verify. Covers 02, 03, 05, 07, 09, 10 and 13 with no
  install. Stateless — one shared instance, nothing to isolate between players.
- **Terminal d'équipe (ttyd)** — `http://<PiIP>:8091`. A Linux shell in the
  browser with `git-dumper`, `john`, `binwalk`, `foremost`, `exiftool`, `curl`,
  `python3`. The catch-all; in practice only **11** (dump a `.git`) really needs
  a shell. Each browser connection gets its own scratch workspace, the container
  runs as a **non-root** user with **no repository, flags or challenge source
  mounted**, and it's capped (`mem_limit 512m`, `cpus 2.0`, `pids 256`), so one
  player can't starve the others or read another challenge's answers.

Both link from the cellule de crise's **Outils** tab and auto-point at the Pi's
IP. Override the addresses with `CYBERCHEF_URL` / `TERMINAL_URL` on the `hub`
service if you host them elsewhere.

**One prep step (needs internet, before the event):** CyberChef ships as a
release zip, not committed to this repo. Download it once and drop it in:

```bash
# grab the "CyberChef_vX.Y.Z.zip" asset from
#   https://github.com/gchq/CyberChef/releases
cp ~/Downloads/CyberChef_v*.zip tools/cyberchef/cyberchef.zip
```

`docker compose up -d --build` then builds both services locally (arm64). The
`toolbox` image pulls its `apt`/`pip` tools and the `ttyd` binary at build time,
so build it while you still have internet, same as the challenge images.

## Resource budget (4 GB)

| Component | Approx RAM |
|-----------|-----------|
| 7 challenge containers + the hub + the file share (gunicorn, 2 workers each; capped at 256 MB / 0.5 CPU each) | ~0.6–0.9 GB actual |
| War Room (gunicorn, 1 worker, capped at 64 MB) | ~40 MB |
| CTFd (in docker-compose, SQLite + `WORKERS 1`, `mem_limit` 768 MB) | ~0.4–0.7 GB |
| CyberChef (static, `mem_limit` 96 MB) | ~15–30 MB actual |
| Terminal toolbox (`mem_limit` 512 MB, `cpus 2.0`) | ~0.15 GB idle, short bursts when cracking/carving |
| OS + Docker | ~0.5–0.8 GB |

Each container is capped in `docker-compose.yml`. One shared instance per
challenge is fine for 6 players — these apps are stateless, so there's nothing
for players to corrupt for each other. With CTFd and the browser toolbox, the
full stack is ~2–2.5 GB in practice: comfortable on 4 GB, but test it before the
event.

The only way to push a 4 GB Pi is several players cracking at once. Our cracks
are tiny (a 15-word `wordlist.txt`, a 1 MB carve) — keep it that way: **don't
drop `rockyou.txt` in**, and the `toolbox` caps mean a runaway only OOM-kills its
own container, not the Pi. As cheap insurance, enable compressed RAM swap once
(prep, with internet):

```bash
sudo apt-get install -y zram-tools
printf 'ALGO=zstd\nPERCENT=50\n' | sudo tee /etc/default/zramswap
sudo systemctl restart zramswap        # ~2 GB of zram-backed swap, no SD wear
```

## Serving the files

The hub serves **no files**. Everything is built into `handouts/dist/` by
`./scripts/build-handouts.sh` and mounted read-only into the two services that
publish it, so players *find* each file in context:

- **Intranet DécaFlop** — the internal file share (`share/`, `:8020`). The crew logs
  in (default `equipe-it` / `transition2026`; override with `SHARE_USER` /
  `SHARE_PASSWORD`) and browses department folders for the evidence: the pcap
  (05), the USB image (07), the SAP export + note + wordlist + encrypted zip
  (09), the `.sap` shortcut (13) and the ABAP source (15). Files are served
  byte-for-byte through an explicit path→name map; nothing else is downloadable
  and there is no path traversal. A file that isn't built yet shows "pas encore
  disponible" in the listing and 404s on download.
- **DécaFlop site** (`:8001`): the poster (02) in `/presse` and the race photo
  (03) in `/actualites`, served byte-for-byte at `:8001/medias/...` (only those
  two names; placeholders before they're built).

No restart is needed after `./scripts/build-handouts.sh` — both services read
`handouts/dist/` live. You can still attach the files in CTFd, or drop them on a
USB stick.

### Challenge 01 gates the share login

The share login is **no longer printed by the hub, nor by the staff portal**.
Players work challenge 01: `/robots.txt` on the DécaFlop site points to the
hidden staff portal, which shows the share **address** (`:8020`) and hints that
the team service account is still shipped with the site's front-end. It is —
every DécaFlop page loads `/assets/site.config.js`, which carries the login
**base64-encoded**. Players recover it from view-source (open
`/assets/site.config.js`, base64-decode the `svc` value → `user:pass`). So 01
(easy, 50 pts) is a soft prerequisite for the five share-hosted challenges —
**05, 07, 09, 13, 15, ~700 pts in all, including the 250-pt finale (09)**. It's a
reference, not a hard gate: the share's own login is unchanged, so a teammate who
already has the credentials can log in directly.

`docker-compose.yml` feeds the SAME `SHARE_USER` / `SHARE_PASSWORD` to the staff
portal (01), the `/assets/site.config.js` asset and the share, so they can never
drift. If a team is stuck on 01, an organizer can just read them the login — it's
`equipe-it` / `transition2026` unless you overrode it in `.env`.

## Pre-event test checklist

Run through this once, ideally the day before:

- [ ] `uname -m` is `aarch64`
- [ ] `tools/cyberchef/cyberchef.zip` is in place (one-time download — see
      "Browser toolbox" above)
- [ ] `docker compose up -d --build` → all containers `Up` (7 challenge apps
      + hub + share + CTFd + cyberchef + toolbox)
- [ ] **`./scripts/build-handouts.sh` → 10 files in `handouts/dist/`. Run this
      BEFORE the checks below.** The poster, the race photo and every share
      download are served from that folder, so until it is built `:8001/presse`,
      `:8001/actualites` and the `:8020` share show "pas encore disponible" and
      the files 404. (No restart needed afterwards — the mount is read-only.)
- [ ] `curl -s localhost:8001/robots.txt` shows the staff path; opening that
      staff portal shows the Intranet DécaFlop address (`:8020`) and the share login
      (the same one the share accepts)
- [ ] `curl -s localhost:8001/presse` and `:8001/actualites` load; the poster
      downloads at `:8001/medias/decaflop_poster.png` and the race photo at
      `:8001/medias/transition_shot.jpg` (both byte-identical to `handouts/dist/`)
- [ ] `Intranet DécaFlop` at `:8020`: logged out redirects to the login; `equipe-it`
      / `transition2026` logs in; folders browse; a listed file downloads
      byte-identical to `handouts/dist/`; a bad login is rejected
- [ ] `curl -s localhost:8010/api/token` returns a JWT; `:8011/.git/` lists;
      `:8012` and `:8014` load
- [ ] `:8090` opens CyberChef; `:8091` opens the terminal and drops you in a
      shell (try `git-dumper --help`); the hub's **Outils** tab links both at
      the Pi's IP
- [ ] Solve each handout once using the steps in `WRITEUPS/` (confirm the
      flags match your `.env`)
- [ ] From a second device on the travel router, open
      `http://<PiIP>:8080`: 14 missions, every "Accès" link reaches its live
      service (site, share or challenge)
- [ ] CTFd at `:8000`: setup wizard done (Teams mode), `ctfd-setup.py` loaded
      the 14 challenges; a test team can register, submit a flag and unlock a hint
- [ ] The cellule de crise's "Tableau des scores" and "Soumettre le flag" links
      open CTFd
- [ ] Decide whether the router's WAN stays off (recommended)

## During the event

- 6 people, 1h–1h30: expect most teams to clear the easy + medium tier and at
  least start the SAP pair. The hint system (point-costed, in each README /
  your scoreboard) keeps beginners from stalling. For a true first-timer, the
  hub's **Mode guidé** tab is a full step-by-step walkthrough (stops before the
  flag), gated by `GUIDE_PASSWORD` (default `debutant`) — give the word only to
  teams that want it, so others aren't spoiled.
- If a flag leaks, `./scripts/gen-flags.sh` + `docker compose up -d --build` +
  `./scripts/build-handouts.sh` rotates everything in ~1 minute. Update the
  scoreboard flags afterward.
