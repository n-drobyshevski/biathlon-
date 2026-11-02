"""The shop serves the poster (02) and photo (03) from /medias, unchanged."""
import io
import sys
import zipfile

import piexif
import pytest

from conftest import TEST_FLAGS


def _disk_bytes(dist, name):
    return (dist / name).read_bytes()


def test_poster_byte_identical(shop, dist):
    r = shop.get("/medias/decaflop_poster.png")
    assert r.status_code == 200
    assert r.mimetype == "image/png"
    assert r.data == _disk_bytes(dist, "decaflop_poster.png")


def test_photo_byte_identical(shop, dist):
    r = shop.get("/medias/transition_shot.jpg")
    assert r.status_code == 200
    assert r.mimetype == "image/jpeg"
    assert r.data == _disk_bytes(dist, "transition_shot.jpg")


def test_poster_still_unzips_to_flag(shop):
    r = shop.get("/medias/decaflop_poster.png")
    z = zipfile.ZipFile(io.BytesIO(r.data))          # ZIP trailer survived
    assert z.read("flag.txt").decode().startswith(TEST_FLAGS["FLAG_02_STEGO"])


def test_photo_keeps_exif(shop):
    r = shop.get("/medias/transition_shot.jpg")
    exif = piexif.load(r.data)
    zeroth, exif_ifd, gps = exif["0th"], exif["Exif"], exif["GPS"]
    assert zeroth[piexif.ImageIFD.ImageDescription].decode() == TEST_FLAGS["FLAG_03_EXIF"]
    assert zeroth[piexif.ImageIFD.Artist]                          # photographer tag
    assert exif_ifd[piexif.ExifIFD.DateTimeOriginal]               # timestamp
    assert gps[piexif.GPSIFD.GPSLatitude] and gps[piexif.GPSIFD.GPSLongitude]


@pytest.mark.parametrize("path", [
    "/medias/other.png",                 # not whitelisted
    "/medias/decaflop_poster.PNG",       # wrong case
    "/medias/app.py",                    # app source
    "/medias/..%2fapp.py",               # encoded traversal
    "/medias/transition_shot.jpg.bak",
])
def test_media_rejects_everything_else(shop, path):
    assert shop.get(path).status_code == 404


def test_missing_file_is_404(shop, shop_module, monkeypatch, tmp_path):
    # Whitelisted name, but the file isn't built in this (empty) dir.
    monkeypatch.setattr(sys.modules["shop"], "HANDOUT_DIR", str(tmp_path))
    assert shop.get("/medias/decaflop_poster.png").status_code == 404
    assert shop.get("/medias/transition_shot.jpg").status_code == 404
