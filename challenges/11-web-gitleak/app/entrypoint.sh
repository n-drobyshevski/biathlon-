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

# The site uses the intranet stylesheet that the app serves at /static/ (it is
# not part of the repo). The Applications links are filled in from the host the
# visitor used, since this page is static.
cat > index.html <<'HTML'
<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Temps intermédiaires - Chronométrage</title>
<link rel="stylesheet" href="/static/intranet.css">
</head><body>
<div class="suite"><a class="brand" data-port="8020" href="/">DécaFlop <span>Intranet</span></a>
<nav class="suite-nav" aria-label="Intranet"><a data-port="8020" href="/">Actualités</a><a data-port="8020" data-path="/documents" href="/">Partage</a><a data-port="8020" data-path="/annuaire" href="/">Annuaire</a>
<details class="apps"><summary>Applications</summary><ul>
<li><a data-port="8020" href="/"><b>Intranet DécaFlop</b><small>Actualités, documents, annuaire</small></a></li><li class="sep"></li>
<li><a data-port="8004" href="/"><b>Espace athlètes</b><small>Dossards, vagues, parc à vélos</small></a></li>
<li><a data-port="8006" href="/"><b>Admin résultats</b><small>Saisie et validation des classements</small></a></li>
<li><a data-port="8010" href="/"><b>Results API</b><small>API des résultats (JSON, v2)</small></a></li>
<li><a href="/"><b>Chronométrage</b><small>Temps intermédiaires de la finale</small></a></li>
<li><a data-port="8012" href="/"><b>Certificats de finaliste</b><small>Génération et impression</small></a></li>
<li><a data-port="8014" href="/"><b>Gateway SAP (SMGW)</b><small>Moniteur du gateway DFL</small></a></li>
</ul></details></nav>
<span class="me"><a data-port="8020" data-path="/login" href="/">Se connecter</a></span><a class="ic" data-port="8020" data-path="/aide" href="/" title="Aide">?</a></div>
<header class="site"><a class="site-logo" href="/" aria-hidden="true" tabindex="-1">CH</a>
<div><div class="site-title"><a href="/">Chronométrage</a></div>
<nav class="topnav" aria-label="Site"><a href="/" aria-current="page">Temps intermédiaires</a></nav></div></header>
<div class="body wide"><main class="main" id="main">
<h1 class="h1">Finale 2026 · temps intermédiaires</h1>
<p class="status">Publication suspendue&#160;: vérification de la liste de départ en cours (direction de course).</p>
<div class="cols"><div>
<section class="wp"><h2>Points de chronométrage</h2>
<table class="list data"><thead><tr><th style="width:50px">Point</th><th>Emplacement</th><th style="width:80px">km</th><th style="width:90px">État</th></tr></thead><tbody>
<tr><td>P0</td><td>Départ natation (ponton du port)</td><td class="num">0,0</td><td><span class="pill ok">actif</span></td></tr>
<tr><td>P1</td><td>Sortie de l'eau / entrée parc</td><td class="num">1,5</td><td><span class="pill ok">actif</span></td></tr>
<tr><td>P2</td><td>Sortie T1</td><td class="num">1,6</td><td><span class="pill ok">actif</span></td></tr>
<tr><td>P3</td><td>Vélo, rond-point des Îles</td><td class="num">21,6</td><td><span class="pill ok">actif</span></td></tr>
<tr><td>P4</td><td>Entrée T2</td><td class="num">41,6</td><td><span class="pill ok">actif</span></td></tr>
<tr><td>P5</td><td>Course, fin de boucle 2</td><td class="num">48,3</td><td><span class="pill">en attente</span></td></tr>
<tr><td>P6</td><td>Arrivée (quai d'honneur)</td><td class="num">51,6</td><td><span class="pill">en attente</span></td></tr>
</tbody></table></section>
</div><div>
<section class="wp"><h2>Exploitation</h2><dl class="kv">
<dt>Serveur</dt><dd>timing.decaflop.local</dd><dt>Déploiement</dt><dd><code>git pull</code> sur le serveur</dd>
<dt>Cabine</dt><dd>Wi-Fi staff DECAFLOP-TIMING</dd><dt>Contact</dt><dd>Lars Eriksen, poste 230</dd></dl></section>
</div></div>
</main></div>
<footer class="foot"><span>Direction des Systèmes d'Information</span><span>Assistance&#160;: poste 300</span><span>Chronométrage · finale 2026</span><span class="ver">DFlop Timing 1.4</span></footer>
<script>
document.querySelectorAll('a[data-port]').forEach(function(a){
 a.href=location.protocol+'//'+location.hostname+':'+a.dataset.port+(a.dataset.path||'/');});
</script>
</body></html>
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
