# 15 · Hardcoded — `SAP` · Medium · 150 pts

> The last audit finding: a custom ABAP report, `ZDFLOP_RESULT_EXPORT`, that
> pushes the results over RFC. Its export token is "not committed" — except it's
> right there in the source, just not spelled out in one place.

**Connect:** `http://<CTF-HOST>:8020` — internal share **Intranet DécaFlop**, folder `Basis SAP / Développements` (`ZDFLOP_RESULT_EXPORT.abap`, with a short `abap_lisezmoi.txt` next to it). Credentials: recover them via challenge 01 (hidden on the DécaFlop site).

Download the report, read it, and recover the export token.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Grepping for the flag won't work — it isn't a single string literal. Read how <code>lv_jeton_final</code> is built.</details>
<details><summary>Hint 2 (−30)</summary>The token is assembled with <code>CONCATENATE</code> from three variables, in the order <code>lv_partie1</code> + <code>lv_partie2</code> + <code>lv_partie3</code>. Ignore <code>lv_leurre</code>. Join their values in that order.</details>
