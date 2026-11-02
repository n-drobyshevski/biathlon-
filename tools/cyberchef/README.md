# CyberChef (browser toolbox)

A static, fully client-side build of [CyberChef](https://github.com/gchq/CyberChef),
served on the offline LAN at `http://<PiIP>:8090`. Players on locked-down
laptops use it for base64, EXIF, unzip (including password-protected archives),
file carving (**Extract Files**), MD5 and JWT decode/sign/verify — all in the
browser, nothing to install.

## One prep step (needs internet, do it before the event)

CyberChef is **not committed** to this repo (it's a ~30 MB release bundle).
Download it once and drop it in here as `cyberchef.zip`:

```bash
# from https://github.com/gchq/CyberChef/releases download the
# "CyberChef_vX.Y.Z.zip" asset, then:
cp ~/Downloads/CyberChef_v*.zip tools/cyberchef/cyberchef.zip
```

Then `docker compose up -d --build` builds the `cyberchef` service locally
(arm64). The build itself needs no network — it just unzips what you dropped in.

`cyberchef.zip` is git-ignored, so it never lands in version control.
