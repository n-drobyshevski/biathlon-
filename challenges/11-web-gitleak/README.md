# 11 · Deleted, Not Gone — `Web` · Hard · 150 pts

> The DécaFlop timing site is deployed with `git pull` straight onto the server
> — and the `.git` folder came along for the ride. Someone did remove the export
> token from the config "to be safe". Git, however, keeps everything.

**Connect:** `http://<CTF-HOST>:8011`

The site's `.git` directory is reachable. Recover it, read the history, and find
the secret that was removed.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Deploying with git can expose the repository. Try browsing to <code>/.git/</code>.</details>
<details><summary>Hint 2 (−30)</summary>Mirror it and treat it as a repo: <code>wget -r http://&lt;host&gt;:8011/.git/</code> (or <code>git-dumper</code>), then <code>git log</code>.</details>
<details><summary>Hint 3 (−50)</summary>The token was removed in the last commit. Look at the one before it: <code>git show HEAD~1:config.py</code>.</details>
