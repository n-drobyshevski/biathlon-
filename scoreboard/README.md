# Scoreboard on the Pi

You need somewhere for teams to submit flags and see the board. Two options.

## Option A — CTFd (default, included)

CTFd handles **teams, flag checking, the point-costed hints and the live
scoreboard**. It's part of `docker-compose.yml` (image `ctfd/ctfd:3.8.8`,
arm64-native, SQLite, data in the `ctfd-data` volume, ~0.5–0.7 GB RAM), so
`docker compose up -d --build` starts it with everything else on port **8000**.
Pull the images once while you still have internet.

**One-time setup (≈5 minutes):**

1. Open `http://<PiIP>:8000` and complete the setup wizard: event name, **user
   mode "Teams"**, your admin account. Leave registration open so teams can
   sign up themselves.
2. In CTFd, open **Settings → Access Tokens** (your admin profile) and generate
   a token. Put it in `.env`, with the address players use:
   ```
   CTFD_TOKEN=ctfd_...
   CTF_HOST=192.168.8.2
   ```
3. Load the challenges:
   ```bash
   python3 scripts/ctfd-setup.py
   ```
   It reads every `challenges/*/README.md` and creates the 9 challenges with
   category, points, description (with the connection link and download links
   to the cellule de crise), the flag from `.env` and the hints with their
   costs. It also sets CTFd's default language to French (`--locale` to change).
   Add `--dry-run` to see what it would do without touching CTFd.

**Cross links (set up by the script):**

- **CTFd → hub:** a "Cellule de crise" item in CTFd's top menu (opens the hub
  in a new tab), and each challenge description links to its own row in the
  hub (`:8080/#mission-04`, highlighted on arrival).
- **Hub → CTFd:** a "Tableau des scores" button, and on every mission a
  "Soumettre le flag" link that opens **that challenge** in CTFd. The script
  writes the CTFd challenge ids to `handouts/dist/ctfd_ids.json` for this;
  without it, the links open the challenge list instead.

The menu link uses `CTF_HOST`: if the Pi's address changes, re-run the script.

**After rotating flags** (`./scripts/gen-flags.sh`), just re-run
`python3 scripts/ctfd-setup.py`: it replaces the flags and updates the texts in
place (your token and host are kept in `.env`). Re-running is safe even
during play: solves and unlocked hints are kept, because hints are updated in
place rather than recreated.

**Reset between events:** `docker compose down -v` wipes CTFd's database (and
nothing else that matters), then redo the one-time setup.

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
| 01 | The Sponsor's Secret | 75 |
| 02 | Share Everywhere | 50 |
| 03 | In Transition | 75 |
| 04 | Not Your Profile | 100 |
| 05 | The Timing Booth | 100 |
| 06 | Results Admin | 125 |
| 07 | The Referee's USB | 125 |
| 09 | Who Rigged the Race? | 250 |
| 10 | Forged Credentials | 175 |
| 11 | Deleted, Not Gone | 150 |
| 12 | Print Your Own | 175 |
| 13 | Saved for Convenience | 75 |
| 14 | The Open Gateway | 150 |
| 15 | Hardcoded | 150 |

Hints and their point costs are listed in each challenge's `README.md`.
(`scripts/ctfd-setup.py` loads all of this automatically.)
