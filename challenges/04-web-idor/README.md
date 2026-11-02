# 04 · Not Your Profile — `Web` · Medium · 100 pts

> The DécaFlop Athlete Portal lets each competitor view their own profile. You
> are logged in as guest bib **#1042**. The crew and admins use this same
> portal — and rumour is the admin's profile has an audit log of who touched
> the start lists.

**Connect:** `http://<CTF-HOST>:8004`

Read a profile that isn't yours. The flag (and a key story clue) live on an
account with a much lower number than yours.

**Flag format:** `BIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Look at the URL after you log in. What does it contain?</details>
<details><summary>Hint 2 (−30)</summary>It's an IDOR. Change the id in <code>/profile/1042</code>. Crew/admin use low numbers like 1000–1001.</details>
