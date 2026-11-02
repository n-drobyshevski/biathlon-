# Scoreboard on the Pi

You need somewhere for teams to submit flags and see the board. Two options.

## Option A — CTFd (full-featured, heavier)

CTFd is the classic Jeopardy scoreboard. On a 4 GB Pi, run it **slim**: SQLite
instead of MySQL, and Redis optional. It fits alongside the 4 challenge
containers, but it's the heaviest single piece — test it before the event.

```bash
git clone https://github.com/CTFd/CTFd   # do this WITH internet, before the event
cd CTFd
# docker-compose.yml ships with MySQL+Redis; for a Pi, prefer the single
# container with SQLite:
docker run -d -p 8000:8000 \
  -e DATABASE_URL=sqlite:////data/ctfd.db \
  -v "$PWD/ctfd-data:/data" \
  --memory=768m --name ctfd ctfd/ctfd:latest
```

Then in the CTFd admin UI:

1. Create challenges matching `challenges/*/README.md` (title, category,
   points, description, hints with their point costs).
2. Set each flag to the matching value from your `.env`
   (`FLAG_01_STAFF` … `FLAG_09_SAP_USR02`). **Static, case-sensitive.**
3. Handout files are served by the cellule de crise
   (`http://<PiIP>:8080`), so you can just link it. Uploading
   them as CTFd challenge files also works.
4. For the live web/SAP challenges, put the connection URL
   (`http://<PiIP>:8001` …) in the description, or link the cellule de crise,
   which has a button for each.
5. Set `SCOREBOARD_URL=http://<PiIP>:8000` in `.env` (then
   `docker compose up -d`) to add a "Soumettre un flag" button to the
   cellule de crise.

> Flags change every time you run `gen-flags.sh`. Re-enter them in CTFd after
> rotating, or keep the flags fixed between runs by not re-running gen-flags.

## Option B — rCTF / static board (lightest)

If CTFd feels heavy, any lightweight flag-checking board works, or for a very
small event you can even run it "honour system": hand out the challenge
READMEs, keep the flags in `.env`, and check submissions manually / in a shared
spreadsheet. For 6 people in one room this is genuinely fine and uses zero
extra RAM.

## Categories to configure

`Web` · `Forensics` · `SAP`

## Point values (suggested)

| # | Challenge | Pts |
|---|-----------|-----|
| 01 | The Sponsor's Secret | 50 |
| 02 | Share Everywhere | 50 |
| 03 | In Transition | 75 |
| 04 | Not Your Profile | 100 |
| 05 | The Timing Booth | 100 |
| 06 | Results Admin | 125 |
| 07 | The Referee's USB | 125 |
| 08 | SAP DFlop ERP | 200 |
| 09 | Who Rigged the Race? | 250 |

Hints and their point costs are listed in each challenge's `README.md`.
