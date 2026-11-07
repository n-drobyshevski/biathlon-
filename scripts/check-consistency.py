#!/usr/bin/env python3
"""
check-consistency.py: do the missions and the War Room still tell the same story?

Builds the REAL handouts (challenges 03, 08, 09) into a temp dir with throwaway
flags, loads the REAL War Room and challenge 14 apps, and checks that the
evidence players will find is what the War Room accepts. Run it after changing
any answer, handout or env default:

    python3 scripts/check-consistency.py        # needs flask, pillow, piexif, zip

Prints PASS / WARN / FAIL per check; exit code 1 only if something FAILs. WARN
means "accepted by the War Room but found nowhere in the game": harmless, but a
sign that an accepted answer has no evidence behind it.
"""
import importlib.util
import os
import re
import struct
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_FLAGS = {"FLAG_03_EXIF": "TRIATHLON{check_exif}", "FLAG_08_PHANTOM": "TRIATHLON{check_phantom}",
              "FLAG_09_SAP_USR02": "TRIATHLON{check_usr02}", "SABOTEUR_NAME": "viktor_lindqvist",
              "FLAG_FINALE": "TRIATHLON{check_finale}", "FLAG_14": "TRIATHLON{check_gateway}"}
SAP_USER, SAP_PASS = "basis_dflop", "Trans1tion!2026"      # challenge 14 logon defaults


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def build_world():
    """Generate the handouts and load the apps under a clean, known environment."""
    for k in [k for k in os.environ if k.startswith(("ROGUE_", "WARROOM_"))]:
        del os.environ[k]
    os.environ.update(TEST_FLAGS)
    out = tempfile.mkdtemp(prefix="consistency-")
    gen = _load("cc_generate", os.path.join(ROOT, "handouts", "generate.py"))
    gen.OUT = out
    gen.gen_exif()
    gen.gen_phantom()
    gen.gen_sap()
    war = _load("cc_warroom", os.path.join(ROOT, "warroom", "app.py"))
    gw = _load("cc_gateway", os.path.join(ROOT, "challenges", "14-sap-gateway", "app", "app.py"))
    return {"out": out, "gen": gen, "war": war, "gw": gw}


# --------------------------------------------------------------------- helpers
def read_pcap(path):
    raw = open(path, "rb").read()
    frames, off = [], 24
    while off < len(raw):
        sec, usec, n, _ = struct.unpack("!IIII", raw[off:off + 16])
        frames.append(raw[off + 16:off + 16 + n])
        off += 16 + n
    return frames


def tcp_payload(frame):
    """(src_mac, src_ip, payload) of an Ethernet/IPv4/TCP frame, else None."""
    if frame[12:14] != b"\x08\x00" or frame[23] != 6:
        return None
    ihl = (frame[14] & 0x0F) * 4
    tcp = 14 + ihl
    data = frame[tcp + ((frame[tcp + 12] >> 4) * 4):]
    mac = ":".join(f"{b:02x}" for b in frame[6:12])
    ip = ".".join(str(b) for b in frame[26:30])
    return mac, ip, data


def gateway_text(gw):
    """Everything a player can read in challenge 14, plus the raw reginfo file."""
    c = gw.app.test_client()
    c.post("/sap/logon", data={"user": SAP_USER, "pass": SAP_PASS})
    pages = [c.get(p).data.decode() for p in ("/sap/menu", "/sap/smgw", "/sap/se16n?table=USR02", "/sap/sm37")]
    pages.append(c.post("/sap/gw/register", data={"tp": "Z_X", "host": "10.0.0.1"}).data.decode())
    pages.append(c.get("/sap/gw/reginfo").data.decode())
    return re.sub(r"<[^>]+>", " ", " ".join(pages)).casefold()


# ---------------------------------------------------------------------- checks
# each returns (status, detail) with status PASS / WARN / FAIL
def check_rogue_device(w):
    war, gen = w["war"], w["gen"]
    if (war.ROGUE_MAC, war.ROGUE_IP) != (gen.ROGUE_MAC, gen.ROGUE_IP):
        return "FAIL", f"generate.py has {gen.ROGUE_MAC}/{gen.ROGUE_IP}, War Room has {war.ROGUE_MAC}/{war.ROGUE_IP}"
    posts = [tcp_payload(f) for f in read_pcap(os.path.join(w["out"], "phantom_signal.pcap"))]
    posts = [p for p in posts if p and p[2].startswith(b"POST /sap/gw/register")]
    if len(posts) != 1:
        return "FAIL", f"expected one POST in the capture, found {len(posts)}"
    mac, ip, _ = posts[0]
    if not (war.check_device(mac) and war.check_device(ip)):
        return "FAIL", f"the capture's sender {mac} / {ip} is not accepted by the War Room"
    return "PASS", f"capture sender {mac} / {ip} == generate.py == War Room field (d)"


def check_exif_time(w):
    import piexif
    exif = piexif.load(os.path.join(w["out"], "transition_shot.jpg"))
    stamp = exif["Exif"][piexif.ExifIFD.DateTimeOriginal].decode()          # 2026:11:01 18:42:11
    war = w["war"]
    if not (war.check_time(stamp) and war.check_time(stamp.split()[1])):
        return "FAIL", f"EXIF time {stamp!r} is not accepted by War Room field (c)"
    if not war.check_time(war.INCIDENT_TIME):
        return "FAIL", "the War Room does not accept its own incident time"
    return "PASS", f"EXIF {stamp} accepted by field (c) (minute {war.INCIDENT_TIME} on {war.INCIDENT_DATE})"


def check_saboteur(w):
    import csv
    war = w["war"]
    rows = list(csv.DictReader(open(os.path.join(w["out"], "SAP_USR02_export.csv"))))
    window = [r["BNAME"] for r in rows if r["TRDAT"] == "20261101" and r["LTIME"].startswith("1842")]
    if len(window) != 1:
        return "FAIL", f"USR02 should have exactly one last logon in the 18:42 window, found {window}"
    zf = zipfile.ZipFile(os.path.join(w["out"], "case_file.zip"))
    story = zf.read("flag.txt", pwd=b"CHIP7").decode()
    name = TEST_FLAGS["SABOTEUR_NAME"].replace("_", " ").title()
    for label, value in (("USR02 user", window[0]), ("case_file name", name)):
        if not war.check_saboteur(value):
            return "FAIL", f"{label} {value!r} is not accepted by War Room field (a)"
    if window[0] not in story or name not in story:
        return "FAIL", "case_file.zip does not name the same saboteur as USR02"
    return "PASS", f"USR02 {window[0]} and case_file '{name}' both accepted by field (a)"


def check_gateway_theme(w):
    text, war = gateway_text(w["gw"]), w["war"]
    def shown(answer):          # whole word(s) only: "odata" must not match inside "horodatages"
        return re.search(r"(?<!\w)" + re.escape(answer.casefold()) + r"(?!\w)", text) is not None
    grounded = [a for a in war.VECTOR_ANSWERS if shown(a)]
    loose = [a for a in war.VECTOR_ANSWERS if a not in grounded]
    core = ("reginfo", "Passerelle SAP", "USR02", "RFC")
    missing = [a for a in core if a not in grounded]
    if missing:
        return "FAIL", f"challenge 14 never mentions accepted answer(s) {missing}"
    if loose:
        return "WARN", f"{grounded} appear in challenge 14; accepted but never shown in the game: {loose}"
    return "PASS", f"every accepted vector appears in challenge 14: {grounded}"


def check_flag_in_pcap(w):
    flag = TEST_FLAGS["FLAG_08_PHANTOM"].encode()
    hits = [(i, tcp_payload(f)) for i, f in enumerate(read_pcap(os.path.join(w["out"], "phantom_signal.pcap")))
            if flag in f]
    if len(hits) != 1:
        return "FAIL", f"FLAG_08 should be in exactly one packet, found {len(hits)}"
    mac, ip, data = hits[0][1]
    if not data.startswith(b"HTTP/1.1 200 OK") or flag not in data:
        return "FAIL", "FLAG_08 is not in the payload of the gateway's 200 OK"
    return "PASS", f"FLAG_08 is in the HTTP 200 body sent by {ip} (frame {hits[0][0]})"


def check_finale_gating(w):
    import itertools
    war = w["war"]
    flag = TEST_FLAGS["FLAG_FINALE"]
    right = {"saboteur": "VLINDQVIST", "vector": "Passerelle SAP", "time": "2026-11-01 18:42",
             "device": "aa:bb:cc:dd:ee:42"}
    c, n = war.app.test_client(), iter(range(1, 10**6))

    def submit(**over):
        ip = f"10.9.{next(n) // 250}.{next(n) % 250 + 1}"
        return c.post("/submit", data={**right, **over}, environ_overrides={"REMOTE_ADDR": ip}).data.decode()
    if flag in c.get("/").data.decode():
        return "FAIL", "the flag is on the empty form"
    leaks = 0
    for k in range(len(right)):                              # every incomplete report
        for wrong in itertools.combinations(right, k + 1):
            leaks += flag in submit(**{f: "nope" for f in wrong})
    if leaks:
        return "FAIL", f"the flag leaked on {leaks} incomplete report(s)"
    if flag not in submit():
        return "FAIL", "a fully correct report does not reveal FLAG_FINALE"
    for _ in range(war.RATE_LIMIT):
        c.post("/submit", data=right, environ_overrides={"REMOTE_ADDR": "10.8.0.1"})
    if flag in c.post("/submit", data=right, environ_overrides={"REMOTE_ADDR": "10.8.0.1"}).data.decode():
        return "FAIL", "the flag was revealed to an IP that is over the rate limit"
    return "PASS", "15 incomplete reports and a rate-limited correct one reveal nothing; 4/4 reveals it"


CHECKS = [("08 rogue MAC/IP  == War Room field (d)", check_rogue_device),
          ("03 EXIF time     == War Room field (c)", check_exif_time),
          ("09 saboteur      == War Room field (a)", check_saboteur),
          ("14 gateway theme == War Room field (b)", check_gateway_theme),
          ("08 FLAG_08 is in phantom_signal.pcap  ", check_flag_in_pcap),
          ("FLAG_FINALE only on full success      ", check_finale_gating)]


def run():
    world = build_world()
    results = []
    for label, fn in CHECKS:
        try:
            status, detail = fn(world)
        except Exception as exc:                              # a crashing check is a failing check
            status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
        results.append((status, label, detail))
    return results


def main():
    results = run()
    for status, label, detail in results:
        print(f"{status:<5} {label}  {detail}")
    bad = sum(1 for s, *_ in results if s == "FAIL")
    warn = sum(1 for s, *_ in results if s == "WARN")
    print(f"\n{len(results) - bad - warn} PASS, {warn} WARN, {bad} FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
