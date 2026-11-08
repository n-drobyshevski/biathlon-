# 10 · Forged Credentials — `Web` · Hard · 175 pts

> During the post-incident audit, the crew finds DécaFlop's **Results API** —
> the JSON service that's replacing the old web results admin. It hands out a
> session token when you ask, and the official results are "admin only". A guest
> token won't get you in.

**Connect:** `http://<CTF-HOST>:8010`

Get a guest token from `/api/token`, then reach `/api/results` as an **admin**.
You'll need to forge your own token.

_Alternate route: the signing secret may have leaked elsewhere in DécaFlop's
infrastructure. Finding it there saves you recovering it the hard way — but you
still forge the admin token and call the API yourself._

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−20)</summary>The token has three dot-separated parts (<code>header.payload.signature</code>), base64url-encoded. The payload has a <code>role</code>. Decode it.</details>
<details><summary>Hint 2 (−40)</summary>It's signed <b>HS256</b>, which uses one shared secret. Crack it offline: <code>jwt_tool &lt;token&gt; -C -d wordlist.txt</code> or <code>hashcat -m 16500 token.txt wordlist.txt</code>. Then re-sign a payload with <code>role:admin</code>.</details>
<details><summary>Hint 3 (−50)</summary>Le secret HS256 est faible. Essayez la wordlist /usr/share/wordlists/jwt_secrets.txt avec hashcat -m 16500, ou récupérez-le depuis le .git de la mission 11.</details>
<details><summary>Hint 4 (−70)</summary>The secret is <code>DecaFlop2026</code>. Forge <code>{"role":"admin"}</code> signed HS256 with it and send it as <code>Authorization: Bearer</code>.</details>
