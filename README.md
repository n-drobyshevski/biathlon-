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
| 02 | Share Everywhere | Forensics/Stego | Easy | 50 | handout |
| 03 | In Transition | Forensics | Easy | 75 | handout |
| 04 | Not Your Profile | Web (IDOR) | Medium | 100 | live (`:8004`) |
| 05 | The Timing Booth | Forensics (pcap) | Medium | 100 | handout |
| 06 | Results Admin | Web (SQLi) | Medium | 125 | live (`:8006`) |
| 07 | The Referee's USB | Forensics (carving) | Medium | 125 | handout |
| 08 | SAP DFlop ERP | **SAP** | **Hard** | 200 | live (`:8008`) |
| 09 | Who Rigged the Race? 🏁 | **SAP** | **Hard** | 250 | handout (finale) |

3 easy · 4 medium · 2 hard. The two hard challenges are the SAP ones.
Total 1075 pts. Flag format: `TRIATHLON{...}`.

Each challenge folder has a player-facing `README.md` (prompt + point-costed
hints). The live web/SAP apps are Flask containers; the forensics/stego/SAP
files are generated as downloadable handouts.

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
```

**Players only need one address: `http://<PiIP>:8001/cellule-de-crise`.**
That page on the DécaFlop site is the in-story "crisis cell": it briefs the
team, lists all 9 missions, links the live challenges and serves every handout
file (straight from `handouts/dist/`). The shop's homepage and every page's
top strip link to it. It never links the hidden staff portal, so challenge 01
stays a puzzle, and no mission is locked behind another.

Live services after step 2:

| Port | Challenge |
|------|-----------|
| 8001 | DécaFlop site + crisis cell (players' entry point) · 01 staff portal |
| 8004 | 04 athlete portal (IDOR) |
| 8006 | 06 results admin (SQLi) |
| 8008 | 08 SAP DFlop ERP |

Handout files after step 3 (downloadable from the crisis cell as soon as they
are built; you can also attach them in CTFd or pass a USB stick around):

```
decaflop_poster.png     -> 02
transition_shot.jpg     -> 03
timing_booth.pcap       -> 05
referee_usb.img         -> 07
SAP_USR02_export.csv + sap_hint.txt + wordlist.txt + case_file.zip  -> 09
```

See [`scoreboard/README.md`](scoreboard/README.md) for the scoreboard options
and [`handouts/HOSTING.md`](handouts/HOSTING.md) for the Pi 5 + travel-router
setup, resource notes, reset, and the pre-event test checklist.

---

## Resetting between runs

```bash
docker compose down            # stop challenges
./scripts/gen-flags.sh         # rotate flags (overwrite .env)
docker compose up -d --build   # restart with new flags
./scripts/build-handouts.sh    # rebuild handouts with new flags
```

Update the flags in your scoreboard to match the new `.env` after rotating.

---

## What's where

```
challenges/            one folder per challenge (player README + web app code)
handouts/              generator for all downloadable forensics/SAP files
  generate.py          builds every handout from .env flags
  assets/              base photo for 03 (AI-generated, metadata stripped)
  HOSTING.md           Pi 5 + travel-router hosting guide
scoreboard/            how to run a scoreboard on the Pi (CTFd-lite / static)
scripts/
  gen-flags.sh         create .env with fresh random flags
  build-handouts.sh    build the handout files in handouts/dist/
docker-compose.yml     the live web + SAP challenges
.env.example           flag template (the real .env is git-ignored)
WRITEUPS/              organizer solutions (git-ignored, shared privately)
```
