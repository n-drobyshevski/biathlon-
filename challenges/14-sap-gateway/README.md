# 14 · The Open Gateway — `SAP` · Medium · 150 pts

> The audit reaches the **SAP DFlop ERP gateway**. Its monitor is on the event
> network, and the Basis team never got around to locking down who may talk to
> it.

**Connect:** `http://<CTF-HOST>:8014`

Read the gateway's security state, then do what a missing ACL lets you do.

> This challenge *simulates* the SAP Gateway reginfo/secinfo exposure for a
> training event. It models the information disclosure and the open-registration
> check only — no real RFC or registration protocol is involved.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−25)</summary>The gateway's <code>reginfo</code>/<code>secinfo</code> access lists decide which external programs may register. Read <code>/sap/gw/reginfo</code> — what does an empty ACL mean?</details>
<details><summary>Hint 2 (−40)</summary>With no ACL, any external program may register. Register one via the monitor's form (any program name) and the gateway trusts it.</details>
