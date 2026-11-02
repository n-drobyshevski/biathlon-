# CyberChef — static, 100% client-side toolbox served over the offline LAN.
# Arch-independent payload (plain JS/HTML) on a multi-arch nginx base, so this
# builds natively on the Pi (arm64). No build-time network: the organizer drops
# the release zip in as tools/cyberchef/cyberchef.zip (see README.md).
FROM nginx:alpine

RUN apk add --no-cache unzip

# The CyberChef release zip (NOT committed — see README.md / .gitignore).
COPY cyberchef.zip /tmp/cyberchef.zip

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
