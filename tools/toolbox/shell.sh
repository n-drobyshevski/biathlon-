#!/bin/bash
# Each browser connection to ttyd gets its own scratch workspace, so players
# don't collide in a shared directory.
ws="$(mktemp -d /work/session-XXXXXX 2>/dev/null)" || ws="/work"
cd "$ws" 2>/dev/null || cd /work

cat <<'BANNER'
──────────────────────────────────────────────
 DÉCAFLOP, boîte à outils de l'équipe
──────────────────────────────────────────────
 Outils installés
   git, git-dumper, binwalk, foremost,
   exiftool, john, unzip, xxd, jq, curl,
   wget, python3

 Les fichiers de preuve sont sur Partage DFlop
 (port 8020) et les services sur l'IP du Pi.
 Récupérez-les avec curl ou wget, par exemple
   wget http://<IP-du-Pi>:<port>/<chemin>

 En ligne (via Cloudflare), ce terminal n'a
 ni internet ni IP du Pi : visez le service
 par son nom interne, port 5000, le même
 que son sous-domaine (site, share,
 athletes, resultats, api, chrono,
 certificats, sapgw), par exemple
   wget http://share:5000/<chemin>

BANNER
echo " Espace de travail : $ws"
echo
exec bash
