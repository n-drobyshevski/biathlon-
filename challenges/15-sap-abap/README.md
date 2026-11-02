# 15 · Hardcoded — `SAP` · Medium · 150 pts

> The last audit finding: a custom ABAP report, `ZDFLOP_RESULT_EXPORT`, that
> pushes the results over RFC. Its export token is "not committed" — except it's
> right there in the source, just not spelled out in one place.

**Connect:** `http://<CTF-HOST>:8020` — internal wiki **Intranet DFlop**, space **Basis SAP**, page « Développements » (`ZDFLOP_RESULT_EXPORT.abap`). Credentials are on the DécaFlop staff portal — see challenge 01.

Download the report, read it, and recover the export token.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>Grepping for the flag won't work — it isn't a single string literal. Read how <code>lv_token</code> is built.</details>
<details><summary>Hint 2 (−30)</summary>The token is assembled with <code>CONCATENATE</code> from three variables, in the order <code>lv_a</code> + <code>lv_b</code> + <code>lv_c</code>. Ignore <code>lv_decoy</code>. Join their values in that order.</details>
