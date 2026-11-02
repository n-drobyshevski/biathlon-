# 02 · Share Everywhere — `Forensics / Stego` · Easy · 50 pts

> DécaFlop's marketing team published the official race poster on the sponsor's
> website and asked everyone to "share it everywhere!" The poster looks normal.
> It is a little heavier than a poster should be, though.

**Connect:** `http://<CTF-HOST>:8001`

The poster is published in DécaFlop's press area ("Espace presse"). Download
it — then notice that something is tacked onto the end of the image. Pull it
out.

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>A PNG ends at its <code>IEND</code> chunk. What if there are more bytes after it?</details>
<details><summary>Hint 2 (−20)</summary>Try <code>unzip decaflop_poster.png</code> or <code>binwalk</code>.</details>
