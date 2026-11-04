# Railway test deploy only (see deploy/railway/README.md). The Pi build
# (tools/cyberchef/Dockerfile) uses a zip the organizer drops in by hand. Here
# the build fetches one pinned official release from GitHub instead, and
# refuses to continue unless its SHA-256 matches. Static files only: CyberChef
# runs entirely in the player's browser.
FROM nginx:alpine

ARG CC_VERSION=v10.19.4
ARG CC_SHA256=3788b29ffb54f5784968fcf998286f0f75670be8a92e40eb683743ebaab97510

RUN set -eu; \
    apk add --no-cache --virtual .fetch curl unzip; \
    curl -fsSL -o /tmp/cc.zip \
        "https://github.com/gchq/CyberChef/releases/download/${CC_VERSION}/CyberChef_${CC_VERSION}.zip"; \
    echo "${CC_SHA256}  /tmp/cc.zip" | sha256sum -c -; \
    rm -rf /usr/share/nginx/html/*; \
    unzip -q /tmp/cc.zip -d /usr/share/nginx/html; \
    ln -s "CyberChef_${CC_VERSION}.html" /usr/share/nginx/html/index.html; \
    rm -f /tmp/cc.zip; \
    apk del .fetch

EXPOSE 80
