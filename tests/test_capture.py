"""Network capture preview on the intranet (share/app/capture.py): packet list,
layers of the clicked packet, odd and damaged files never break the page."""
import base64
import re
import socket
import struct
import sys

import pytest

PCAP = "/apercu/Chronom%C3%A9trage/Captures/timing_booth.pcap"
FLAG = "TRIATHLON{pcap_creds_test}"          # conftest's FLAG_05_PCAP
TOTAL, OLD_N, AUTH_N = 43, 22, 28           # packets in timing_booth.pcap; the expired-password try; the accepted login


@pytest.fixture()
def capture(share_module):
    return sys.modules["capture"]


def test_list_shows_packets_without_headers(share):
    page = share.get(PCAP).data.decode()
    assert '<table class="pc-tbl">' in page and "/static/capture.css" in page.split("</head>")[0]
    assert f"{TOTAL} paquets" in page
    assert "GET /timing/submit?bib=1042 HTTP/1.1" in page and "HTTP/1.1 200 OK (text/plain)" in page
    assert "10.13.37.42" in page and "10.13.37.10" in page
    assert "Authorization" not in page and "Aucun paquet sélectionné" in page


def test_clicked_packet_shows_layers_and_http_headers(share):
    page = share.get(PCAP + f"?p={AUTH_N}").data.decode()
    for layer in (f"Trame {AUTH_N}", "Ethernet II", "Internet Protocol Version 4", "Transmission Control Protocol",
                  "Hypertext Transfer Protocol"):
        assert layer in page, layer
    creds = base64.b64encode(("timingop:" + FLAG).encode()).decode()
    assert f"<code>Authorization: Basic {creds}</code>" in page     # still base64: the player decodes it
    assert FLAG not in page
    assert f'aria-current="true">{AUTH_N}</a>' in page
    assert "01/11/2026 18:40:00" in page                           # the eve of the final, as in the story
    reply = share.get(PCAP + f"?p={AUTH_N + 1}").data.decode()
    assert "Corps : " in reply and "OK split recorded." in reply and "200 OK" in reply


def test_capture_has_smoke_and_a_rejected_decoy(share):
    page = share.get(PCAP).data.decode()
    for noise in ("DNS", "/live/classement.json", "401 Unauthorized", "10.13.37.61"):
        assert noise in page, noise
    old = base64.b64encode(b"timingop:chrono2025").decode()
    assert f"<code>Authorization: Basic {old}</code>" in share.get(PCAP + f"?p={OLD_N}").data.decode()
    assert "401 Unauthorized" in share.get(PCAP + f"?p={OLD_N + 1}").data.decode()   # the server refused it


@pytest.mark.parametrize("p", ["0", "44", "abc", "-1", "1e3"])
def test_bad_packet_number_shows_list_only(share, p):
    r = share.get(PCAP + "?p=" + p)
    assert r.status_code == 200 and "Aucun paquet sélectionné" in r.data.decode()


# ------------------------------------------------------------------ synthetic captures
def ipv4(src, dst, proto, payload):
    return struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 1, 0, 64, proto, 0,
                       socket.inet_aton(src), socket.inet_aton(dst)) + payload


def tcp(sport, dport, payload, flags=0x18):
    return struct.pack("!HHIIBBHHH", sport, dport, 1, 1, 5 << 4, flags, 1024, 0, 0) + payload


def udp(sport, dport, payload):
    return struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload


def eth(payload, etype=0x0800):
    return b"\x02" * 6 + b"\x04" * 6 + struct.pack("!H", etype) + payload


def pcap(frames, end="<", link=1, magic=0xa1b2c3d4, cut=0):
    out = struct.pack(end + "IHHiIII", magic, 2, 4, 0, 0, 65535, link)
    for i, f in enumerate(frames):
        out += struct.pack(end + "IIII", 1793558400 + i, 500, len(f), len(f)) + f
    return out[:len(out) - cut] if cut else out


def test_little_endian_nanoseconds_udp_and_raw_ip(capture):
    frames = [eth(ipv4("10.0.0.1", "10.0.0.53", 17, udp(5353, 53, b"\x00" * 12))),
              eth(ipv4("10.0.0.1", "10.0.0.2", 6, tcp(1234, 8080, b"POST /x HTTP/1.1\r\nHost: a\r\n\r\nbody")))]
    cap = capture.parse(pcap(frames, "<", magic=0xa1b23c4d))
    assert cap["ns"] and [p["proto"] for p in cap["packets"]] == ["DNS", "HTTP"]
    assert cap["packets"][1]["info"] == "POST /x HTTP/1.1"
    raw = capture.parse(pcap([ipv4("1.1.1.1", "2.2.2.2", 6, tcp(1, 2, b"", 0x02))], ">", link=101))
    assert raw["packets"][0]["proto"] == "TCP" and "[SYN]" in raw["packets"][0]["info"]


def test_truncated_pcapng_and_garbage(capture):
    frames = [eth(ipv4("10.0.0.1", "10.0.0.2", 6, tcp(1, 80, b"GET / HTTP/1.1\r\n\r\n")))] * 3
    cut = capture.parse(pcap(frames, cut=10))
    assert cut["truncated"] and len(cut["packets"]) == 3
    assert "Capture tronquée" in capture.view(pcap(frames, cut=10), "", "/x")
    assert capture.parse(b"\x0a\x0d\x0d\x0a" + b"\x00" * 40) == {"error": "pcapng"}
    assert "pcapng" in capture.view(b"\x0a\x0d\x0d\x0a" + b"\x00" * 40, "", "/x")
    assert capture.parse(b"not a capture at all") == {"error": "format"}
    bad = capture.parse(pcap([eth(b"\x45\x00\x00")]))        # IP header cut short: no crash
    assert len(bad["packets"]) == 1


def test_everything_is_escaped(capture):
    evil = b"GET /<script>alert(1)</script> HTTP/1.1\r\nX-Evil: <img src=x onerror=1>\r\n\r\n<b>body</b>"
    page = capture.view(pcap([eth(ipv4("10.0.0.1", "10.0.0.2", 6, tcp(1, 80, evil)))]), "1", "/x")
    assert "<script>alert(1)" not in page and "<img src=x" not in page and "<b>body" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_packet_cap(capture, monkeypatch):
    monkeypatch.setattr(capture, "MAX_PACKETS", 5)
    frames = [eth(ipv4("10.0.0.1", "10.0.0.2", 6, tcp(1, 80, b"")))] * 9
    cap = capture.parse(pcap(frames))
    assert len(cap["packets"]) == 5 and cap["truncated"]


def test_stylesheet_is_local(share_anon):
    r = share_anon.get("/static/capture.css")
    assert r.status_code == 200 and not re.search(r"https?://", r.data.decode())
