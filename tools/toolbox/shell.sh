#!/bin/bash
# Each browser connection to ttyd gets its own scratch workspace, so players
# don't collide in a shared directory.
ws="$(mktemp -d /work/session-XXXXXX 2>/dev/null)" || ws="/work"
cd "$ws" 2>/dev/null || cd /work

cat <<'BANNER'
────────────────────────────────────────────────────────────
 DÉCAFLOP — boîte à outils de l'équipe  (navigateur → shell)
────────────────────────────────────────────────────────────
 Outils : git, git-dumper, binwalk, foremost, exiftool, john, hashcat, tshark,
          unzip, xxd, jq, curl, wget, python3.

 Le shell tourne SUR le Pi : rien à téléverser depuis le PC, on
 récupère les fichiers directement depuis les services —
   • site public (:8001)  curl -OJ http://<IP-du-Pi>:8001/medias/decaflop_poster.png
   • Intranet (:8020)     grab http://<IP-du-Pi>:8020/telecharger/<...>
                          (grab demande le login — celui du challenge 01)
   • dépôt .git (:8011)   git-dumper http://<IP-du-Pi>:8011/.git/ dump && cd dump
BANNER
echo " Espace de travail : $ws"
echo
exec bash
