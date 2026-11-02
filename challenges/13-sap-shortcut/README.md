# 13 · Saved for Convenience — `SAP` · Easy · 75 pts

> On a crew laptop the audit finds a **SAP GUI shortcut** (`.sap`) for the DFlop
> ERP. Someone ticked "save password" so they wouldn't have to type it. Handy —
> and readable.

**Handout:** `dflop_erp.sap`

The shortcut has a saved password. Recover it.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>A <code>.sap</code> shortcut is a plain text file. Open it and look at the <code>Password</code> field.</details>
<details><summary>Hint 2 (−20)</summary>The saved password is Base64-encoded. Decode it: <code>echo &lt;value&gt; | base64 -d</code>.</details>
