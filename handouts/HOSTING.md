# Hosting on a Raspberry Pi 5 (4 GB) + travel router

This CTF is sized to run comfortably on a Pi 5 with 4 GB RAM on an **isolated,
offline** network created by a travel router (GL.iNet, TP-Link, etc.).

## Why offline

The web and SAP challenges are **deliberately vulnerable**. Keep them off the
public internet:

- Put the Pi and all players on the travel router's LAN/Wi-Fi.
- **Disable the router's WAN/uplink** (or just don't plug it in). Players don't
  need internet for any challenge — handouts and the scoreboard are local.
  (Exception: if a team wants an online hash-cracker for 09, give them the
  `wordlist.txt` instead so the event stays fully offline.)
- Give the Pi a static lease, e.g. `192.168.8.2`. Players start at
  `http://192.168.8.2:8080` (the cellule de crise), which links every challenge
  (`:8001` … `:8014`) and serves the handouts. Replace `<CTF-HOST>` in the
  challenge READMEs / scoreboard with that IP.

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

## Resource budget (4 GB)

| Component | Approx RAM |
|-----------|-----------|
| 8 challenge containers + the hub (`mem_limit` 96–160 MB each) | ~0.5–0.8 GB actual |
| CTFd (in docker-compose, `mem_limit` 768 MB) | ~0.4–0.7 GB |
| OS + Docker | ~0.5 GB |

Each container is capped in `docker-compose.yml`. One shared instance per
challenge is fine for 6 players — these apps are stateless, so there's nothing
for players to corrupt for each other. With CTFd, the full stack is ~1.5–2 GB
in practice: comfortable on 4 GB, but test it before the event.

## Serving the handout files

Nothing to do: `docker-compose.yml` mounts `handouts/dist/` (read-only) into
the hub container, and the cellule de crise offers each file as a download.
Missions whose files aren't built yet show "pas encore disponible" until you
run `./scripts/build-handouts.sh`, with no restart needed.

You can still attach them as files in CTFd, or drop them on a USB stick.

## Pre-event test checklist

Run through this once, ideally the day before:

- [ ] `uname -m` is `aarch64`
- [ ] `docker compose up -d --build` → all containers `Up` (8 live challenges
      + hub + CTFd)
- [ ] `curl -s localhost:8001/robots.txt` shows the staff path
- [ ] `curl -s localhost:8008/sap/public/info` returns the SAP note
- [ ] `curl -s localhost:8010/api/token` returns a JWT; `:8011/.git/` lists;
      `:8012` and `:8014` load
- [ ] `./scripts/build-handouts.sh` → 8 files in `handouts/dist/`
- [ ] Solve each handout once using the steps in `WRITEUPS/` (confirm the
      flags match your `.env`)
- [ ] From a second device on the travel router, open
      `http://<PiIP>:8080`: 9 missions, every download works,
      every "Ouvrir…" button reaches its challenge
- [ ] CTFd at `:8000`: setup wizard done (Teams mode), `ctfd-setup.py` loaded
      9 challenges; a test team can register, submit a flag and unlock a hint
- [ ] The cellule de crise's "Tableau des scores" and "Soumettre le flag" links
      open CTFd
- [ ] Decide whether the router's WAN stays off (recommended)

## During the event

- 6 people, 1h–1h30: expect most teams to clear the easy + medium tier and at
  least start the SAP pair. The hint system (point-costed, in each README /
  your scoreboard) keeps beginners from stalling.
- If a flag leaks, `./scripts/gen-flags.sh` + `docker compose up -d --build` +
  `./scripts/build-handouts.sh` rotates everything in ~1 minute. Update the
  scoreboard flags afterward.
