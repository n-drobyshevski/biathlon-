# 03 · At the Range — `Forensics` · Easy · 75 pts

> A photo turned up from the shooting range the evening before the final race.
> No text, nothing obvious in the picture — but cameras remember more than
> what they show. When and *where* was this taken, and who shot it?

**Handout:** `range_shot.jpg`

The flag is in the image's metadata. (The timestamp, GPS location and the
photographer's tag are useful later — note them down.)

**Flag format:** `BIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>Photos carry EXIF metadata.</details>
<details><summary>Hint 2 (−25)</summary><code>exiftool range_shot.jpg</code> — look at the Image Description, Artist, Date/Time and GPS fields.</details>
