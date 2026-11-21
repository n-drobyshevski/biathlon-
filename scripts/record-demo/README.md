# Demo video recorder

Records a ~6-minute walkthrough of the whole lab, for presenting it to people
who cannot sit on the event's Wi-Fi (a video call, a meeting room). Everything
runs against the real services, offline; the video is 1080p / 30 fps, with
French documentary-style captions and chapter titles.

The page is shown inside a fake browser window (`harness.html`: tabs, address
bar, loading spinner) with the Pi's address in the address bar. A Playwright
script drives it like a person would: eased mouse moves, typed URLs, smooth
scrolling, zooms on the important bits. Frames come from Playwright's
`page.screencast` and go straight to ffmpeg (x264), not through the built-in
low-bitrate video recorder.

## What the video shows

1. The *cellule de crise* (`:8080`): briefing, the Contexte sheet.
2. A player creates their CTFd account (`:8000`), on camera.
3. Mission 01 (robots.txt → staff portal → flag), the front-end leak of the
   Intranet login, the Intranet (`:8020`) and its SAP export preview.
4. Missions 04 (IDOR) and 06 (SQL injection).
5. The players' tools from the Outils tab: CyberChef (`:8090`) decodes the
   leaked base64 login, the team terminal (`:8091`) signs in, `grab`s the
   mission 03 photo and reads its EXIF (author, time, camera, GPS: not the flag).
6. Mission 14 on the SAP portal (`:8014`): Basis logon, SM37, SE16N, SMGW,
   open `reginfo`, registration → flag.
7. Back to the hub (mission marked *Résolu*), the flag submitted in CTFd,
   the tile turns green, the scoreboard with six teams.

At most four tabs are open at any time; finished ones are closed on camera.

**The video shows real flags** (01, 04, 06, 14, plus the CTFd scoreboard) and
the answers to the finale (who, when). Record it on a throwaway set of flags,
then rotate them before the event (`./scripts/gen-flags.sh`, rebuild the
handouts, `scripts/ctfd-setup.py`: see the main README, "Resetting between runs").

## Prerequisites

- The lab running: `docker compose up -d` (with CTFd, CyberChef and the
  toolbox), handouts built, CTFd's setup wizard done and
  `python3 scripts/ctfd-setup.py` run (it needs `CTFD_TOKEN` in `.env` and
  writes `handouts/dist/ctfd_ids.json`).
- On the machine that records (the Pi or a laptop on the travel router):
  Node.js 18+, ffmpeg, and Playwright's Chromium:

  ```bash
  cd scripts/record-demo
  npm install
  npx playwright install chromium
  ```

## Record

```bash
# 1) CTFd demo data. DESTRUCTIVE: deletes every non-admin account, then adds
#    five demo teams with real solves spread over the last hour. Never on the
#    event's CTFd once players signed up. --reset-terminal also frees the
#    pseudo the video uses in the team terminal.
python3 scripts/record-demo/seed-ctfd.py --yes --reset-terminal

# 2) the recording (about 7 minutes of wall-clock time)
cd scripts/record-demo
SHOW_HOST=192.168.8.2 APP_HOST=192.168.8.2 node record.js demo.mp4
```

Run step 1 again before every new take: the video registers `equipe-it-03`
on camera, in CTFd and in the terminal, so the name must be free.

The five demo teams (`equipe-it-01`, `-02`, `-04`, `-05`, `-06`) are made-up
data; say so when you show the video.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SHOW_HOST` | `192.168.8.2` | Address shown in the address bar, and used by the terminal's `grab` |
| `APP_HOST` | `127.0.0.1` | Where the services really answer (the Pi's IP when recording from a laptop) |
| `PLAYER` / `PLAYER_PASS` | `equipe-it-03` / `Demo-2026!` | Account created on camera |
| `STEP_LOG` | unset | `1` prints each caption with a timestamp, to find a scene in the video |

Logins (Intranet, SAP Basis) and the mission 14 flag are read from the repo's
`.env`, so they always match the running lab. The closing card says
"16 missions · 2175 points": update it in `record.js` if the game changes.

## How it works

- `record.js` starts a small HTTP proxy that the browser goes through: it
  serves `harness.html`, maps `SHOW_HOST:<port>` to `APP_HOST:<port>`, adds a
  realistic 0.3–0.65 s delay to page loads and tunnels the terminal's
  WebSocket. Redirects, cookies and the `Host` header behave as on the Pi.
- Each tab of the fake window is an `<iframe>`; the address bar, title and
  spinner follow the iframe's real navigations.
- Links that open a new tab (`target="_blank"`: the hub's tools, CTFd) are
  shown as a new tab of the fake window.
- If a step does not produce what the caption claims (for instance CyberChef
  did not decode), the script stops with an error instead of recording a
  wrong scene.
