# 11 · Deleted, Not Gone — `Web` · Hard · 150 pts

> This is the same timing chain whose booth login you sniffed in challenge 05 —
> here's its public site. It's deployed with `git pull` straight onto the server,
> so the `.git` folder came along for the ride. Someone did clean the secrets out
> of the config "to be safe"; git, however, keeps everything.

**Connect:** `http://<CTF-HOST>:8011`

The site's `.git` directory is reachable. Recover it, read the history, and find
the secret that was removed. That old config held **more than the export
token** — worth reading every line of it.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Deploying with git can expose the repository. Try browsing to <code>/.git/</code>.</details>
<details><summary>Hint 2 (−30)</summary>Mirror it and treat it as a repo: <code>wget -r http://&lt;host&gt;:8011/.git/</code> (or <code>git-dumper</code>), then <code>git log</code>.</details>
<details><summary>Hint 3 (−50)</summary>The secrets were removed in the last commit. Look at the one before it: <code>git show HEAD~1:config.py</code> — it holds the export token (the flag) <em>and</em> the results API's JWT signing secret, handy for challenge 10.</details>
