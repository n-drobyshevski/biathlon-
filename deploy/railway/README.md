# Railway test deploy (temporary)

A throwaway copy of the online lab on Railway, used to test the Cloudflare
Tunnel + Access path (domain, login, Zscaler, terminal WebSocket) before the
Pi is ready. **Not for the event**: Railway cannot block outbound traffic from
containers (no `internal: true` networks, no egress firewall), so a popped
challenge there could reach the internet. Delete the project after testing.

## What runs there
One Railway service per lab service, named exactly like the compose services
(`hub`, `staff`, `share`, `idor`, `sqli`, `jwt`, `gitleak`, `ssti`, `sapgw`,
`ctfd`, `cyberchef`, `toolbox`, `cloudflared`), so each is reachable on
Railway's private network as `<name>.railway.internal`. None has a public
Railway domain: the only way in is the tunnel, behind Cloudflare Access.

- Most services build from their own folder's Dockerfile.
- `share` and `staff` use `deploy/railway/{share,staff}.Dockerfile` (build
  context: repo root). Railway has no `handouts/dist` bind mount, so they
  generate the evidence files from their `FLAG_*` variables at start.
- `cyberchef` uses `deploy/railway/cyberchef.Dockerfile`: the build downloads
  the pinned official release (v10.19.4) from GitHub and checks its SHA-256
  (the Pi build uses the zip you drop in by hand instead).
- `toolbox` start command adds ttyd's `-O -m 20`, as in the overlay.
- `cloudflared`: the pinned image, start command
  `cloudflared tunnel --no-autoupdate --metrics 127.0.0.1:20241 run`,
  `TUNNEL_TOKEN` pasted by you in Railway → cloudflared → Variables.
- `ctfd`: the pinned image, a volume on `/var/uploads`, `RAILWAY_RUN_UID=0`
  (Railway volumes are root-owned).
- Flags are random test flags in the environment's shared variables.

## Tunnel routes: one set for Railway and the Pi
Point the tunnel's public hostnames at `<service>.railway.internal`:

| Hostname | Service URL |
| --- | --- |
| `hub.<domain>` | `http://hub.railway.internal:5000` |
| `ctfd.<domain>` | `http://ctfd.railway.internal:8000` |
| `site.<domain>` | `http://staff.railway.internal:5000` |
| `share.<domain>` | `http://share.railway.internal:5000` |
| `idor` / `sqli` / `jwt` / `ssti` / `sapgw` `.<domain>` | `http://<name>.railway.internal:5000` |
| `git.<domain>` | `http://gitleak.railway.internal:5000` |
| `cyberchef.<domain>` | `http://cyberchef.railway.internal:80` |
| `terminal.<domain>` | `http://toolbox.railway.internal:7681` (+ HTTP Host Header `terminal.<domain>`) |

`docker-compose.cloudflare.yml` gives every service the same
`<service>.railway.internal` alias, so **these routes also work unchanged on
the Pi**. Inside the Railway terminal, services are `share.railway.internal`
etc. (the banner's short names only exist on the Pi).

## Before the real event
**Delete the Railway project** (or at least its `cloudflared` service) before
starting the Pi. Two connectors on one tunnel share the traffic, so players
would randomly land on Railway instead of the Pi.
