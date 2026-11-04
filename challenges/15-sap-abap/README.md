# 15 · Hardcoded — `SAP` · Medium · 150 pts

> The last audit finding: a custom ABAP report, `ZDFLOP_RESULT_EXPORT`, that
> pushes the results over RFC. Its export token is "not committed" — except it's
> right there in the source, just not spelled out in one place.

**Connect:** `http://<CTF-HOST>:8020` — internal share **Intranet DécaFlop**, folder `Basis SAP / Développements` (`ZDFLOP_RESULT_EXPORT.abap`). Credentials: recover them via challenge 01 (hidden on the DécaFlop site).

Download the report, read it, and recover the export token.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>The complete-looking token you can grep for is not the one sent in production. Check which branch runs on <code>DFL</code>, the production system named in the header.</details>
<details><summary>Hint 2 (−30)</summary>In the production branch the token is <code>CONCATENATE lv_k3 lv_k1 lv_k2</code>, and <code>lv_k1</code> first goes through <code>FORM normalize</code>, which reverses it (<code>reverse( )</code>). Turn that piece round, then join the three pieces in that order.</details>
