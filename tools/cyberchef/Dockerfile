# CyberChef — static, 100% client-side toolbox served over the offline LAN.
# Arch-independent payload (plain JS/HTML) on a multi-arch nginx base, so this
# builds natively on the Pi (arm64).
#
# The build fetches a pinned CyberChef release and checks its SHA-256, so it
# needs internet once, during prep (like every other image). To build fully
# offline instead, drop a release zip in as tools/cyberchef/cyberchef.zip: when
# present it is used as-is and nothing is downloaded (see README.md).
FROM nginx:alpine

ARG CYBERCHEF_VERSION=v10.24.0
ARG CYBERCHEF_SHA256=29947b4d7805b74135c8370f3cba19b609d63e8ece6e33b2cb8ee0dfbbf1393c

# nginx:alpine already ships curl, unzip and sha256sum: no apk step, so the
# local-zip build below works with no network at all.

# README.md always exists, so this COPY works whether or not the optional
# cyberchef.zip (git-ignored) is there.
COPY README.md cyberchef.zip* /tmp/cc-src/

RUN set -eu; \
    if [ -f /tmp/cc-src/cyberchef.zip ]; then \
        echo "Using the local cyberchef.zip"; \
        mv /tmp/cc-src/cyberchef.zip /tmp/cyberchef.zip; \
    else \
        curl -fsSL -o /tmp/cyberchef.zip \
            "https://github.com/gchq/CyberChef/releases/download/${CYBERCHEF_VERSION}/CyberChef_${CYBERCHEF_VERSION}.zip"; \
        echo "${CYBERCHEF_SHA256}  /tmp/cyberchef.zip" | sha256sum -c -; \
    fi; \
    rm -rf /tmp/cc-src

# Unpack into the web root. The release may lay files at the root of the zip or
# inside a single top-level folder; flatten either shape, and make sure "/"
# serves the CyberChef_vX.Y.Z.html entry point.
RUN set -eu; \
    rm -rf /usr/share/nginx/html/*; \
    mkdir -p /tmp/cc; \
    unzip -q /tmp/cyberchef.zip -d /tmp/cc; \
    if [ "$(ls -1 /tmp/cc | wc -l)" = "1" ] && [ -d "/tmp/cc/$(ls -1 /tmp/cc)" ]; then \
        mv /tmp/cc/*/* /usr/share/nginx/html/; \
    else \
        mv /tmp/cc/* /usr/share/nginx/html/; \
    fi; \
    if [ ! -f /usr/share/nginx/html/index.html ]; then \
        entry="$(cd /usr/share/nginx/html && ls -1 CyberChef_*.html 2>/dev/null | head -n1)"; \
        [ -n "$entry" ] && ln -s "$entry" /usr/share/nginx/html/index.html; \
    fi; \
    rm -rf /tmp/cc /tmp/cyberchef.zip

EXPOSE 80
