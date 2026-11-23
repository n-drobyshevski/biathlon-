"""Every tool a hint, the guide, the hub's Outils tile or the terminal banner
names must really be installed in the team terminal (tools/toolbox/Dockerfile),
and selftest.sh must check it. Static: no Docker needed.

This is what went wrong before: hint 2 of 10 named jwt_tool (not installed) and
Debian's core john could not crack 09 or 10 although the hub advertised it.
"""
import re

from conftest import ROOT

TOOLBOX = ROOT / "tools" / "toolbox"
DOCKERFILE = (TOOLBOX / "Dockerfile").read_text()

# Commands each apt / pip package puts on PATH (only the ones we rely on).
APT_PROVIDES = {
    "git": ["git"], "curl": ["curl"], "wget": ["wget"], "python3": ["python3"],
    "file": ["file"], "binwalk": ["binwalk"], "foremost": ["foremost"],
    "sleuthkit": ["fls", "icat", "mmls"], "pngcheck": ["pngcheck"],
    "libimage-exiftool-perl": ["exiftool"], "hashcat": ["hashcat"],
    "tshark": ["tshark"], "binutils": ["strings"], "unzip": ["unzip"],
    "xxd": ["xxd"], "jq": ["jq"],
}
PIP_PROVIDES = {"git-dumper": ["git-dumper"]}

# Well-known CLI tools: a one-word <code> snippet naming one of these is a tool
# reference too (other one-word snippets are file names, fields, etc.).
KNOWN_TOOLS = {
    "binwalk", "foremost", "exiftool", "pngcheck", "fls", "icat", "file", "strings",
    "john", "hashcat", "jwt_tool", "zip2john", "git-dumper", "tshark", "wireshark",
    "sqlmap", "steghide", "stegseek", "zsteg", "volatility", "xortool", "unzip",
}
# Shell built-ins and words that start a snippet without being a program.
NOT_PROGRAMS = {"echo", "cd", "export", "authorization:", "{{", "'", "`'"}


def _apt_block():
    m = re.search(r"apt-get install -y --no-install-recommends(.*?)&& rm -rf",
                  DOCKERFILE.split("FROM debian:bookworm-slim\n", 1)[1], re.S)
    return set(m.group(1).replace("\\", " ").split())


def installed():
    apt = _apt_block()
    cmds = set()
    for pkg, provided in APT_PROVIDES.items():
        if pkg in apt:
            cmds.update(provided)
    for pkg, provided in PIP_PROVIDES.items():
        if re.search(rf"pip3 install[^\n]*(\\\n[^\n]*)*\b{re.escape(pkg)}\b", DOCKERFILE):
            cmds.update(provided)
    # commands placed on PATH by hand (symlinks, wrappers, COPY)
    cmds.update(re.findall(r"/usr/local/bin/([A-Za-z0-9_-]+)", DOCKERFILE))
    for loop in re.findall(r"for t in ([^;]+); do ln -s", DOCKERFILE):
        cmds.update(loop.split())
    return cmds


def test_dockerfile_installs_what_the_map_expects():
    apt = _apt_block()
    for pkg in APT_PROVIDES:
        assert pkg in apt, f"{pkg} missing from the toolbox apt install"
    # john must be the jumbo build (Debian's core john has no Raw-MD5/HMAC-SHA256)
    assert " john " not in f" {' '.join(apt)} ", "use john jumbo, not Debian's core john"
    assert "openwall/john" in DOCKERFILE and "COPY --from=john" in DOCKERFILE


def _hint_snippets():
    for readme in sorted((ROOT / "challenges").glob("*/README.md")):
        for code in re.findall(r"<code>(.*?)</code>", readme.read_text()):
            yield readme.parent.name, code
    hub = (ROOT / "hub" / "app" / "app.py").read_text()
    guide = hub[hub.index("GUIDE = {"):]
    for code in re.findall(r"`([^`]+)`", guide):
        yield "hub GUIDE", code


def test_every_tool_named_in_hints_and_guide_is_installed():
    have = installed()
    missing = []
    for where, code in _hint_snippets():
        first = code.strip().split()[0] if code.strip() else ""
        if " " in code.strip():
            # programs are lower case; "Extract Files" etc. are CyberChef operations
            if first.lower() in NOT_PROGRAMS or not re.match(r"^[a-z][a-z0-9_.-]*$", first):
                continue
            if first not in have:
                missing.append((where, code))
        elif first in KNOWN_TOOLS and first not in have:
            missing.append((where, code))
    assert not missing, f"named but not installed in the toolbox: {missing}"


def test_hub_chips_are_installed(hub_module):
    have = installed()
    chip_cmd = {"sleuth kit": "fls"}
    term = next(t for t in hub_module.tools() if t["icon"] == "term")
    for chip in term["chips"]:
        cmd = chip_cmd.get(chip.lower(), chip.split()[0].lower())
        assert cmd in have, chip


def test_banner_lists_only_installed_tools():
    have = installed()
    banner = (TOOLBOX / "shell.sh").read_text().split("BANNER", 2)[1]
    block = banner.split("Outils installés", 1)[1].split("\n\n", 1)[0]
    words = re.findall(r"[A-Za-z0-9_-]+", block)
    not_cmds = {"jumbo"}
    alias = {"sleuthkit": "fls"}
    for w in words:
        if w in not_cmds:
            continue
        assert alias.get(w, w) in have, w


def test_selftest_checks_every_installed_command():
    selftest = (TOOLBOX / "selftest.sh").read_text()
    checked = set(re.search(r"for t in (.*?); do", selftest, re.S).group(1).replace("\\", " ").split())
    expected = installed() - {"ttyd", "player-shell", "selftest", "rar2john"}
    assert expected <= checked, sorted(expected - checked)
    # and the modes the hints rely on
    for needle in ("Raw-MD5", "HMAC-SHA256", "16500", "jwt_tool"):
        assert needle in selftest, needle
