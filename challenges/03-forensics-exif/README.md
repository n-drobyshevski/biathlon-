# 03 · In Transition — `Forensics` · Easy · 75 pts

> DécaFlop posted a photo from its race crew on the sponsor's website. It looks
> like any other event photo — but cameras remember more than what they show,
> and plenty of sites publish photos without ever stripping that. When and
> *where* was this taken, and who shot it?

**Connect:** `http://<CTF-HOST>:8001`

The photo is published in DécaFlop's news section ("Actualités"). Save the
full-size original and read its metadata: the flag is in there. (The timestamp,
GPS location and the photographer's tag are useful later — note them down.)

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>Photos carry EXIF metadata. A website rarely removes it.</details>
<details><summary>Hint 2 (−25)</summary><code>exiftool transition_shot.jpg</code> — look at the Image Description, Artist, Date/Time and GPS fields.</details>
