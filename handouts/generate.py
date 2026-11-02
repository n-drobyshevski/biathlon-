#!/usr/bin/env python3
"""
Generates all DÉCAFLOP forensics / stego / SAP handout files from the flags in
the environment (.env). Output -> /out (mounted) or ./dist locally.

Nothing here is committed with real flags; files are built on the Pi.

Challenges produced:
  02 stego   -> decaflop_poster.png     (PNG with an appended ZIP)
  03 exif    -> transition_shot.jpg     (flag + GPS + timestamp in EXIF)
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

# Poster fonts: DejaVu from the toolbox image (fonts-dejavu-core); falls back
# to Pillow's built-in scalable font, then to the tiny bitmap one.
_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf"

def _has_dejavu():
    try:
        ImageFont.truetype(_DEJAVU.format("-Bold"), 10)
        return True
    except OSError:
        return False

HAS_DEJAVU = _has_dejavu()

def plain(text):
    """Pillow's fallback font has no accents, × or em dash: fold them to ASCII."""
    if HAS_DEJAVU:
        return text
    import unicodedata
    text = text.replace("×", "x").replace("—", "-").replace("·", "-")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()

def text(d, xy, s, **kw):
    d.text(xy, plain(s), **kw)

def font(size, bold=False):
    try:
        return ImageFont.truetype(_DEJAVU.format("-Bold" if bold else ""), size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return FONT

def slanted(img, xy, text, fnt, fill, shear=0.2):
    """Draw text with a forward slant (the site's heavy-italic look); return the x after it."""
    text = plain(text)
    l, t, r, b = fnt.getbbox(text)
    w, h = r + int(shear * b) + 4, b + 4
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).text((int(shear * b), 0), text, font=fnt, fill=255)
    layer = layer.transform((w, h), Image.AFFINE, (1, shear, 0, 0, 1, 0), resample=Image.BICUBIC)
    img.paste(Image.new("RGB", (w, h), fill), (xy[0], xy[1]), layer)
    return xy[0] + int(fnt.getlength(text))

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
    f = flag("FLAG_02_STEGO", "TRIATHLON{stego_placeholder}")
    W, H = 800, 1000
    BLUE, DARK, MINT, INK, WHITE = (54, 67, 186), (38, 47, 138), (122, 255, 166), (16, 16, 16), (255, 255, 255)
    img = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(img)

    # top band: wordmark + event
    d.rectangle([0, 0, W, 112], fill=INK)
    x = slanted(img, (48, 30), "DÉCA", font(56, bold=True), (124, 134, 255))
    slanted(img, (x, 30), "FLOP", font(56, bold=True), WHITE)
    text(d, (W - 48, 42), "×  CHAMPIONNAT RÉGIONAL", font=font(18, bold=True), fill=WHITE, anchor="ra")
    text(d, (W - 48, 66), "DE TRIATHLON 2026", font=font(18, bold=True), fill=MINT, anchor="ra")

    # headline
    tag, tf = plain("2 NOVEMBRE · LA PLAGE"), font(20, bold=True)
    d.rectangle([48, 168, 48 + int(tf.getlength(tag)) + 24, 206], fill=MINT)
    text(d, (60, 175), tag, font=tf, fill=INK)
    size = 118                                   # largest size where the widest line fits
    while font(size, bold=True).getlength("C'EST DEMAIN") * 1.04 > W - 96 and size > 40:
        size -= 2
    hf, lead = font(size, bold=True), int(size * 1.12)
    block = 2 * lead + 26 + 30                   # two headline lines + gap + subtitle
    top = 206 + (586 - 206 - block) // 2         # centred between the date tag and the cards
    slanted(img, (44, top), "LA FINALE,", hf, WHITE)
    x = slanted(img, (44, top + lead), "C'EST ", hf, WHITE)
    slanted(img, (x, top + lead), "DEMAIN", hf, MINT)
    text(d, (50, top + 2 * lead + 26), "Nage. Vélo. Course. Venez encourager les finalistes !",
           font=font(25), fill=WHITE)

    # three legs: swim / bike / run, each in a card
    cards = [(48, "1,5 km", "NAGE"), (290, "40 km", "VÉLO"), (532, "10 km", "COURSE")]
    for cx, dist, label in cards:
        d.rectangle([cx, 586, cx + 220, 836], fill=DARK)
        d.rectangle([cx, 586, cx + 220, 594], fill=MINT)
        text(d, (cx + 110, 768), dist, font=font(34, bold=True), fill=MINT, anchor="ma")
        text(d, (cx + 110, 806), label, font=font(20, bold=True), fill=WHITE, anchor="ma")
    import math                                              # swim: three smooth waves
    for i in range(3):
        y0 = 654 + i * 28
        pts = [(x, y0 + 8 * math.sin((x - 78) / 72 * 2 * math.pi)) for x in range(78, 239, 4)]
        d.line(pts, fill=MINT, width=6, joint="curve")
    bx = 290 + 110                                           # bike
    rear, front, bb, seat, head = (bx - 58, 712), (bx + 58, 712), (bx - 6, 712), (bx - 18, 664), (bx + 38, 666)
    for wx, wy in (rear, front):
        d.ellipse([wx - 32, wy - 32, wx + 32, wy + 32], outline=MINT, width=6)
    for p1, p2 in ((rear, seat), (seat, bb), (bb, rear), (seat, head), (head, bb), (head, front)):
        d.line([p1, p2], fill=MINT, width=6)
    d.line([(bx - 30, 657), (bx - 6, 657)], fill=MINT, width=7)
    d.line([(head[0], head[1]), (head[0] + 4, 648), (head[0] + 20, 648)], fill=MINT, width=6)
    rx = 532 + 110                                           # run: runner mid-stride
    d.ellipse([rx - 6, 630, rx + 20, 656], outline=MINT, width=6)
    d.line([(rx + 4, 660), (rx - 8, 704)], fill=MINT, width=7)
    d.line([(rx - 8, 704), (rx - 34, 740)], fill=MINT, width=7)
    d.line([(rx - 8, 704), (rx + 22, 734)], fill=MINT, width=7)
    d.line([(rx + 22, 734), (rx + 36, 728)], fill=MINT, width=7)
    d.line([(rx + 1, 674), (rx - 26, 690)], fill=MINT, width=7)
    d.line([(rx + 1, 674), (rx + 30, 686)], fill=MINT, width=7)

    # footer band
    d.rectangle([0, 884, W, H], fill=MINT)
    text(d, (48, 908), "Affiche officielle — partagez-la partout !", font=font(26, bold=True), fill=INK)
    text(d, (48, 950), "#DecaFlopTri  ·  sport pour (presque) tous", font=font(20), fill=INK)
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
    f = flag("FLAG_03_EXIF", "TRIATHLON{exif_placeholder}")
    img = Image.new("RGB", (640, 426), (120, 140, 160))
    d = ImageDraw.Draw(img)
    for x in range(40, 600, 70):                       # bike racks
        d.line([(x, 260), (x + 50, 260)], fill=(60, 60, 60), width=4)
        d.ellipse([x, 262, x + 22, 284], outline=(30, 30, 30), width=3)
        d.ellipse([x + 30, 262, x + 52, 284], outline=(30, 30, 30), width=3)
    d.text((20, 200), "transition zone - bikes on the racks", fill=(20,20,20), font=FONT)

    # Kalmar triathlon transition area, Sweden: 56.6634 N, 16.3568 E
    def deg(dd):
        dd = abs(dd); dmin, sec = int(dd), (dd-int(dd))*60
        mm, ss = int(sec), (sec-int(sec))*60
        return ((dmin,1),(mm,1),(int(ss*100),100))
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: deg(56.6634),
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: deg(16.3568),
    }
    zeroth = {
        piexif.ImageIFD.Make: b"DecaFlopCam",
        piexif.ImageIFD.Model: b"DFL-T2Cam 200",
        piexif.ImageIFD.ImageDescription: f.encode(),       # <-- the flag
        piexif.ImageIFD.Artist: b"crew:v.lindqvist",        # story clue
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2026:11:01 18:42:11",  # sabotage window
        piexif.ExifIFD.UserComment: b"ASCII\x00\x00\x00transition zone photo, final-race eve",
    }
    exif_bytes = piexif.dump({"0th": zeroth, "Exif": exif_ifd, "GPS": gps})
    img.save(os.path.join(OUT, "transition_shot.jpg"), exif=exif_bytes, quality=85)
    print("[03] transition_shot.jpg")

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
    f = flag("FLAG_05_PCAP", "TRIATHLON{pcap_placeholder}")
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
    f = flag("FLAG_07_USB", "TRIATHLON{usb_placeholder}")
    hidden_png = text_png_bytes(
        ["RECOVERED FILE  (was deleted from the referee USB)", "", f,
         "", "note: carved from unallocated space - nice work."],
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
    f = flag("FLAG_09_SAP_USR02", "TRIATHLON{sap_placeholder}")
    saboteur = flag("SABOTEUR_NAME", "viktor_lindqvist").replace("_", " ").title()
    # NOTE: real SAP CODVN B (BCODE, hashcat -m 7700) is fiddly to reproduce
    # reliably offline, so for a self-hosted event we model the *legacy
    # MD5-based* nature of CODVN B with a plain MD5 of the upper-cased password.
    # The organizer writeup is explicit about this simplification.
    def codvn_b(pw):   # simplified legacy hash
        return hashlib.md5(pw.upper().encode()).hexdigest().upper()

    operator_pw = "CHIP7"            # the crackable password (also the zip password)
    rows = [
        # MANDT,BNAME,BCODE,CODVN,UFLAG,TRDAT,LTIME
        ("001", "RESULTS_ADMIN", codvn_b("ADMIN2019"), "B", "64", "20260715", "091500"),
        ("001", "VLINDQVIST",    codvn_b(operator_pw), "B", "00", "20261101", "184230"),
        ("001", "MSORENSEN",     codvn_b("SUMMER"),    "B", "00", "20261028", "133010"),
        ("001", "JKOWALSKI",     codvn_b("SWIM2020"),   "B", "00", "20261030", "171240"),
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
            "spring","summer","swim2020","admin2019","triathlon","results",
            "chip7","wetsuit","transition","sweden","kalmar","password",
            "decaflop","timing","aero"]) + "\n")

    # password-protected zip with the finale flag + story
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "flag.txt")
        with open(fp, "w") as fh:
            fh.write(
f"""CASE CLOSED.

{f}

The last logon on table ZRACE_RESULT before the sabotage was user VLINDQVIST
(client 001), 2026-11-01 18:42 — the same timestamp as the transition photo, the
same operator seen in the IDOR audit log and the results-admin accounts.

The saboteur is: {saboteur} (SAP user VLINDQVIST).
He swapped the timing-chip assignments to rig the final race.
""")
        out_zip = os.path.join(OUT, "case_file.zip")
        if os.path.exists(out_zip): os.remove(out_zip)
        subprocess.run(["zip", "-j", "-P", operator_pw, out_zip, fp],
                       check=True, stdout=subprocess.DEVNULL)
    print("[09] SAP_USR02_export.csv, sap_hint.txt, wordlist.txt, case_file.zip")

if __name__ == "__main__":
    gen_stego(); gen_exif(); gen_pcap(); gen_usb(); gen_sap()
    print("\nAll handouts written to", OUT)
