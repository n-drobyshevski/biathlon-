# 13 · Saved for Convenience — `SAP` · Easy · 75 pts

> On a crew laptop the audit finds a **SAP GUI shortcut** (`.sap`) for the DFlop
> ERP — system DFL, client 001, the very system whose user table named the
> saboteur in finale 09. Someone ticked "save password" so they wouldn't have to
> type it. Handy — and readable.

**Connect:** `http://<CTF-HOST>:8020` — internal wiki **Intranet DFlop**, space **IT**, page « Sauvegardes postes » (`dflop_erp.sap`). Credentials are on the DécaFlop staff portal — see challenge 01.

Download the shortcut: it has a saved password. Recover it.

The shortcut points at system **DFL**, client **001** — DécaFlop's production
ERP. That's the same system behind the USR02 export in challenge 09 and the SAP
gateway in challenge 14.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>A <code>.sap</code> shortcut is a plain text file. Open it and look at the <code>Password</code> field.</details>
<details><summary>Hint 2 (−20)</summary>The saved password is Base64-encoded. Decode it: <code>echo &lt;value&gt; | base64 -d</code>.</details>
