#!/usr/bin/env bash
# ============================================================================
#  build-handouts.sh — generate the forensics / stego handout files.
#  These are static files players download. They are built FROM the flags in
#  .env, so they are never committed (see .gitignore) and never spoil anything
#  in the public repo.
#
#  Builds a small arm64 generator image, then runs each challenge generator.
#  Output goes to handouts/dist/.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f .env ]] || { echo "No .env found. Run ./scripts/gen-flags.sh first."; exit 1; }

echo "[*] Building generator toolbox image (arm64-friendly)..."
docker build -t decaflop-gen -f handouts/Dockerfile .

echo "[*] Generating handout files -> handouts/dist/"
mkdir -p handouts/dist
docker run --rm \
  --env-file .env \
  -v "$PWD/handouts/dist:/out" \
  decaflop-gen

echo
echo "[+] Done. Files for players:"
ls -la handouts/dist/
echo
echo "Hand these out (per challenge):"
echo "  02 stego    -> decaflop_poster.png"
echo "  03 exif     -> transition_shot.jpg"
echo "  05 pcap     -> timing_booth.pcap"
echo "  07 usb      -> referee_usb.img"
echo "  09 sap      -> SAP_USR02_export.csv  + sap_hint.txt"
