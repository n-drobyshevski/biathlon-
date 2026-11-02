# 09 · Who Rigged the Race? — `SAP` · Hard · 250 pts · 🏁 FINALE

> The results table `ZRACE_RESULT` in SAP DFlop ERP was altered the night
> before the final race. The Basis team exported the system's user master
> table **USR02** — every account, its last logon, and its (weak, legacy)
> password hash. Prove who did it.

**Handouts:** `SAP_USR02_export.csv`, `sap_hint.txt`, `wordlist.txt`

1. Find the account whose **last logon** matches the sabotage window (cross-check
   the timestamp from the transition photo, challenge 03).
2. Crack that account's legacy password hash (see `sap_hint.txt`).
3. The recovered password opens **`case_file.zip`** (also handed out), which
   contains the final flag and names the saboteur.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−25)</summary>USR02 column <code>TRDAT</code>/<code>LTIME</code> = last logon date/time. Which user logged on on 2026-11-01 around 18:42?</details>
<details><summary>Hint 2 (−40)</summary><code>BCODE</code> here is MD5(UPPERCASE(password)). Crack VLINDQVIST's hash with <code>wordlist.txt</code> (or <code>hashcat -m 0</code>).</details>
<details><summary>Hint 3 (−70)</summary>The cracked password is <code>CHIP7</code>. Run <code>unzip -P CHIP7 case_file.zip</code>.</details>
