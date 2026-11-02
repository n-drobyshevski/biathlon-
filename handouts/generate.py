#!/usr/bin/env python3
"""
Generates all DÉCAFLOP forensics / stego / SAP handout files from the flags in
the environment (.env). Output -> /out (mounted) or ./dist locally.

Nothing here is committed with real flags; files are built on the Pi.

Challenges produced:
  02 stego   -> decaflop_poster.png     (PNG with an appended ZIP)
  03 exif    -> range_shot.jpg          (flag + GPS + timestamp in EXIF)
  05 pcap    -> timing_booth.pcap       (HTTP Basic-Auth creds = flag)
  07 usb     -> referee_usb.img         (carve a deleted PNG that holds the flag)
  09 sap     -> SAP_USR02_export.csv, sap_hint.txt, wordlist.txt, case_file.zip
               (crack the operator's legacy hash -> password opens the zip)
"""
import io, os, sys, zipfile, struct, socket, hashlib, base64, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
import piexif

OUT = "/out" if os.path.isdir("/out") else os.path.join(os.path.dirname(__file__), "dist")
os.makedirs(OUT, exist_ok=True)

def flag(name, default):
    return os.environ.get(name, default)

FONT = ImageFont.load_default()

def text_png_bytes(lines, w=920, h=150, bg=(255,255,255), fg=(0,0,0)):
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    y = 16
    for ln in lines:
        d.text((16, y), ln, fill=fg, font=FONT)
        y += 22
    buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()

# ---------------------------------------------------------------------------
# 02 · STEGO (easy) — PNG poster with an appended ZIP (polyglot)
# ---------------------------------------------------------------------------
def gen_stego():
    f = flag("FLAG_02_STEGO", "BIATHLON{stego_placeholder}")
    img = Image.new("RGB", (800, 1000), (11, 61, 46))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 800, 120], fill=(7, 41, 31))
    d.text((40, 48), "DECAFLOP  x  REGIONAL BIATHLON CHAMPIONSHIP", fill=(234,255,245), font=FONT)
    d.text((40, 300), "THE FINAL RACE", fill=(25,195,125), font=FONT)
    d.text((40, 340), "Sport pour (presque) tous.", fill=(143,233,196), font=FONT)
    d.text((40, 900), "Official promo poster — share everywhere!", fill=(95,174,143), font=FONT)
    png = io.BytesIO(); img.save(png, "PNG"); png = png.getvalue()

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("flag.txt", f + "\n\nNice. The poster was hiding a zip at the end.\n")
    with open(os.path.join(OUT, "decaflop_poster.png"), "wb") as fh:
        fh.write(png + zbuf.getvalue())          # PNG renders; unzip finds the trailer
    print("[02] decaflop_poster.png")

# ---------------------------------------------------------------------------
# 03 · EXIF (easy) — flag + GPS + timestamp in metadata
# ---------------------------------------------------------------------------
def gen_exif():
    f = flag("FLAG_03_EXIF", "BIATHLON{exif_placeholder}")
    img = Image.new("RGB", (640, 426), (120, 140, 160))
    d = ImageDraw.Draw(img)
    d.text((20, 200), "shooting range — athletes on the mat", fill=(20,20,20), font=FONT)

    # Ostersund biathlon arena, Sweden: 63.1792 N, 14.6357 E
    def deg(dd):
        dd = abs(dd); dmin, sec = int(dd), (dd-int(dd))*60
        mm, ss = int(sec), (sec-int(sec))*60
        return ((dmin,1),(mm,1),(int(ss*100),100))
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: deg(63.1792),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: deg(14.6357),
    }
    zeroth = {
        piexif.ImageIFD.Make: b"DecaFlopCam",
        piexif.ImageIFD.Model: b"DFL-RangeCam 200",
        piexif.ImageIFD.ImageDescription: f.encode(),       # <-- the flag
        piexif.ImageIFD.Artist: b"crew:v.lindqvist",        # story clue
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2026:11:01 18:42:11",  # sabotage window
        piexif.ExifIFD.UserComment: b"ASCII\x00\x00\x00range photo, final-race eve",
    }
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif_ifd, "GPS": gps})
    img.save(os.path.join(OUT, "range_shot.jpg"), exif=exif_bytes, quality=85)
    print("[03] range_shot.jpg")

# ---------------------------------------------------------------------------
# 05 · PCAP (medium) — HTTP Basic-Auth over plain HTTP; creds hold the flag
# ---------------------------------------------------------------------------
def _csum(data):
    if len(data) % 2: data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data)//2), data))
    s = (s >> 16) + (s & 0xffff); s += (s >> 16)
    return (~s) & 0xffff

def _ipv4(src, dst, proto, payload):
    ver_ihl = 0x45; tot = 20 + len(payload)
    hdr = struct.pack("!BBHHHBBH4s4s", ver_ihl, 0, tot, 0x1c46, 0x4000, 64,
                      proto, 0, socket.inet_aton(src), socket.inet_aton(dst))
    chk = _csum(hdr)
    hdr = hdr[:10] + struct.pack("!H", chk) + hdr[12:]
    return hdr + payload

def _tcp(sport, dport, seq, ack, flags, src, dst, payload):
    off = (5 << 4)
    hdr = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, off, flags, 64240, 0, 0)
    pseudo = socket.inet_aton(src) + socket.inet_aton(dst) + struct.pack("!BBH", 0, 6, len(hdr)+len(payload))
    chk = _csum(pseudo + hdr + payload)
    hdr = hdr[:16] + struct.pack("!H", chk) + hdr[18:]
    return hdr + payload

def _eth(payload):
    return struct.pack("!6s6sH", b"\x02\x00\x00\x00\x00\x02",
                       b"\x02\x00\x00\x00\x00\x01", 0x0800) + payload

def _frame(src, dst, sport, dport, seq, ack, flags, http):
    return _eth(_ipv4(src, dst, 6, _tcp(sport, dport, seq, ack, flags, src, dst, http)))

def gen_pcap():
    f = flag("FLAG_05_PCAP", "BIATHLON{pcap_placeholder}")
    creds = base64.b64encode(("timingop:" + f).encode()).decode()
    req = ("GET /timing/submit?bib=1042 HTTP/1.1\r\n"
           "Host: timing.decaflop.local\r\n"
           f"Authorization: Basic {creds}\r\n"
           "User-Agent: DFlop-TimingBooth/1.2\r\n"
           "Connection: close\r\n\r\n").encode()
    resp = ("HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n"
            "OK split recorded. (Crew: STOP using HTTP Basic over the open booth Wi-Fi!)\r\n").encode()
    c, s = "10.13.37.42", "10.13.37.10"
    p1 = _frame(c, s, 49231, 80, 1000, 5000, 0x18, req)   # PSH,ACK
    p2 = _frame(s, c, 80, 49231, 5000, 1000+len(req), 0x18, resp)
    with open(os.path.join(OUT, "timing_booth.pcap"), "wb") as fh:
        fh.write(struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1))  # global hdr (big-endian magic)
        for ts, pkt in ((1762022400, p1), (1762022401, p2)):
            fh.write(struct.pack("!IIII", ts, 0, len(pkt), len(pkt)) + pkt)
    print("[05] timing_booth.pcap")

# ---------------------------------------------------------------------------
# 07 · USB carving (medium) — a 'deleted' PNG (holding the flag) inside a raw image
# ---------------------------------------------------------------------------
def gen_usb():
    f = flag("FLAG_07_USB", "BIATHLON{usb_placeholder}")
    hidden_png = text_png_bytes(
        ["RECOVERED FILE  (was deleted from the referee USB)", "", f,
         "", "note: carved from unallocated space — nice work."],
        w=940, h=150, bg=(245,245,245))
    blob = bytearray()
    blob += b"DECAFLOP-REMOVABLE-MEDIA\x00FAT16\x00" + b"\x00" * 480
    blob += b"NOTE.TXT (deleted)\nref rotation sheet, do not sha" + b"\x00" * 300  # partially 'overwritten'
    blob += os.urandom(2048)
    blob += hidden_png                                    # <-- carve this PNG
    blob += os.urandom(4096)
    # pad to a round size
    blob += b"\x00" * ((1 << 20) - (len(blob) % (1 << 20)))
    with open(os.path.join(OUT, "referee_usb.img"), "wb") as fh:
        fh.write(blob)
    print("[07] referee_usb.img")

# ---------------------------------------------------------------------------
# 09 · SAP USR02 (HARD, finale) — identify + crack the saboteur's legacy hash
# ---------------------------------------------------------------------------
def gen_sap():
    f = flag("FLAG_09_SAP_USR02", "BIATHLON{sap_placeholder}")
    saboteur = flag("SABOTEUR_NAME", "viktor_lindqvist").replace("_", " ").title()
    # NOTE: real SAP CODVN B (BCODE, hashcat -m 7700) is fiddly to reproduce
    # reliably offline, so for a self-hosted event we model the *legacy
    # MD5-based* nature of CODVN B with a plain MD5 of the upper-cased password.
    # The organizer writeup is explicit about this simplification.
    def codvn_b(pw):   # simplified legacy hash
        return hashlib.md5(pw.upper().encode()).hexdigest().upper()

    operator_pw = "LANE7"            # the crackable password (also the zip password)
    rows = [
        # MANDT,BNAME,BCODE,CODVN,UFLAG,TRDAT,LTIME
        ("001", "RESULTS_ADMIN", codvn_b("ADMIN2019"), "B", "64", "20260715", "091500"),
        ("001", "VLINDQVIST",    codvn_b(operator_pw), "B", "00", "20261101", "184230"),
        ("001", "MSORENSEN",     codvn_b("WINTER"),    "B", "00", "20261028", "133010"),
        ("001", "JKOWALSKI",     codvn_b("SKI2020"),   "B", "00", "20261030", "171240"),
        ("000", "SAP*",          "",                    "A", "00", "20260101", "000000"),
    ]
    with open(os.path.join(OUT, "SAP_USR02_export.csv"), "w") as fh:
        fh.write("MANDT,BNAME,BCODE,CODVN,UFLAG,TRDAT,LTIME\n")
        for r in rows:
            fh.write(",".join(r) + "\n")

    with open(os.path.join(OUT, "sap_hint.txt"), "w") as fh:
        fh.write(
"""SAP DFlop ERP — export of table USR02 (user master / logon data).

Columns: MANDT=client, BNAME=user, BCODE=legacy password hash,
         CODVN=hash version, UFLAG=lock (64=locked), TRDAT=last logon date,
         LTIME=last logon time.

The authoritative results table ZRACE_RESULT was changed on 2026-11-01,
around 18:42. Find the user whose LAST LOGON matches that window, then prove
it by recovering their password.

CODVN 'B' (BCODE) is the old, weak, MD5-based SAP hashing scheme. For this
exercise each BCODE is MD5(UPPERCASE(password)). Crack the suspect's hash
(a tiny wordlist.txt is provided; or use hashcat -m 0). The recovered password
is the passphrase for case_file.zip, which contains the final flag and names
the saboteur.

(For reference: real-world SAP CODVN B is hashcat mode 7700.)
""")

    with open(os.path.join(OUT, "wordlist.txt"), "w") as fh:
        fh.write("\n".join([
            "winter","summer","ski2020","admin2019","biathlon","results",
            "lane7","rifle","target","sweden","ostersund","password",
            "decaflop","timing","snow"]) + "\n")

    # password-protected zip with the finale flag + story
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "flag.txt")
        with open(fp, "w") as fh:
            fh.write(
f"""CASE CLOSED.

{f}

The last logon on table ZRACE_RESULT before the sabotage was user VLINDQVIST
(client 001), 2026-11-01 18:42 — the same timestamp as the range photo, the
same operator seen in the IDOR audit log and the results-admin accounts.

The saboteur is: {saboteur} (SAP user VLINDQVIST).
He swapped the shooting-lane assignments to rig the final race.
""")
        out_zip = os.path.join(OUT, "case_file.zip")
        if os.path.exists(out_zip): os.remove(out_zip)
        subprocess.run(["zip", "-j", "-P", operator_pw, out_zip, fp],
                       check=True, stdout=subprocess.DEVNULL)
    print("[09] SAP_USR02_export.csv, sap_hint.txt, wordlist.txt, case_file.zip")

if __name__ == "__main__":
    gen_stego(); gen_exif(); gen_pcap(); gen_usb(); gen_sap()
    print("\nAll handouts written to", OUT)
