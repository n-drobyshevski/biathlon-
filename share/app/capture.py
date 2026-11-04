"""
Network capture (.pcap) preview for the Intranet DécaFlop share.

A Wireshark-style packet list, and the layers of the packet the player clicks
(?p=N): frame, Ethernet / Linux cooked, IPv4 / IPv6, TCP / UDP / ICMP, and HTTP
requests and responses with their headers and the start of the body. There is
no hex dump. Pure Python (struct), no third-party library: a damaged or cut
capture shows what could be read, never an error page.

Supported: classic libpcap files (both byte orders, micro- or nanosecond
timestamps), link types Ethernet (1), raw IP (101, 228, 229) and Linux cooked
(113). pcapng gets a short "download it" note.
"""
import socket
import struct
import time
from html import escape as esc

MAX_PACKETS = 2000
BODY_CHARS = 4000
HTTP_METHODS = (b"GET ", b"POST ", b"PUT ", b"DELETE ", b"HEAD ", b"OPTIONS ", b"PATCH ", b"CONNECT ")
TCP_FLAGS = [(0x01, "FIN"), (0x02, "SYN"), (0x04, "RST"), (0x08, "PSH"), (0x10, "ACK"), (0x20, "URG"),
             (0x40, "ECE"), (0x80, "CWR")]
IP_PROTOS = {1: "ICMP", 2: "IGMP", 6: "TCP", 17: "UDP", 58: "ICMPv6"}
ETHERTYPES = {0x0800: "IPv4", 0x0806: "ARP", 0x86DD: "IPv6", 0x8100: "VLAN"}
LINKTYPES = {1: "Ethernet", 101: "IP brut", 113: "Linux cooked", 228: "IPv4 brut", 229: "IPv6 brut"}
MAGIC = {b"\xa1\xb2\xc3\xd4": (">", 1e-6), b"\xd4\xc3\xb2\xa1": ("<", 1e-6),
         b"\xa1\xb2\x3c\x4d": (">", 1e-9), b"\x4d\x3c\xb2\xa1": ("<", 1e-9)}


# ------------------------------------------------------------------ parsing
def mac(b):
    return ":".join(f"{x:02x}" for x in b)


def flags_text(fl):
    return ", ".join(name for bit, name in TCP_FLAGS if fl & bit) or "aucun"


def printable(b, limit):
    s = b[:limit].decode("utf-8", errors="replace")
    return "".join(c if c.isprintable() or c in "\n\t" else "." for c in s)


def parse_http(payload):
    """(summary, lines, body, body_len, content_type) or None."""
    if not (payload.startswith(HTTP_METHODS) or payload.startswith(b"HTTP/1.") or payload.startswith(b"HTTP/2")):
        return None
    head, sep, body = payload.partition(b"\r\n\r\n")
    if not sep:
        head, sep, body = payload.partition(b"\n\n")
    lines = head.decode("latin-1").replace("\r\n", "\n").split("\n")
    ctype = ""
    for ln in lines[1:]:
        k, _, v = ln.partition(":")
        if k.strip().lower() == "content-type":
            ctype = v.strip().split(";")[0]
    summary = lines[0] + (f" ({ctype})" if lines[0].startswith("HTTP/") and ctype else "")
    return summary, lines, body, len(body), ctype


def parse_transport(proto, seg, src, dst, pkt):
    """Fill the TCP / UDP / ICMP layer and the application layer of `pkt`."""
    if proto == 6 and len(seg) >= 20:
        sport, dport, seq, ack, off, fl, win = struct.unpack("!HHIIBBH", seg[:16])
        hlen = (off >> 4) * 4
        payload = seg[hlen:] if hlen >= 20 else b""
        pkt["proto"] = "TCP"
        pkt["info"] = f"{sport} → {dport} [{flags_text(fl)}] Seq={seq} Ack={ack} Win={win} Len={len(payload)}"
        pkt["layers"].append((f"Transmission Control Protocol, port source {sport}, port destination {dport}, "
                              f"Seq {seq}, Ack {ack}, Len {len(payload)}", [
                                  ("Port source", sport), ("Port destination", dport),
                                  ("Numéro de séquence", seq), ("Numéro d'acquittement", ack),
                                  ("Longueur de l'en-tête", f"{hlen} octets"), ("Drapeaux", f"0x{fl:02x} ({flags_text(fl)})"),
                                  ("Fenêtre", win), ("Données", f"{len(payload)} octets")]))
        app(payload, pkt)
    elif proto == 17 and len(seg) >= 8:
        sport, dport, ulen, _ck = struct.unpack("!HHHH", seg[:8])
        payload = seg[8:]
        pkt["proto"] = "UDP"
        pkt["info"] = f"{sport} → {dport} Len={len(payload)}"
        pkt["layers"].append((f"User Datagram Protocol, port source {sport}, port destination {dport}", [
            ("Port source", sport), ("Port destination", dport), ("Longueur", ulen), ("Données", f"{len(payload)} octets")]))
        if dport == 53 or sport == 53:
            pkt["proto"] = "DNS"
        app(payload, pkt, http=False)
    elif proto in (1, 58) and len(seg) >= 4:
        typ, code = seg[0], seg[1]
        names = {(1, 0): "Echo (ping) reply", (1, 8): "Echo (ping) request", (1, 3): "Destination unreachable",
                 (58, 128): "Echo (ping) request", (58, 129): "Echo (ping) reply"}
        pkt["proto"] = IP_PROTOS[proto]
        pkt["info"] = names.get((proto, typ), f"Type {typ}, code {code}")
        pkt["layers"].append((f"{'Internet Control Message Protocol' if proto == 1 else 'ICMPv6'}", [
            ("Type", typ), ("Code", code)]))
    else:
        pkt["proto"] = IP_PROTOS.get(proto, f"IP proto {proto}")
        pkt["info"] = f"{src} → {dst}"


def app(payload, pkt, http=True):
    if not payload:
        return
    h = parse_http(payload) if http else None
    if h:
        summary, lines, body, blen, ctype = h
        pkt["proto"] = "HTTP"
        pkt["info"] = summary
        pkt["http"] = {"lines": lines, "body": body, "blen": blen, "ctype": ctype}
    else:
        pkt["data"] = payload


def parse_ip(buf, pkt):
    if not buf:
        return
    ver = buf[0] >> 4
    if ver == 4 and len(buf) >= 20:
        ihl = (buf[0] & 15) * 4
        tos, tlen, ident, frag, ttl, proto, _ck = struct.unpack("!BHHHBBH", buf[1:12])
        src, dst = socket.inet_ntoa(buf[12:16]), socket.inet_ntoa(buf[16:20])
        pkt["src"], pkt["dst"] = src, dst
        pkt["layers"].append((f"Internet Protocol Version 4, source {src}, destination {dst}", [
            ("Version", 4), ("Longueur de l'en-tête", f"{ihl} octets"), ("Longueur totale", tlen),
            ("Identification", f"0x{ident:04x}"), ("Durée de vie (TTL)", ttl),
            ("Protocole", f"{IP_PROTOS.get(proto, proto)} ({proto})"), ("Source", src), ("Destination", dst)]))
        end = min(len(buf), tlen) if tlen >= ihl else len(buf)
        parse_transport(proto, buf[ihl:end], src, dst, pkt)
    elif ver == 6 and len(buf) >= 40:
        plen, nxt, hop = struct.unpack("!HBB", buf[4:8])
        src = socket.inet_ntop(socket.AF_INET6, buf[8:24])
        dst = socket.inet_ntop(socket.AF_INET6, buf[24:40])
        pkt["src"], pkt["dst"] = src, dst
        pkt["layers"].append((f"Internet Protocol Version 6, source {src}, destination {dst}", [
            ("Version", 6), ("Longueur des données", plen), ("En-tête suivant", f"{IP_PROTOS.get(nxt, nxt)} ({nxt})"),
            ("Limite de sauts", hop), ("Source", src), ("Destination", dst)]))
        parse_transport(nxt, buf[40:40 + plen], src, dst, pkt)


def parse_link(link, frame, pkt):
    if link == 1 and len(frame) >= 14:
        dst, src, etype = frame[:6], frame[6:12], struct.unpack("!H", frame[12:14])[0]
        off = 14
        if etype == 0x8100 and len(frame) >= 18:          # one VLAN tag
            etype, off = struct.unpack("!H", frame[16:18])[0], 18
        pkt["src"], pkt["dst"] = mac(src), mac(dst)
        pkt["layers"].append((f"Ethernet II, source {mac(src)}, destination {mac(dst)}", [
            ("Destination", mac(dst)), ("Source", mac(src)),
            ("Type", f"{ETHERTYPES.get(etype, 'inconnu')} (0x{etype:04x})")]))
        pkt["proto"] = ETHERTYPES.get(etype, f"0x{etype:04x}")
        if etype in (0x0800, 0x86DD):
            parse_ip(frame[off:], pkt)
        elif etype == 0x0806 and len(frame) >= off + 28:
            spa, tpa = socket.inet_ntoa(frame[off + 14:off + 18]), socket.inet_ntoa(frame[off + 24:off + 28])
            op = struct.unpack("!H", frame[off + 6:off + 8])[0]
            pkt["info"] = f"Qui a {tpa} ? Répondre à {spa}" if op == 1 else f"{spa} est à {mac(frame[off + 8:off + 14])}"
    elif link == 113 and len(frame) >= 16:
        etype = struct.unpack("!H", frame[14:16])[0]
        pkt["layers"].append(("Linux cooked capture", [("Protocole", f"{ETHERTYPES.get(etype, 'inconnu')} (0x{etype:04x})")]))
        parse_ip(frame[16:], pkt)
    elif link in (101, 228, 229):
        parse_ip(frame, pkt)


def parse(data):
    """{"error"} or {"link", "packets", "truncated", "ns"}."""
    if data[:4] == b"\x0a\x0d\x0d\x0a":
        return {"error": "pcapng"}
    if len(data) < 24 or data[:4] not in MAGIC:
        return {"error": "format"}
    end, unit = MAGIC[data[:4]]
    _vmaj, _vmin, _tz, _sig, _snap, link = struct.unpack(end + "HHiIII", data[4:24])
    packets, pos, t0, truncated = [], 24, None, False
    while pos + 16 <= len(data) and len(packets) < MAX_PACKETS:
        sec, frac, caplen, origlen = struct.unpack(end + "IIII", data[pos:pos + 16])
        pos += 16
        frame = data[pos:pos + caplen]
        if len(frame) < caplen:
            truncated = True
        pos += caplen
        ts = sec + frac * unit
        t0 = ts if t0 is None else t0
        pkt = {"n": len(packets) + 1, "ts": ts, "rel": ts - t0, "caplen": len(frame), "origlen": origlen,
               "src": "", "dst": "", "proto": LINKTYPES.get(link, str(link)), "info": "", "layers": []}
        try:
            parse_link(link, frame, pkt)
        except (struct.error, ValueError, OSError):
            pkt["info"] = pkt["info"] or "Paquet mal formé"
        packets.append(pkt)
        if truncated:
            break
    if pos < len(data) and not truncated and len(packets) >= MAX_PACKETS:
        truncated = True
    return {"link": link, "packets": packets, "truncated": truncated, "ns": unit < 1e-6}


# ------------------------------------------------------------------ rendering
def when(ts):
    return time.strftime("%d/%m/%Y %H:%M:%S", time.gmtime(ts)) + f".{int(ts % 1 * 1e6):06d} UTC"


def layer_html(title, fields):
    rows = "".join(f"<dt>{esc(str(k))}</dt><dd>{esc(str(v))}</dd>" for k, v in fields)
    return f'<details open><summary>{esc(title)}</summary><dl class="pc-kv">{rows}</dl></details>'


def detail_html(pkt):
    frame = layer_html(f"Trame {pkt['n']} : {pkt['caplen']} octets capturés ({pkt['origlen']} sur le réseau)", [
        ("Arrivée", when(pkt["ts"])), ("Temps depuis le début", f"{pkt['rel']:.6f} s"),
        ("Longueur capturée", f"{pkt['caplen']} octets"), ("Longueur sur le réseau", f"{pkt['origlen']} octets")])
    parts = [frame] + [layer_html(t, f) for t, f in pkt["layers"]]
    h = pkt.get("http")
    if h:
        lines = "".join(f"<li><code>{esc(ln)}</code></li>" for ln in h["lines"] if ln)
        body = ""
        if h["blen"]:
            text = printable(h["body"], BODY_CHARS)
            more = f" (les {BODY_CHARS} premiers caractères)" if h["blen"] > BODY_CHARS else ""
            body = (f'<p class="pc-sub">Corps : {h["blen"]} octets{esc(more)}'
                    f'{", " + esc(h["ctype"]) if h["ctype"] else ""}</p><pre class="pc-body">{esc(text)}</pre>')
        parts.append(f'<details open><summary>Hypertext Transfer Protocol</summary><ul class="pc-http">{lines}</ul>'
                     f'{body}</details>')
    elif pkt.get("data"):
        d = pkt["data"]
        parts.append(f'<details open><summary>Données ({len(d)} octets)</summary>'
                     f'<pre class="pc-body">{esc(printable(d, BODY_CHARS))}</pre></details>')
    return "".join(parts)


def view(data, selected, base, cut_note=""):
    """The preview body. `selected` is the ?p= value, `base` the preview URL."""
    cap = parse(data)
    if "error" in cap:
        msg = ("Cette capture est au format pcapng, que l'aperçu ne lit pas encore."
               if cap["error"] == "pcapng" else "Ce fichier ne ressemble pas à une capture pcap lisible.")
        return (f'<div class="sheet nopv"><h2>Aperçu non disponible</h2><p>{msg} '
                'Téléchargez-le pour l\'ouvrir dans un analyseur réseau.</p></div>')
    pk = cap["packets"]
    sel = int(selected) if str(selected).isdigit() and 1 <= int(selected) <= len(pk) else None
    dur = pk[-1]["rel"] if pk else 0
    rows = []
    for p in pk:
        cls = f'pc-{p["proto"].lower()}' + (" pc-on" if p["n"] == sel else "")
        href = f'{base}?p={p["n"]}#paquet'
        cur = ' aria-current="true"' if p["n"] == sel else ""
        rows.append(
            f'<tr class="{esc(cls)}"><td class="num"><a href="{esc(href)}"{cur}>{p["n"]}</a></td>'
            f'<td class="num">{p["rel"]:.6f}</td><td>{esc(p["src"])}</td><td>{esc(p["dst"])}</td>'
            f'<td>{esc(p["proto"])}</td><td class="num">{p["origlen"]}</td>'
            f'<td class="pc-info"><a href="{esc(href)}" tabindex="-1">{esc(p["info"])}</a></td></tr>')
    note = ""
    if cap["truncated"]:
        note = (f'<p class="status">Capture tronquée ou trop longue : {len(pk)} paquets affichés. '
                'Téléchargez-la pour la voir en entier.</p>')
    summary = (f'<p class="pc-meta">{len(pk)} paquet{"s" if len(pk) > 1 else ""}, sur {dur:.3f} s. '
               f'Lien : {esc(LINKTYPES.get(cap["link"], str(cap["link"])))}. '
               f'Cliquez sur un paquet pour voir son détail.</p>')
    table = ('<div class="pc-list"><table class="pc-tbl"><thead><tr><th class="num">N°</th><th class="num">Temps</th>'
             '<th>Source</th><th>Destination</th><th>Protocole</th><th class="num">Longueur</th><th>Infos</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')
    if sel:
        detail = (f'<section class="pc-detail" id="paquet" aria-label="Détail du paquet {sel}">'
                  f'<h2>Paquet {sel}</h2>{detail_html(pk[sel - 1])}</section>')
    else:
        detail = ('<section class="pc-detail pc-empty" id="paquet"><p>Aucun paquet sélectionné. Cliquez sur une ligne '
                  'de la liste pour afficher ses couches : trame, Ethernet, IP, TCP ou UDP, et HTTP.</p></section>')
    return (cut_note + note + f'<div class="sheet wide pc">{summary}{table}{detail}</div>')
