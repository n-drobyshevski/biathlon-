# 🏊🚴🏃 Opération Dernière Transition — a DécaFlop CTF

A small Jeopardy-style Capture The Flag built around one story. Designed for
**~6 players, beginner → intermediate, 1h–1h30**, self-hosted on a **Raspberry
Pi 5 (4 GB)** behind a travel router with **no internet**.

> ⚠️ **Secrets stay out of git.** No submittable flag is committed: flags are
> random, generated on the Pi (`scripts/gen-flags.sh` → git-ignored `.env`),
> and organizer solutions live in `WRITEUPS/` (also git-ignored, shared
> privately). The challenge *source* is here, though, so a player who reads
> this public repo can learn the techniques and the storyline. The event is
> meant to be played against the running Pi, not GitHub — if you want it fully
> spoiler-proof, make the repo private before the event.

---

## The story

**DécaFlop** — "sport pour (presque) tous" — is a budget sporting-goods chain
and the title sponsor of the Regional Triathlon Championship. The night before
the final race, someone broke into the event systems and **rigged the start
list**, swapping timing-chip assignments to fix the result.

Your team is the event's emergency IT crew. Follow the trail across DécaFlop's
website, the timing booth, a referee's USB stick and the company's **SAP DFlop
ERP** system. The final challenge names the saboteur.

Every challenge drops a clue that feeds the next; the finale (09) ties them
together. Suggested order is the numbering, but challenges are independent
enough for 6 people to split up and work in parallel.

---

## Challenges

| # | Title | Category | Difficulty | Pts | Type |
|---|-------|----------|-----------|-----|------|
| 01 | The Sponsor's Secret | Web | Easy | 50 | live (`:8001`) |
| 02 | Share Everywhere | Forensics/Stego | Easy | 50 | live (`:8001`) |
| 03 | In Transition | Forensics | Easy | 75 | live (`:8001`) |
| 04 | Not Your Profile | Web (IDOR) | Medium | 100 | live (`:8004`) |
| 05 | The Timing Booth | Forensics (pcap) | Medium | 100 | handout |
| 06 | Results Admin | Web (SQLi) | Medium | 125 | live (`:8006`) |
| 07 | The Referee's USB | Forensics (carving) | Medium | 125 | handout |
| 09 | Who Rigged the Race? 🏁 | **SAP** | **Hard** | 250 | handout (finale) |

The finale (09) closes the sabotage story. Missions **10–15** are an optional
**audit complémentaire** — a deeper security sweep of DécaFlop's systems; they
are independent of the main trail.

| # | Title | Category | Difficulty | Pts | Type |
|---|-------|----------|-----------|-----|------|
| 10 | Forged Credentials | Web (JWT) | **Hard** | 175 | live (`:8010`) |
| 11 | Deleted, Not Gone | Web (.git) | **Hard** | 150 | live (`:8011`) |
| 12 | Print Your Own | Web (SSTI) | **Hard** | 175 | live (`:8012`) |
| 13 | Saved for Convenience | **SAP** | Easy | 75 | handout |
| 14 | The Open Gateway | **SAP** | Medium | 150 | live (`:8014`) |
| 15 | Hardcoded | **SAP** | Medium | 150 | handout |

**14 challenges** · 4 easy · 6 medium · 4 hard. Total **1750 pts**.
Flag format: `TRIATHLON{...}`.

Each challenge folder has a player-facing `README.md` (prompt + point-costed
hints). The live web/SAP apps are Flask containers; the forensics/stego/SAP
files are generated as handouts and published on two internal services (the
DécaFlop site for the poster/photo, the `Intranet DécaFlop` file share for the rest)
so players find them in context instead of downloading them from the hub.

---

## Organizer quick start (on the Pi)

```bash
git clone https://github.com/n-drobyshevski/biathlon- && cd biathlon-

# 1) generate fresh random flags -> .env  (never committed)
./scripts/gen-flags.sh

# 2) start the live web + SAP challenges (arm64 native, memory-capped)
docker compose up -d --build

# 3) build the forensics / stego / SAP handout files -> handouts/dist/
./scripts/build-handouts.sh

# 4) scoreboard: finish CTFd's setup wizard at http://<PiIP>:8000 (mode "Users": solo),
#    put CTFD_TOKEN + CTF_HOST in .env, then load the challenges:
python3 scripts/ctfd-setup.py
```

**Players only need one address: `http://<PiIP>:8080`.**
That's the "cellule de crise" (`hub/`, its own container, not a challenge):
the in-story briefing page for the emergency IT crew. It lists every mission and
links the live service each one is reached through. The hub serves **no files**
itself: evidence files live on the internal share **Intranet DécaFlop** (`:8020`),
and the poster/photo on the DécaFlop site (`:8001`). The hub gives out the
share's crew login in its Contexte sheet. It never links the hidden staff
portal, so challenge 01 stays a puzzle, and no mission is locked behind another.

For true first-timers, the hub also has an optional **Mode guidé** tab: a
step-by-step walkthrough of every mission (what the technique is, where to go,
then the steps revealed one at a time, always stopping before the flag). It is
gated by a simple password (`GUIDE_PASSWORD`, default `debutant`) so ordinary
players don't hit spoilers — hand the word only to players who want the training
wheels.

Live services after step 2:

| Port | Service |
|------|-----------|
| 8080 | Cellule de crise (players' entry point, not a challenge) |
| 8001 | 01 DécaFlop site + staff portal (also the poster/photo for 02/03) |
| 8020 | Intranet DécaFlop — internal file share (02 evidence for 05/07/09/13/15; not a challenge) |
| 8004 | 04 athlete portal (IDOR) |
| 8006 | 06 results admin (SQLi) |
| 8010 | 10 Results API (JWT) |
| 8011 | 11 Timing site (exposed .git) |
| 8012 | 12 Certificate generator (SSTI) |
| 8014 | 14 SAP gateway (reginfo) |
| 8000 | CTFd scoreboard: one account per player, flags, hints, ranking |

Where players find each file (all built into `handouts/dist/` by step 3, then
mounted read-only into the service that publishes them):

On the **internal share** `Intranet DécaFlop` (`:8020`, log in `equipe-it` /
`transition2026`):

```
Chronométrage / Captures / timing_booth.pcap                     -> 05
Arbitrage / Pièces / referee_usb.img                             -> 07
Basis SAP / Exports / SAP_USR02_export.csv, sap_hint.txt         -> 09
IT / Outils / wordlist.txt                                       -> 09
Direction de course / Dossier incident / case_file.zip           -> 09
IT / Sauvegardes postes / portable-equipe-03 / dflop_erp.sap     -> 13
Basis SAP / Développements / ZDFLOP_RESULT_EXPORT.abap           -> 15
```

Clicking a file name opens a read-only viewer (`/apercu/<chemin>`): text, ABAP
and `.sap` files with line numbers, CSV as a spreadsheet grid, ZIP archives as
their file list (names only, the encrypted content is never read). PCAP and disk
images show "Aperçu non disponible". Downloads (`/telecharger/<chemin>`) stay
byte-for-byte.

On the **DécaFlop site** (`:8001`): the poster (02) in its press area
(`/presse`) and the race photo (03) in its actualités (`/actualites`), served
byte-for-byte at `:8001/medias/...`.

See [`scoreboard/README.md`](scoreboard/README.md) for the scoreboard options
and [`handouts/HOSTING.md`](handouts/HOSTING.md) for the Pi 5 + travel-router
setup, resource notes, reset, and the pre-event test checklist.

**Optional online hosting** (players on locked-down corporate laptops that
can't reach a local LAN): [`CLOUDFLARE.md`](CLOUDFLARE.md) publishes the lab
through an outbound-only Cloudflare Tunnel behind a Cloudflare Access login,
using the `docker-compose.cloudflare.yml` overlay. Offline stays the default.

---

## Resetting between runs

```bash
docker compose down            # stop challenges
./scripts/gen-flags.sh         # rotate flags (keeps CTFD_TOKEN / CTF_HOST)
docker compose up -d --build   # restart with new flags
./scripts/build-handouts.sh    # rebuild handouts with new flags
python3 scripts/ctfd-setup.py  # push the new flags to CTFd
```

The last line pushes the new flags to CTFd; player accounts and scores are
kept, and so are the players' terminal spaces (logins, files, sessions). To
wipe them too before a new event, use `docker compose down -v` (it deletes the
`ctfd-data` and `toolbox-data` volumes) and redo CTFd's setup wizard.

---

## What's where

```
challenges/            one folder per challenge (player README + web app code)
hub/                   "cellule de crise": players' entry point (port 8080)
share/                 "Intranet DécaFlop": intranet site + internal file share (port 8020, not a challenge)
handouts/              generator for all forensics/SAP evidence files
  generate.py          builds every handout from .env flags
  assets/              base photo for 03 (AI-generated, metadata stripped)
  HOSTING.md           Pi 5 + travel-router hosting guide
scoreboard/            how to run a scoreboard on the Pi (CTFd-lite / static)
scripts/
  gen-flags.sh         create .env with fresh random flags
  ctfd-setup.py        load the challenges (flags, hints) into CTFd
  build-handouts.sh    build the handout files in handouts/dist/
docker-compose.yml     the live web + SAP challenges
docker-compose.cloudflare.yml  optional online overlay (Cloudflare Tunnel, see CLOUDFLARE.md)
CLOUDFLARE.md          optional online hosting runbook (Tunnel + Access)
.env.example           flag template (the real .env is git-ignored)
WRITEUPS/              organizer solutions (git-ignored, shared privately)
```

Every internal tool (the share, the staff portal and challenges 04, 06, 10,
11, 12, 14) shares one intranet look: `intranet.py` (page chrome) and
`static/intranet.css`. Each Docker build only sees its own folder, so the two
files are copied into every app; `tests/test_intranet_assets.py` fails if a
copy drifts. Edit them in `share/app/`, then copy them to the others.
