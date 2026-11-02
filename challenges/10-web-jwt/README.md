# 10 · Forged Credentials — `Web` · Hard · 175 pts

> During the post-incident audit, the crew finds DécaFlop's **Results API**. It
> hands out a session token when you ask, and the official results are "admin
> only". The token is a JWT — and whoever set it up used a secret you can guess.

**Connect:** `http://<CTF-HOST>:8010`

Get a guest token from `/api/token`, then reach `/api/results` as an **admin**.
You'll need to forge your own token.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−20)</summary>The token has three dot-separated parts (<code>header.payload.signature</code>), base64url-encoded. The payload has a <code>role</code>. Decode it.</details>
<details><summary>Hint 2 (−40)</summary>It's signed <b>HS256</b>, which uses one shared secret. Crack it offline: <code>jwt_tool &lt;token&gt; -C -d wordlist.txt</code> or <code>hashcat -m 16500 token.txt wordlist.txt</code>. Then re-sign a payload with <code>role:admin</code>.</details>
<details><summary>Hint 3 (−70)</summary>The secret is <code>DecaFlop2026</code>. Forge <code>{"role":"admin"}</code> signed HS256 with it and send it as <code>Authorization: Bearer</code>.</details>
