#!/bin/bash
# Organizer check, run during prep on the Pi:
#   docker compose run --rm toolbox selftest
# Confirms every tool the hints and the hub's Outils tile name is installed and
# can do the job it is named for. Prints one line per check, exits non-zero on
# any failure. Uses only made-up data (no flags, no challenge files).
set -u
fail=0
ok()  { printf '  ok    %s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; fail=1; }
has() { command -v "$1" >/dev/null 2>&1; }

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cd "$tmp" || exit 1

echo "Commandes installées"
for t in git git-dumper curl wget python3 jq xxd strings file unzip \
         binwalk foremost exiftool pngcheck fls icat mmls tshark \
         john zip2john hashcat jwt_tool grab; do
    if has "$t"; then ok "$t"; else bad "$t introuvable"; fi
done

echo "John the Ripper (jumbo)"
formats="$(john --list=formats 2>/dev/null | tr -d ' \n')"
for f in Raw-MD5 HMAC-SHA256 PKZIP ZIP; do
    case ",$formats," in *",$f,"*) ok "john format $f" ;; *) bad "john sans le format $f" ;; esac
done
printf 'hello\nPASSWORD\nworld\n' > words.txt
printf 'x:%s\n' "$(printf PASSWORD | md5sum | cut -d' ' -f1)" > md5.txt
if john --format=Raw-MD5 --wordlist=words.txt --pot=./t.pot md5.txt >/dev/null 2>&1 \
   && john --show --format=Raw-MD5 --pot=./t.pot md5.txt 2>/dev/null | grep -q ':PASSWORD$'; then
    ok "john casse un MD5 avec une wordlist"
else
    bad "john ne casse pas un MD5 de test"
fi

echo "hashcat"
modes="$(hashcat --help 2>/dev/null)"
for m in 0 16500 17200; do
    if printf '%s\n' "$modes" | grep -Eq "^ +$m \|"; then ok "hashcat -m $m"; else bad "hashcat sans -m $m"; fi
done

echo "jwt_tool"
tok="$(python3 -c 'import jwt; print(jwt.encode({"u":"x"}, "PASSWORD", algorithm="HS256"))' 2>/dev/null)"
if jwt_tool "$tok" -C -d words.txt 2>/dev/null | grep -q 'PASSWORD'; then
    ok "jwt_tool retrouve un secret HS256 de test"
else
    bad "jwt_tool ne retrouve pas le secret de test"
fi

echo "Fichiers"
python3 - <<'PY' > t.png
import struct, zlib, sys
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
raw = b"\x00\x00"
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
sys.stdout.buffer.write(png + b"trailing")
PY
if file t.png | grep -q 'PNG image'; then ok "file reconnaît un PNG"; else bad "file"; fi
if pngcheck -v t.png 2>&1 | grep -qi 'additional data after IEND'; then
    ok "pngcheck signale des données après IEND"
else
    bad "pngcheck ne voit pas les données après IEND"
fi

echo
if [ "$fail" -eq 0 ]; then echo "Tout est prêt."; else echo "Des outils manquent : voir FAIL ci-dessus."; fi
exit "$fail"
