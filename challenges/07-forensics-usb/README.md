# 07 · The Referee's USB — `Forensics` · Medium · 125 pts

> A referee left a USB stick in the timing booth. They swear they "deleted
> everything sensitive." Deleting a file doesn't erase its bytes, though — it
> just forgets where they are. We imaged the stick. Recover what was removed.

**Connect:** `http://<CTF-HOST>:8020` — internal wiki **Intranet DFlop**, space **Arbitrage**, page « Clé USB retrouvée » (`referee_usb.img`). Credentials are on the DécaFlop staff portal — see challenge 01.

Download the disk image. A file was deleted from it. Carve it back out and read the flag.
(Grepping for the flag won't work — the bytes you need aren't text.)

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−15)</summary>File carving = finding files by their magic bytes in raw data.</details>
<details><summary>Hint 2 (−30)</summary><code>binwalk -e referee_usb.img</code> or <code>foremost referee_usb.img</code>. Look for an embedded PNG, extract it, and open it.</details>
