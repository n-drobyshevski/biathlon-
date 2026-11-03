#!/usr/bin/env bash
# ============================================================================
#  cloudflare-egress.sh — restrict the tunnel container's own network access
#  (OPTIONAL online mode only, see CLOUDFLARE.md).
#
#  In docker-compose.cloudflare.yml every lab service is on internal-only
#  networks; `cloudflared` alone is also on `edge`, a normal bridge with the
#  fixed interface name `ctf-edge`. By default that bridge can reach anything:
#  the internet, your LAN, your router, the Pi itself. The tunnel only needs:
#    - DNS (udp/tcp 53)
#    - Cloudflare's edge on port 7844 (tcp = HTTP/2, udp = QUIC)
#    - tcp 443 (Cloudflare API, Access JWT signing keys, update checks)
#  This script lets exactly that through and rejects the rest, including any
#  private / link-local / CGNAT destination (no LAN, no router admin page, no
#  metadata service) and any connection to the Pi itself (SSH etc.).
#
#  Usage (on the Pi, as root, AFTER `docker compose ... up -d`):
#    sudo scripts/cloudflare-egress.sh apply     # install / refresh (idempotent)
#    sudo scripts/cloudflare-egress.sh status    # show the rules + counters
#    sudo scripts/cloudflare-egress.sh remove    # take them out again
#
#  Rules live in their own chains (CTF-EDGE, CTF-EDGE-IN) hooked from Docker's
#  DOCKER-USER chain and from INPUT. They are not persistent across reboots:
#  re-run `apply`, or use the systemd unit shown in CLOUDFLARE.md. Rejected
#  packets are logged (rate-limited) with the prefix "ctf-edge-drop".
#  Offline mode never creates `ctf-edge`, so these rules match nothing there.
# ============================================================================
set -euo pipefail

IFACE="ctf-edge"
FWD="CTF-EDGE"            # forwarded traffic from the tunnel container
INP="CTF-EDGE-IN"         # traffic from the tunnel container to the Pi itself

# private, CGNAT, link-local (metadata), reserved/documentation, multicast
PRIVATE4="10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 100.64.0.0/10 169.254.0.0/16 0.0.0.0/8 192.0.0.0/24 192.0.2.0/24 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/4 240.0.0.0/4"
PRIVATE6="fc00::/7 fe80::/10 ff00::/8"

die() { echo "cloudflare-egress: $*" >&2; exit 1; }

need_root() { [[ $(id -u) -eq 0 ]] || die "run as root (sudo $0 $*)"; }

# fill one address family: $1 = iptables|ip6tables, $2 = private ranges
fill() {
  local ipt=$1 ranges=$2 cidr
  # (re)create our chains empty
  $ipt -N "$FWD" 2>/dev/null || $ipt -F "$FWD"
  $ipt -N "$INP" 2>/dev/null || $ipt -F "$INP"

  # forwarded traffic: replies, DNS, no private ranges, then 7844/443 only
  $ipt -A "$FWD" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
  $ipt -A "$FWD" -p udp --dport 53 -j RETURN
  $ipt -A "$FWD" -p tcp --dport 53 -j RETURN
  for cidr in $ranges; do
    $ipt -A "$FWD" -d "$cidr" -m limit --limit 6/min -j LOG --log-prefix "ctf-edge-drop " || true
    $ipt -A "$FWD" -d "$cidr" -j REJECT
  done
  $ipt -A "$FWD" -p tcp --dport 7844 -j RETURN
  $ipt -A "$FWD" -p udp --dport 7844 -j RETURN
  $ipt -A "$FWD" -p tcp --dport 443 -j RETURN
  $ipt -A "$FWD" -m limit --limit 6/min -j LOG --log-prefix "ctf-edge-drop " || true
  $ipt -A "$FWD" -j REJECT

  # to the Pi itself: only replies to connections the Pi opened
  $ipt -A "$INP" -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  $ipt -A "$INP" -m limit --limit 6/min -j LOG --log-prefix "ctf-edge-drop " || true
  $ipt -A "$INP" -j REJECT

  # hook them in, once, at the top
  $ipt -C DOCKER-USER -i "$IFACE" -j "$FWD" 2>/dev/null || $ipt -I DOCKER-USER 1 -i "$IFACE" -j "$FWD"
  $ipt -C INPUT -i "$IFACE" -j "$INP" 2>/dev/null || $ipt -I INPUT 1 -i "$IFACE" -j "$INP"
}

unhook() {
  local ipt=$1
  while $ipt -C DOCKER-USER -i "$IFACE" -j "$FWD" 2>/dev/null; do $ipt -D DOCKER-USER -i "$IFACE" -j "$FWD"; done
  while $ipt -C INPUT -i "$IFACE" -j "$INP" 2>/dev/null; do $ipt -D INPUT -i "$IFACE" -j "$INP"; done
  for c in "$FWD" "$INP"; do
    $ipt -F "$c" 2>/dev/null || true
    $ipt -X "$c" 2>/dev/null || true
  done
}

has_v6() { command -v ip6tables >/dev/null && ip6tables -S DOCKER-USER >/dev/null 2>&1; }

cmd=${1:-}
case "$cmd" in
  apply)
    need_root apply
    command -v iptables >/dev/null || die "iptables not found"
    iptables -S DOCKER-USER >/dev/null 2>&1 \
      || die "no DOCKER-USER chain: start Docker first (needs Docker's iptables firewall backend)"
    [[ -e /sys/class/net/$IFACE ]] \
      || echo "cloudflare-egress: note: interface $IFACE not up yet (overlay not running?); rules installed anyway, they match it by name."
    fill iptables "$PRIVATE4"
    if has_v6; then fill ip6tables "$PRIVATE6"; fi
    echo "cloudflare-egress: $IFACE may only reach DNS, tcp/udp 7844 and tcp 443 on public addresses."
    ;;
  remove)
    need_root remove
    unhook iptables
    if has_v6; then unhook ip6tables; fi
    echo "cloudflare-egress: rules removed."
    ;;
  status)
    need_root status
    for ipt in iptables ip6tables; do
      [[ $ipt == ip6tables ]] && ! has_v6 && continue
      echo "== $ipt"
      $ipt -S DOCKER-USER 2>/dev/null | grep -- "-i $IFACE" || echo "   (not hooked into DOCKER-USER)"
      $ipt -S INPUT 2>/dev/null | grep -- "-i $IFACE" || echo "   (not hooked into INPUT)"
      $ipt -L "$FWD" -v -n 2>/dev/null || true
      $ipt -L "$INP" -v -n 2>/dev/null || true
    done
    ;;
  *)
    echo "usage: sudo $0 apply|status|remove" >&2
    exit 2
    ;;
esac
