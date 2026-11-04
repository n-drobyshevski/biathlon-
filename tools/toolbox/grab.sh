#!/bin/bash
# grab — download challenge evidence into the current directory.
#
# The ttyd shell runs ON the Pi, next to the services, so you never upload a
# file from your laptop — you pull it straight from the service:
#
#   public file (DécaFlop site :8001)   grab http://<IP>:8001/medias/decaflop_poster.png
#   Intranet share (:8020)              grab http://<IP>:8020/telecharger/<...> [user] [pass]
#
# The Intranet share needs a login; grab asks for it (use the account you found
# in challenge 01). Copy the exact download URL from the share page in your
# browser (right-click the file -> copy link).
set -euo pipefail

url="${1:-}"
if [ -z "$url" ]; then
  echo "usage: grab <url-du-fichier> [identifiant] [motdepasse]"
  exit 1
fi
base="$(printf '%s' "$url" | grep -oE '^https?://[^/]+' || true)"
if [ -z "$base" ]; then echo "URL invalide : $url"; exit 1; fi

if printf '%s' "$url" | grep -q ':8020/'; then
  # Intranet DécaFlop share — form login + session cookie.
  user="${2:-}"; pass="${3:-}"
  [ -n "$user" ] || read -rp "Identifiant Intranet : " user
  [ -n "$pass" ] || { read -rsp "Mot de passe : " pass; echo; }
  jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT
  # Open the login page first: the share hands this browser its own lockout
  # bucket in the session cookie, so a typo here never locks out other players
  # of this terminal (they all reach the share from the same IP).
  curl -s -c "$jar" -b "$jar" -o /dev/null "$base/login" || true
  curl -s -c "$jar" -b "$jar" \
       --data-urlencode "identifiant=$user" \
       --data-urlencode "motdepasse=$pass" \
       "$base/login" >/dev/null || true
  code="$(curl -s -b "$jar" -o /dev/null -w '%{http_code}' "$base/" || echo 000)"
  if [ "$code" != "200" ]; then
    echo "Login refusé — vérifiez les identifiants (challenge 01)."
    exit 1
  fi
  curl -fL -b "$jar" -OJ "$url" && echo "→ téléchargé." \
    || { echo "Échec du téléchargement — vérifiez l'URL."; exit 1; }
else
  # Public file (no login).
  curl -fL -OJ "$url" && echo "→ téléchargé." \
    || { echo "Échec du téléchargement — vérifiez l'URL."; exit 1; }
fi
