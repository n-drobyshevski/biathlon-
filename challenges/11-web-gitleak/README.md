# 11 · Deleted, Not Gone — `Web` · Hard · 150 pts

> The DécaFlop timing site was pushed live in a hurry, straight onto the server.
> Someone cleaned an export secret out of its config "to be safe" just before
> go-live. On a deploy done that fast, though, "removed" rarely means gone.

**Connect:** `http://<CTF-HOST>:8011`

Recover the export secret that was taken out of the config before go-live. What
you pull back held **more than the export token** — worth reading every line of
it.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Deploying with git can expose the repository. Try browsing to <code>/.git/</code>.</details>
<details><summary>Hint 2 (−30)</summary>Mirror it and treat it as a repo: <code>wget -r http://&lt;host&gt;:8011/.git/</code> (or <code>git-dumper</code>), then <code>git log</code>.</details>
<details><summary>Hint 3 (−50)</summary>The secrets were removed in the last commit. Look at the one before it: <code>git show HEAD~1:config.py</code> — it holds the export token (the flag) <em>and</em> the results API's JWT signing secret, handy for challenge 10.</details>
