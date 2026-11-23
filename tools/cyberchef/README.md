# CyberChef (browser toolbox)

A static, fully client-side build of [CyberChef](https://github.com/gchq/CyberChef),
served on the offline LAN at `http://<PiIP>:8090`. Players on locked-down
laptops use it for base64, EXIF, unzip (including password-protected archives),
file carving (**Extract Files**), MD5 and JWT decode/sign/verify — all in the
browser, nothing to install.

## Build (needs internet once, during prep)

`docker compose up -d --build` builds the `cyberchef` service locally (arm64).
The build downloads the pinned release set in the `Dockerfile`
(`CYBERCHEF_VERSION`, currently v10.24.0) and checks its SHA-256
(`CYBERCHEF_SHA256`), so a corrupted or swapped download fails the build.

To move to a newer release, change both build args together:

```bash
v=v10.24.0   # the release tag
curl -fsSLO "https://github.com/gchq/CyberChef/releases/download/$v/CyberChef_$v.zip"
sha256sum "CyberChef_$v.zip"   # paste into CYBERCHEF_SHA256
```

## Building with no network

Drop a release zip in here as `cyberchef.zip` before building. When that file
exists the build uses it as-is and downloads nothing:

```bash
cp ~/Downloads/CyberChef_v*.zip tools/cyberchef/cyberchef.zip
```

`cyberchef.zip` is git-ignored, so it never lands in version control.
