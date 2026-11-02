# 06 · Results Admin — `Web` · Medium · 125 pts

> The official results are pushed through the DécaFlop Results Admin login.
> "Authorized crew only," it says. The login form was clearly written in a
> hurry the night before the race.

**Connect:** `http://<CTF-HOST>:8006`

Get in without valid credentials. The flag is on the dashboard, along with a
pointer to where the *real* results live.

**Flag format:** `BIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>What happens if you put a single quote <code>'</code> in the username?</details>
<details><summary>Hint 2 (−30)</summary>Classic SQL injection auth bypass. Try username <code>' OR '1'='1' -- </code> (note the trailing space) and any password.</details>
