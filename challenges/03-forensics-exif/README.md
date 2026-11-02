# 03 · In Transition — `Forensics` · Easy · 75 pts

> A photo from a crew camera turned up on the timing-booth PC. It looks like
> any other race photo — but cameras remember more than what they show. When
> and *where* was this taken, and who shot it?

**Handout:** `transition_shot.jpg`

The flag is in the image's metadata. (The timestamp, GPS location and the
photographer's tag are useful later — note them down.)

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>Photos carry EXIF metadata.</details>
<details><summary>Hint 2 (−25)</summary><code>exiftool transition_shot.jpg</code> — look at the Image Description, Artist, Date/Time and GPS fields.</details>
