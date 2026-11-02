# 01 · The Sponsor's Secret — `Web` · Easy · 75 pts

> DécaFlop, the championship's title sponsor, swears their website has nothing
> to hide. The crew mentioned an "internal area" though — and for something
> internal, they sure told the search engines about it.

**Connect:** `http://<CTF-HOST>:8001`

Two steps. First, find the staff portal and read the flag. Then notice it links
the team's intranet with a **"saved" login** — the credentials aren't printed on
the page, but the little script the portal loads knows them. Recover the intranet
username and password (you'll need them for missions 05, 07, 09, 13 and 15).

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>What file do crawlers read before indexing a site? Visit <code>/robots.txt</code> and go to the path it tries to hide.</details>
<details><summary>Hint 2 (−20)</summary>The flag is on the portal. For the intranet login, view the page source: it loads a small script, <code>/static/tools.js</code>, that holds the "saved connection".</details>
<details><summary>Hint 3 (−30)</summary>In the script the username is in clear; the password is only Base64-encoded. Decode it: <code>echo &lt;value&gt; | base64 -d</code>.</details>
