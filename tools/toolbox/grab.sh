#!/bin/bash
# grab — download challenge evidence into the current directory.
#
# The ttyd shell runs ON the Pi, next to the services, so you never upload a
# file from your laptop — you pull it straight from the service by its URL:
#
#   grab <url-du-fichier> [identifiant] [motdepasse]
#
# A public file downloads directly. A password-protected service asks for a
# login; grab prompts for it if you don't pass it on the command line. Copy
# the exact download URL from the page in your browser (right-click the file
# -> copy link).
set -euo pipefail

url="${1:-}"
if [ -z "$url" ]; then
  echo "usage: grab <url-du-fichier> [identifiant] [motdepasse]"
  exit 1
fi
base="$(printf '%s' "$url" | grep -oE '^https?://[^/]+' || true)"
if [ -z "$base" ]; then echo "URL invalide : $url"; exit 1; fi

if printf '%s' "$url" | grep -q ':8020/'; then
  # Password-protected share — form login + session cookie.
  user="${2:-}"; pass="${3:-}"
  [ -n "$user" ] || read -rp "Identifiant Intranet : " user
  [ -n "$pass" ] || { read -rsp "Mot de passe : " pass; echo; }
  jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT
  curl -s -c "$jar" \
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
