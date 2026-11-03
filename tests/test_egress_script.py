"""scripts/cloudflare-egress.sh: the optional firewall for the tunnel's bridge.

Static checks only: the rules themselves need root + Docker's iptables and are
exercised by hand (see CLOUDFLARE.md, step 4b)."""
import pathlib
import re
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cloudflare-egress.sh"
TEXT = SCRIPT.read_text()


def test_script_parses():
    if not shutil.which("bash"):
        pytest.skip("bash not installed")
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_matches_the_overlay_bridge_name():
    overlay = (ROOT / "docker-compose.cloudflare.yml").read_text()
    assert 'IFACE="ctf-edge"' in TEXT
    assert "com.docker.network.bridge.name: ctf-edge" in overlay


def test_allows_only_dns_7844_443():
    returns = re.findall(r"-p (tcp|udp) --dport (\d+) -j RETURN", TEXT)
    assert sorted(returns) == sorted([("udp", "53"), ("tcp", "53"), ("tcp", "7844"),
                                      ("udp", "7844"), ("tcp", "443")])
    assert '$ipt -A "$FWD" -j REJECT' in TEXT                     # default: reject the rest
    assert '$ipt -A "$INP" -j REJECT' in TEXT                     # nothing to the Pi itself


def test_rejects_private_and_metadata_ranges_before_the_allowlist():
    v4 = re.search(r'^PRIVATE4="([^"]+)"', TEXT, re.M).group(1).split()
    for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16"):
        assert cidr in v4, cidr
    v6 = re.search(r'^PRIVATE6="([^"]+)"', TEXT, re.M).group(1).split()
    assert "fc00::/7" in v6 and "fe80::/10" in v6
    fill = TEXT.split("fill() {", 1)[1].split("\n}\n", 1)[0]
    assert fill.index('-d "$cidr" -j REJECT') < fill.index("--dport 7844")   # LAN blocked even on 7844


def test_commands_and_idempotent_hooks():
    for cmd in ("apply)", "remove)", "status)"):
        assert cmd in TEXT
    # hooks are checked (-C) before insertion, so apply can be re-run safely
    assert '-C DOCKER-USER -i "$IFACE" -j "$FWD"' in TEXT
    assert '-C INPUT -i "$IFACE" -j "$INP"' in TEXT
