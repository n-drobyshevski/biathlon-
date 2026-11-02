#!/bin/bash
# Each browser connection to ttyd gets its own scratch workspace, so players
# don't collide in a shared directory.
ws="$(mktemp -d /work/session-XXXXXX 2>/dev/null)" || ws="/work"
cd "$ws" 2>/dev/null || cd /work

cat <<'BANNER'
────────────────────────────────────────────────────────────
 DÉCAFLOP — boîte à outils de l'équipe  (navigateur → shell)
────────────────────────────────────────────────────────────
 Outils : git, git-dumper, binwalk, foremost, exiftool, john,
          unzip, xxd, jq, curl, wget, python3.
 Les fichiers de preuve sont sur le Partage DFlop (:8020) et
 les services tournent sur l'IP du Pi — récupérez-les au besoin
 (ex. : git-dumper http://<IP-du-Pi>:8011/.git/ dump && cd dump).
BANNER
echo " Espace de travail : $ws"
echo
exec bash
