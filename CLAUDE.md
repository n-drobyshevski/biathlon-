# Project: Opération Dernière Transition (CTF)

## Stack
- Python/Flask + Jinja2, plain CSS, Docker Compose
- Runs on Raspberry Pi 5 (4GB), offline, no internet at runtime
- Flags NEVER hardcoded — always os.environ["FLAG_XX"]
- Players use locked-down corporate laptops: browser-only, no client installs

## Language rules
- ALL player-facing UI text, labels, tooltips, error messages, documentation: FRENCH
- Code comments and variable names: English
- French tone: professional IT/security ("cellule de crise" narrative)

## Key conventions
- Every Flask challenge app reads its flag from env vars set by scripts/gen-flags.sh
- Templates go in <app>/templates/, static assets in <app>/static/
- The SAP mock (challenges/14/) must look like SAP GUI for HTML (early 2010s enterprise)
- The Intranet (share/) is a file share + wiki, port 8020

## Architecture (Phase 2 focus)
- challenges/14/ = Mock SAP WebGUI (Level 3, Basis Admin)
- share/ = Intranet + Documentation Technique wiki (Level 2)
- handouts/generate.py = builds all forensics/SAP evidence files

## Do NOT
- Never commit flags or secrets
- Never use Flask dev server in production Dockerfiles (use gunicorn)
- Never add external CDN links (everything is offline/self-hosted)
