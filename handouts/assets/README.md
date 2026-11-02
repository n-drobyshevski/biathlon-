# Handout assets

`transition_photo.jpg` is the base picture for challenge 03
(`transition_shot.jpg`). It was supplied by the organizer and is
**AI-generated**: the original file carried C2PA content credentials from
Google's generative AI tools. The people, banners and bib numbers are not real.

The copy here was resized to 1600 px and **all original metadata was removed**
(EXIF, thumbnail, C2PA). `generate.py` writes the challenge EXIF (flag, artist,
timestamp, GPS, camera fields) when it builds the handout, so players only see
those fields. If this file is missing, `generate.py` falls back to a drawn scene.

`poster.png` is the artwork for challenge 02 (`decaflop_poster.png`). It was
supplied by the organizer and is **AI-generated**. The copy here was resized to
1200 px wide, saved without any metadata, and the comma after "LA FINALE," was
shortened so it no longer touches the N of "DEMAIN". `generate.py` re-encodes
it as PNG and appends the ZIP after the image data. If this file is missing,
`generate.py` draws a simple poster instead.
