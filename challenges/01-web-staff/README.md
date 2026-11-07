# 01 · The Sponsor's Secret — `Web` · Easy · 50 pts

> DécaFlop, the championship's title sponsor, swears their website has nothing
> to hide. The crew mentioned an "internal area" though. Funny — for something
> internal, they sure told the search engines about it.

**Connect:** `http://<CTF-HOST>:8001`

Find the staff portal and read the flag.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−0)</summary>Regardez le fichier robots.txt et le code source JavaScript de la page.</details>
<details><summary>Hint 2 (−10)</summary>What file do crawlers read before indexing a site?</details>
<details><summary>Hint 3 (−20)</summary>Visit <code>/robots.txt</code> and go to the path it tries to hide.</details>
<details><summary>Hint 4 (−50)</summary>Indice : Un post-it sur le moniteur de l'accueil indique les identifiants du portail interne : `{{SHARE_USER}} / {{SHARE_PASSWORD}}`. Utilisez-les pour accéder à l'Intranet DécaFlop.</details>
<!-- Hint 4 is the soft-gate safety net (organisers: make it free after 45 min with
     `python3 scripts/ctfd-setup.py --unlock-gate`). {{SHARE_*}} are filled from .env. -->
