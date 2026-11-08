# 08 · Le Signal Fantôme — `Forensics / Réseau` · Medium · 125 pts

> La veille de la course, un équipement inconnu est apparu sur le segment réseau
> de la cabine de chronométrage. Personne ne sait qui l'a branché. Nous avons
> capturé le trafic de la nuit.

**Connect:** `http://<CTF-HOST>:8020` — partage interne **Intranet DécaFlop**, dossier `Réseau / Captures terrain` (`phantom_signal.zip`, mot de passe `infected`). Identifiants : à retrouver via le défi 01 (cachés sur le site DécaFlop).

Téléchargez la capture, décompressez-la et analysez-la. L'intrus a reçu une réponse de la passerelle SAP : la clé d'enregistrement qu'elle renvoie est le flag.

Relevez aussi l'adresse MAC et l'adresse IP de l'intrus : elles serviront au rapport d'incident final.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−25)</summary>Filtrez le trafic HTTP. Cherchez un POST vers /sap/gw/register. L'adresse MAC de la machine qui l'émet est l'intrus.</details>
