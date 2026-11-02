# 02 · Share Everywhere — `Forensics / Stego` · Easy · 50 pts

> DécaFlop's marketing team pushed out a promo poster for the final race and
> asked everyone to "share it everywhere!" The poster looks normal. It is a
> little heavier than a poster should be, though.

**Handout:** `decaflop_poster.png`

Something is tacked onto the end of this image. Pull it out.

**Flag format:** `BIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>A PNG ends at its <code>IEND</code> chunk. What if there are more bytes after it?</details>
<details><summary>Hint 2 (−20)</summary>Try <code>unzip decaflop_poster.png</code> or <code>binwalk</code>.</details>
