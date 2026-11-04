# Online hosting (optional): Cloudflare Tunnel + Cloudflare Access

The lab is built to run **offline** on a Raspberry Pi behind a travel router
(see [handouts/HOSTING.md](handouts/HOSTING.md)). That stays the default and
does not change.

This page is for the other case: players on locked-down corporate laptops
(always-on Zscaler, no access to a local LAN) who can only reach a normal HTTPS
website. You publish the lab through an **outbound-only Cloudflare Tunnel**, and
**Cloudflare Access** puts a login in front of every hostname. Nothing on the
Pi accepts inbound connections: no port forwarding, no public IP, no open
firewall.

```
player browser ──HTTPS──▶ Cloudflare edge ──Access login──▶ tunnel ◀──outbound── cloudflared (Pi)
                                                                                   │ internal-only networks
                                                         hub · ctfd · staff · share · idor · sqli · jwt
                                                         gitleak · ssti · sapgw · cyberchef · toolbox
```

> [!WARNING]
> **The challenges are deliberately vulnerable, and some give remote code
> execution (12 = SSTI).** Never add a Public Hostname that does not have a
> Cloudflare Access policy in front of it, not even "just for a minute to test".
> Without Access, anyone on the internet can get a shell on your Pi's
> containers. If in doubt, delete the hostname or stop `cloudflared`.

## What the overlay does (repo side, already done)

`docker-compose.cloudflare.yml` is an overlay. You only get it when you name
both files:

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d
```

It assumes **a challenge container will be popped**, and contains the damage:

| Measure | Effect |
| --- | --- |
| Every service is **only** on `internal: true` networks | No internet egress, no route to your LAN. A shell in `ssti` cannot download tools, call out to a C2 or scan your network. Verified: `connect 1.1.1.1` gives `Network is unreachable`, and DNS for external names fails. |
| Segmented networks: `internal` (challenges, share, toolbox), `scoreboard` (CTFd), `front` (hub), `chef` (CyberChef) | A popped challenge cannot reach CTFd or the hub at all: their names don't resolve and their IPs are unreachable (verified). So nobody can brute-force CTFd's login or API from inside, past Access. The terminal still reaches every challenge by name. |
| Only `cloudflared` joins all of them plus `edge` (normal bridge, interface `ctf-edge`) | It is the one container that can reach the internet, and it only dials **out** to Cloudflare. |
| No host ports on the public interface | Docker does not publish ports for containers that are only on an internal network. The overlay pins the port lists to `127.0.0.1` anyway as a fail-safe, and `BIND_ADDR=127.0.0.1` does the same for the base file. |
| No repo, `.env`, flags or docker socket mounted | Each challenge still gets only its own `FLAG` env, as offline. `hub`, `staff` and `share` keep their read-only `handouts/dist` mount: the evidence files players download anyway. |
| Non-root, `cap_drop: ALL`, `no-new-privileges` | The Flask apps (incl. `gitleak`) run as `nobody`. CTFd runs as its own user. nginx (`cyberchef`) keeps only the 4 capabilities it needs. `toolbox`: ttyd runs as root with only `SETUID`/`SETGID`/`CHOWN`/`KILL`, to hand every browser tab its own Unix user (`joueur01`..`joueur24`, no capabilities). All of this is in the base file, so it applies offline too. |
| Read-only root filesystem everywhere, scratch on small `tmpfs` | A popped app cannot rewrite its own code or pages to deface them for everyone; `restart <service>` brings it back pristine. CTFd's state stays in its `ctfd-data` volume. The terminal's `/work` is a 256 MB tmpfs; each seat's home in it is wiped as soon as its tab closes. |
| `pids_limit` + `cpus` caps | A fork bomb in a challenge stops at 128 processes (verified: the app keeps serving) and cannot starve the Pi. |
| Terminal: ttyd `-O` (`--check-origin`), `-m 20` | ttyd refuses WebSockets opened from another origin. A script a player plants on another lab subdomain cannot open a shell with someone else's Access cookie (verified: same-origin gets 101, `ssti.<domain>` as Origin is dropped). At most 20 concurrent terminals. |
| Images pinned by tag **and digest** (`cloudflared:2026.10.1@sha256:a15a…`, `ctfd:3.8.8@sha256:07cc…`), `--no-autoupdate` | A re-tagged or tampered upstream image cannot slip in, and nothing changes under you mid-event. To bump: `docker buildx imagetools inspect <image>:<tag>`, then copy the top-level digest (multi-arch, includes arm64). |
| Hub links → subdomains | The overlay sets `SITE_URL=https://site.${CTF_DOMAIN}/` etc., so the cellule de crise links to `https://<svc>.<domain>/` instead of `host:port`. The intranet "Applications" menus of the challenges switch to subdomains by themselves when they are reached on one. |
| cloudflared metrics on loopback (`--metrics 127.0.0.1:20241`) | In a container cloudflared otherwise listens on `0.0.0.0:20241`, on the same network as the challenges. Verified: from a popped `ssti`, that port served `/metrics`, `/config` (every hostname and origin) and `/debug/pprof` (heap dumps of the process holding the tunnel token). Now closed. |
| Tunnel egress allowlist (optional script, step 4b) | `scripts/cloudflare-egress.sh` limits the `ctf-edge` bridge to DNS, tcp/udp 7844 and tcp 443 on public addresses. Without it the tunnel container could reach your LAN, your router, the metadata address and the Pi itself (verified); with it, all of those are rejected. |
| CTFd `REVERSE_PROXY=true` | CTFd trusts cloudflared's `X-Forwarded-Proto/Host` and builds its own `https://ctfd.<domain>` URLs. |

## Operator runbook (Cloudflare dashboard side)

You need a domain whose DNS is on Cloudflare. A free plan is enough for both
Tunnel and Access (Zero Trust free tier: up to 50 users). Below, `<domain>` is
the base you put in `CTF_DOMAIN`: a zone such as `example.com`, or a sub-zone
such as `ctf.example.com`.

> On Cloudflare's free Universal SSL certificate, `*.example.com` covers only
> **one** level of subdomain. With `CTF_DOMAIN=ctf.example.com`, the hostnames
> `hub.ctf.example.com` and so on are two levels deep. They then need Advanced
> Certificate Manager or a dedicated certificate for `*.ctf.example.com`.
> Simplest: use the zone apex (`CTF_DOMAIN=example.com`), or a domain bought
> for the event.

### 1. Create the tunnel

1. Zero Trust dashboard → **Networks → Tunnels → Create a tunnel** →
   *Cloudflared*. Name it, e.g. `decaflop-ctf`.
2. On the "Install connector" step, choose **Docker**. Copy only the token,
   the long string after `--token`.
3. On the Pi, put it in `.env`, which is git-ignored, mode 600. **Never commit
   it**: anyone holding it can serve your hostnames.

   ```ini
   TUNNEL_TOKEN=eyJhIjoi...           # from step 2
   CTF_DOMAIN=example.com             # base of hub.<domain>, ctfd.<domain>, ...
   BIND_ADDR=127.0.0.1                # base file binds loopback only
   ```

   `./scripts/gen-flags.sh` keeps these three lines when it rotates flags.

### 2. Add one Public Hostname per service

In the tunnel → **Public Hostname → Add a public hostname**. The service URL
is the **internal** docker name and port, never the Pi's IP or a host port:

| Public hostname | Service type | URL |
| --- | --- | --- |
| `hub.<domain>` | HTTP | `hub:5000` |
| `ctfd.<domain>` | HTTP | `ctfd:8000` |
| `site.<domain>` | HTTP | `staff:5000` |
| `share.<domain>` | HTTP | `share:5000` |
| `idor.<domain>` | HTTP | `idor:5000` |
| `sqli.<domain>` | HTTP | `sqli:5000` |
| `jwt.<domain>` | HTTP | `jwt:5000` |
| `git.<domain>` | HTTP | `gitleak:5000` |
| `ssti.<domain>` | HTTP | `ssti:5000` |
| `sapgw.<domain>` | HTTP | `sapgw:5000` |
| `cyberchef.<domain>` | HTTP | `cyberchef:80` |
| `terminal.<domain>` | HTTP | `toolbox:7681` |

- `terminal` (ttyd) needs **WebSockets**. They are on by default for tunnels.
  Check that zone → **Network → WebSockets** is enabled.
- `terminal` only: set **Additional application settings → HTTP Settings →
  HTTP Host Header** = `terminal.<domain>`. ttyd's origin check (`-O`) compares
  the browser's `Origin` with the `Host` it receives, and pinning it here makes
  them match whatever cloudflared's default is. Symptom if they don't match:
  the terminal page loads, then says the connection was closed.
- Recommended: zone → **SSL/TLS → Edge Certificates → Always Use HTTPS** = on.
  Some challenge pages print their own address back, and the apps only see
  plain HTTP from cloudflared.
- Do **not** add a catch-all for the whole domain pointing anywhere, and do
  **not** add `http://localhost:...` style origins. Every hostname maps to
  exactly one service.

### 3. Put Cloudflare Access in front of every hostname (mandatory)

**Do this before anyone gets the URL.** It is what keeps the open internet out.

1. Zero Trust → **Access → Applications → Add an application → Self-hosted**.
2. Application domain: `*.<domain>` (a wildcard covers all 12 hostnames and any
   you add later). If you prefer, create one application per hostname instead,
   but then **every** hostname from step 2 must be listed.
3. Session duration: the length of the event, e.g. 12 h.
4. Policy, action **Allow**. Pick one:
   - **Emails**: the invited players' addresses, or **Emails ending in**
     `@company.com`. Login is by one-time PIN sent to that address.
   - Or an identity provider group (Google Workspace, Entra ID, ...) if you set
     one up.
   Do **not** use "Everyone", or a "Bypass" or "Service auth" action, on these
   hostnames.
5. Zero Trust → **Settings → Authentication**: make sure **One-time PIN** is
   enabled (it is the default login method).
6. Test from a private browser window: `https://hub.<domain>` must show the
   Cloudflare Access login page **before** any lab content. Check one challenge
   host too, e.g. `https://ssti.<domain>`.

### 3b. Make the tunnel itself refuse unauthenticated requests (fail-closed)

Access at the edge is the gate. This step adds a second lock **in cloudflared**,
so a mistake in step 3 fails closed: a deleted Access app, a hostname added
later and missed by a non-wildcard app, or a policy changed to Bypass.

1. Access → Applications → your app → **Overview**: copy the **Application
   Audience (AUD) tag**. Note your **team name**: the `<team>` in your team
   domain `<team>.cloudflareaccess.com`, shown in Zero Trust settings.
2. For **each** Public Hostname of the tunnel: **Additional application
   settings → Access**, turn on JWT enforcement (labelled "Protect with Access"
   or "Enforce Access JSON Web Token (JWT) validation", depending on the
   dashboard version) with that team name and AUD tag.

   This is `originRequest.access: {required: true, teamName, audTag}` in the
   tunnel config. cloudflared then checks the `Cf-Access-Jwt-Assertion` header
   that Access adds, and drops any request without a valid token for that
   application, before it reaches the lab.
3. Re-test step 3.6. Logged-in players see no difference.

### 3c. Tighten the Access application (recommended)

- **Session duration** = the event window (e.g. 12 h), not the 24 h+ default.
- **Login methods**: one-time PIN or your IdP only. **Never** Bypass, Service
  Auth or Everyone on lab hostnames.
- Optional extra **Require** rule in the Allow policy, e.g. *Country* = the
  countries your players are in, so a leaked PIN email is useless from
  elsewhere.
- After the event, review **Logs → Access** for who logged in, and when.
- **Cookie settings** (application → Settings → Cookie settings). The lab
  pages are deliberately vulnerable, so assume a player can plant a script on
  one of them:
  - **HTTP Only**: keep it **on** (the default). Scripts on a lab page cannot
    read the `CF_Authorization` cookie.
  - **Enable Binding Cookie**: **on**. Access issues a second cookie at login
    and rejects `CF_Authorization` without it, so a stolen session cookie
    cannot be replayed from another browser. It is browser-only, which is fine
    here: every lab hostname is used from a browser, the terminal included.
  - **SameSite**: optional. *Lax* is safe, since all lab hostnames are
    subdomains of one site.

### 3e. Lock the CTFd admin pages to the organizers (recommended)

The wildcard application lets every invited player reach `ctfd.<domain>`,
including `/admin`. Put the admin pages behind their own, stricter
application:

1. Access → Applications → **Add an application → Self-hosted**. Domain
   `ctfd.<domain>`, **path** `admin`.
2. Policy **Allow**, *Emails* = the organizers only.
3. Access applies the most specific path, so this app wins over the wildcard
   app for `/admin`, and `/admin/...` inherits it.
4. Test from a private window: a player address must be refused at
   `https://ctfd.<domain>/admin`, while the scoreboard still works for them.
   An organizer address must get in.

This guards the admin UI. Still give the CTFd admin account a strong, unique
password. `ctfd-setup.py` talks to CTFd's container IP from the Pi, so it is
not affected.

### 3d. Optional: rate-limit the scoreboard

The free plan includes one rate-limiting rule (Security → WAF → Rate limiting
rules). If you want it, point it at `ctfd.<domain>` with path `/login` or
`/api/v1/challenges/attempt`, counted per IP, action Block. Players are
already authenticated, and CTFd has its own submission throttle, so this only
slows down a player scripting flag guesses.

### 4. Start the lab in online mode

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml logs -f cloudflared   # "Registered tunnel connection"
```

#### 4b. Restrict the tunnel's own egress (recommended)

The lab containers have no egress at all. `cloudflared` must reach the
internet, but it only needs DNS, Cloudflare's edge on port **7844** (TCP for
HTTP/2, UDP for QUIC), and **443** (Cloudflare API, Access signing keys,
update checks). That matches Cloudflare's "Tunnel with firewall" requirements.
Lock its bridge (`ctf-edge`) down to exactly that:

```bash
sudo scripts/cloudflare-egress.sh apply     # idempotent; re-run any time
sudo scripts/cloudflare-egress.sh status    # rules + packet counters
sudo journalctl -k | grep ctf-edge-drop     # what got rejected (rate-limited log)
sudo scripts/cloudflare-egress.sh remove    # undo
```

It also rejects every private, CGNAT, link-local and reserved destination,
so no LAN hosts, no router admin page and no metadata service, even on ports
53, 443 and 7844. It also rejects any connection from the container to the
Pi itself (SSH etc.). It needs Docker's default iptables firewall backend, and
it only touches its own chains (`CTF-EDGE`, `CTF-EDGE-IN`).

The rules do not survive a reboot. Either re-run `apply` after boot, or
install a oneshot unit (adjust the path):

```ini
# /etc/systemd/system/ctf-egress.service
[Unit]
Description=DecaFlop CTF: restrict the Cloudflare tunnel's egress
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/home/pi/biathlon-/scripts/cloudflare-egress.sh apply
ExecStop=/home/pi/biathlon-/scripts/cloudflare-egress.sh remove

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now ctf-egress
```

If the tunnel stops connecting after `apply`, look at the counters and the
`ctf-edge-drop` log. Something other than DNS, 7844 or 443 is needed, e.g. the
venue network forces an outbound HTTP proxy on a private address (a
locked-down network like that usually blocks 7844 anyway; see Cloudflare's
"Tunnel with firewall" page). Then `remove`, investigate, and re-apply.

The overlay refuses to start if `TUNNEL_TOKEN` or `CTF_DOMAIN` is missing from
`.env`.

Load the challenges into CTFd with online links. Finish the CTFd setup wizard
at `https://ctfd.<domain>` first. Online, CTFd publishes no host port, so the
script talks to its container IP (the host can reach it; containers cannot
reach the host's LAN):

```bash
CTFD_URL=http://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
    $(docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml ps -q ctfd)):8000 \
  python3 scripts/ctfd-setup.py --base-domain example.com      # or CTF_DOMAIN in .env
```

Every challenge's **Connect** line then points at its subdomain:

| Challenges | Connect |
| --- | --- |
| 01, 02, 03 | `https://site.<domain>` |
| 04 | `https://idor.<domain>` |
| 05, 07, 09, 13, 15 | `https://share.<domain>` |
| 06 | `https://sqli.<domain>` |
| 10 | `https://jwt.<domain>` |
| 11 | `https://git.<domain>` |
| 12 | `https://ssti.<domain>` |
| 14 | `https://sapgw.<domain>` |

The "Cellule de crise" menu item and the mission links go to
`https://hub.<domain>/`. Titles, flags and hints are the same as offline.
Use `--dry-run` to preview.

### 5. Players

Send players **one address: `https://hub.<domain>`**. They log in through
Access (one-time PIN to their email), then play from the cellule de crise as
usual. Every link opens the matching subdomain, and Access remembers them for
the session.

## The team terminal online

The toolbox (`terminal.<domain>`) is on the internal network too: **it has no
internet and there is no Pi IP to use.** It reaches the services by their
internal name on port 5000. Every service also answers on the same name as its
subdomain (aliases `site` for `staff`, `git` for `gitleak`). The banner tells
players that. Examples (organizer reference, **not** for the banner):

```bash
wget http://share:5000/telecharger/...          # an evidence file (copy the link from the share)
git-dumper http://gitleak:5000/.git/ dump       # mission 11 (http://git:5000/.git/ works too)
```

Files players download in the browser come straight from
`https://share.<domain>`. CyberChef runs entirely in their browser.

## Containment and incident notes

- **Assume compromise.** A popped challenge has no egress and no LAN access.
  It can reach the other challenges, the share and the terminal on the
  `internal` network, exactly like a player can, and nothing else: not CTFd,
  not the hub, not CyberChef. It cannot rewrite its own files either, and a
  restart wipes whatever it left in `/tmp`.
- **Rotate flags** if they leak (e.g. someone posts one):
  `./scripts/gen-flags.sh`, then
  `docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --force-recreate`,
  then re-run `ctfd-setup.py` as above (it replaces the flags in place). The
  tunnel token, domain and bind address survive the rotation.
- **Rebuild a trashed service** (a vandalised page, a stuck process):
  `docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d --build --force-recreate <service>`.
  The apps are stateless. CTFd state lives in the `ctfd-data` volume, so do not
  `down -v` unless you want to wipe scores.
- **Cut access instantly**: stop the tunnel
  (`docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml stop cloudflared`),
  or delete the Public Hostnames, or disable the tunnel in the dashboard.
  Revoke the token (Tunnels → *your tunnel* → Refresh token) if `.env` might
  have leaked.
- **After the event**: **Refresh the tunnel token** (Tunnels → *your tunnel*),
  then delete the Public Hostnames and the Access application, or the whole
  tunnel. Then go back to offline mode with a plain
  `docker compose up -d`. Unset `BIND_ADDR` in `.env` first, or the base file
  stays loopback-only.

## Going back to offline mode

```bash
docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml down
# in .env: comment out BIND_ADDR (TUNNEL_TOKEN / CTF_DOMAIN are ignored offline)
docker compose up -d
```

Offline, nothing in this page applies: the services publish their usual ports
on every interface, and the hub links use `http://<PiIP>:<port>`.
