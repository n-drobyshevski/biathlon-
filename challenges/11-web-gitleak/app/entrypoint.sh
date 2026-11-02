#!/bin/sh
# Build the site's git history at startup so the flag (from $FLAG) lives in an
# old commit. The vuln: the whole .git directory is served to the web.
set -e
SITE="${SITE_DIR:-/srv/site}"
# The results API's JWT signing secret (challenge 10). Same value 10 signs with;
# docker-compose passes the same literal to both. It lands in the FIRST commit's
# config below, so dumping .git leaks it — an alternate route into challenge 10.
API_JWT_SECRET="${API_JWT_SECRET:-DecaFlop2026}"
rm -rf "$SITE"; mkdir -p "$SITE"; cd "$SITE"
git init -q
git config user.email "crew@decaflop.local"
git config user.name "DFlop Timing Bot"

cat > index.html <<'HTML'
<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DécaFlop · Chronométrage</title>
<style>body{font-family:system-ui,sans-serif;background:#10243a;color:#eaf2fb;margin:0}
header{background:#0a1626;padding:20px 24px;border-bottom:3px solid #4fb0ff}
main{max-width:640px;margin:36px auto;padding:0 18px;line-height:1.6}
.card{background:#14304d;border:1px solid #2d5d8c;border-radius:10px;padding:18px}</style>
</head><body><header><h1>⏱ DécaFlop · Chronométrage</h1></header>
<main><div class="card"><p>Portail de chronométrage de la finale. Les temps
intermédiaires sont publiés ici pendant la course.</p>
<p>Déploiement : <code>git pull</code> sur le serveur, comme d'habitude.</p></div></main></body></html>
HTML

# commit 1: the site, with a config file that still holds the secrets —
# the results export token AND the results API's JWT signing secret
cat > config.py <<CFG
# DécaFlop chronométrage — configuration
DB_HOST = "db.decaflop.local"
DB_USER = "timing"
DB_PASS = "T1m1ng-db-2026"
# Jeton d'export des résultats officiels (NE PAS committer)
EXPORT_TOKEN = "$FLAG"
# Clé de signature des jetons de l'API des résultats (partagée, NE PAS committer)
RESULTS_API_JWT_SECRET = "$API_JWT_SECRET"
CFG
git add -A
git commit -q -m "Initial timing site + config"

# commit 2: someone "removes" the secret — but git never forgets
cat > config.py <<'CFG'
# DécaFlop chronométrage — configuration
# Secrets déplacés vers des variables d'environnement (voir .env, non committé).
import os
DB_HOST = os.environ.get("DB_HOST", "db.decaflop.local")
DB_USER = os.environ.get("DB_USER", "timing")
DB_PASS = os.environ.get("DB_PASS", "")
EXPORT_TOKEN = os.environ.get("EXPORT_TOKEN", "")
RESULTS_API_JWT_SECRET = os.environ.get("RESULTS_API_JWT_SECRET", "")
CFG
printf '.env\n__pycache__/\n' > .gitignore
git add -A
git commit -q -m "Déplace les secrets vers des variables d'environnement; ajoute .gitignore"

exec python /app/app.py
