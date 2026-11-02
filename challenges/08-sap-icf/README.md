# 08 · SAP DFlop ERP — `SAP` · Hard · 200 pts

> DécaFlop runs everything on **SAP DFlop ERP** — inventory, payroll, and (it
> turns out) the authoritative race results. Their Basis admin is... learning
> on the job. The logon screen is exposed on the event network. Get in.

**Connect:** `http://<CTF-HOST>:8008`

This is a (simulated) SAP NetWeaver / Fiori system. Two real-world SAP
mistakes will get you administrative access and the flag.

**Flag format:** `BIATHLON{...}`

<details><summary>Hint 1 (−25)</summary>Some SAP ICF services are reachable without logging in. Try <code>/robots.txt</code>, then <code>/sap/public/info</code> and read the Basis note carefully.</details>
<details><summary>Hint 2 (−40)</summary>When the <b>SAP*</b> emergency user is deleted and not recreated, SAP falls back to a hard-coded default password. Look up "SAP* default password". Log on to client <code>001</code> as user <code>SAP*</code>.</details>
<details><summary>Hint 3 (−60)</summary>User <code>SAP*</code>, password <code>06071992</code>, client <code>001</code>.</details>
