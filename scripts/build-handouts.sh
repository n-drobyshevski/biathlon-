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
# Git Bash on Windows rewrites /c/... paths in arguments, which mangles the -v
# mount so the files land somewhere other than handouts/dist. Give Docker a
# native host path (C:/... via cygpath when available) and turn the rewriting
# off. On Linux (the Pi) cygpath is absent and MSYS_NO_PATHCONV is ignored.
HOST_DIR="$PWD"
command -v cygpath >/dev/null 2>&1 && HOST_DIR="$(cygpath -m "$PWD")"
MSYS_NO_PATHCONV=1 docker run --rm \
  --env-file .env \
  -v "$HOST_DIR/handouts/dist:/out" \
  decaflop-gen

echo
echo "[+] Done. Files for players:"
ls -la handouts/dist/
echo
echo "Published on the DécaFlop site ('staff' container, :8001):"
echo "  02 stego    -> decaflop_poster.png   (espace presse: /presse)"
echo "  03 exif     -> transition_shot.jpg   (actualités:    /actualites)"
echo
echo "On the internal share 'Intranet DécaFlop' ('share' container, :8020):"
echo "  05 pcap     -> Chronométrage / Captures / timing_booth.pcap"
echo "  08 pcap     -> Réseau / Captures terrain / phantom_signal.zip (password: infected)"
echo "  07 usb      -> Arbitrage / Pièces / referee_usb.img"
echo "  09 sap      -> Basis SAP / Exports / SAP_USR02_export.csv + sap_hint.txt"
echo "              -> IT / Outils / wordlist.txt"
echo "              -> Direction de course / Dossier incident / case_file.zip"
echo "  13 sap      -> IT / Sauvegardes postes / portable-equipe-03 / dflop_erp.sap"
echo "  15 sap      -> Basis SAP / Développements / ZDFLOP_RESULT_EXPORT.abap + abap_lisezmoi.txt"
