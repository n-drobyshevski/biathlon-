# 03 · In Transition — `Forensics` · Easy · 75 pts

> A photo turned up from the transition zone the evening before the final race.
> No text, nothing obvious in the picture — but cameras remember more than
> what they show. When and *where* was this taken, and who shot it?

**Handout:** `transition_shot.jpg`

The flag is in the image's metadata. (The timestamp, GPS location and the
photographer's tag are useful later — note them down.)

**Flag format:** `TRIATHLON{...}`

<details><summary>Hint 1 (−10)</summary>Photos carry EXIF metadata.</details>
<details><summary>Hint 2 (−25)</summary><code>exiftool transition_shot.jpg</code> — look at the Image Description, Artist, Date/Time and GPS fields.</details>
