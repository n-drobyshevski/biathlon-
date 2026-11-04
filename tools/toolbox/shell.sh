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
   exiftool, john, hashcat, tshark, unzip,
   xxd, jq, curl, wget, python3

 Les fichiers de preuve sont sur Intranet
 DécaFlop (port 8020) ; les services sur
 l'IP du Pi. curl/wget pour les récupérer.
 Pour le partage (login du challenge 01) :
   grab http://<IP-du-Pi>:8020/telecharger/<...>

 En ligne (via Cloudflare), ce terminal n'a
 ni internet ni IP du Pi : visez le service
 par son nom interne, port 5000, le même
 que son sous-domaine (site, share, idor,
 sqli, jwt, git, ssti, sapgw), par exemple
   wget http://share:5000/<chemin>
BANNER
echo " Espace de travail : $ws"
echo
exec bash
