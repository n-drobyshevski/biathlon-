# 15 · Hardcoded — `SAP` · Medium · 150 pts

> The last audit finding: a custom ABAP report, `ZDFLOP_RESULT_EXPORT`, that
> pushes the results over RFC. Its export token is "not committed" — except it's
> right there in the source, just not spelled out in one place.

**Connect:** `http://<CTF-HOST>:8020` — internal share **Intranet DécaFlop**, folder `Basis SAP / Développements` (`ZDFLOP_RESULT_EXPORT.abap`, with a short `abap_lisezmoi.txt` next to it). Credentials: recover them via challenge 01 (hidden on the DécaFlop site).

Download the report, read it, and recover the export token. New to ABAP? The
intranet's **Documentation Technique** has a "Lire du code ABAP" article, and
`abap_lisezmoi.txt` (in French, next to the report) gives reading tips.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>The complete-looking token you can grep for is not the one sent in production. Check which branch runs on <code>DFL</code>, the production system named in the header.</details>
<details><summary>Hint 2 (−25)</summary>Dans la branche de production, cherchez l'instruction CONCATENATE : l'ordre des variables dans CONCATENATE a b c INTO resultat est l'ordre du jeton, pas l'ordre des affectations.</details>
<details><summary>Hint 3 (−30)</summary>In the production branch the token is <code>CONCATENATE lv_k3 lv_k1 lv_k2</code>, and <code>lv_k1</code> first goes through <code>FORM normalize</code>, which reverses it (<code>reverse( )</code>). Turn that piece round, then join the three pieces in that order.</details>
