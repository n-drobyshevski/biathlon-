# Terminal d'équipe — a Linux shell in the browser (ttyd) with the CTF toolkit
# pre-installed, for players on locked-down laptops. Built natively on arm64.
#
# Isolation: runs as a non-root user with NO repository, flags or challenge
# source mounted (nothing to mount is declared in docker-compose.yml). It only
# reaches the challenge services over the LAN. Each browser connection gets its
# own scratch workspace (see shell.sh). Capped in docker-compose.yml.
#
# Every tool a hint or the hub's Outils tile names must exist here:
# tests/test_toolbox_consistency.py checks the names, selftest.sh checks the
# built image (`docker compose run --rm toolbox selftest`).

# --- Stage 1: John the Ripper "jumbo" ---------------------------------------
# Debian's `john` package is the core build: no raw-md5, no HMAC-SHA256 (JWT),
# no zip2john. Jumbo is what every CTF guide assumes, so build it from a pinned
# bleeding-jumbo commit. Takes a while on a Pi 5: do it during prep, online.
FROM debian:bookworm-slim AS john
ARG JOHN_COMMIT=ea6b98c095559785903a10d51c47d90aafcc52c8
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git build-essential pkg-config \
        libssl-dev zlib1g-dev libbz2-dev libgmp-dev \
    && rm -rf /var/lib/apt/lists/*
RUN set -eu; \
    git init -q /opt/src && cd /opt/src; \
    git fetch -q --depth 1 https://github.com/openwall/john.git "${JOHN_COMMIT}"; \
    git checkout -q FETCH_HEAD; \
    cd src; \
    # System-wide mode, like Debian's package: binaries and .conf in /opt/john
    # (read-only), the player's pot and session files in ~/.john.
    ./configure --disable-opencl --with-systemwide \
        CFLAGS="-O2 -DJOHN_SYSTEMWIDE_EXEC='\"/opt/john\"' -DJOHN_SYSTEMWIDE_HOME='\"/opt/john\"'" \
        >/dev/null; \
    make -s clean && make -sj"$(nproc)" >/dev/null; \
    mkdir -p /opt/john && cp -a ../run/. /opt/john/; \
    rm -rf /opt/src

# --- Stage 2: the player toolbox --------------------------------------------
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# CLI toolkit used across the challenges (triage, carving, filesystem forensics,
# exif, pcap, cracking, git, http). Build-time apt/pip/download needs internet,
# do it during prep.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget git python3 python3-pip \
        file binwalk foremost sleuthkit pngcheck libimage-exiftool-perl \
        hashcat pocl-opencl-icd ocl-icd-libopencl1 \
        libssl3 zlib1g libbz2-1.0 libgmp10 libgomp1 \
        tshark binutils \
        unzip xxd jq nano less openssh-client \
    && rm -rf /var/lib/apt/lists/*

# John jumbo from stage 1. john finds its .conf next to the binary; the *2john
# helpers (zip2john, ...) are on PATH too.
COPY --from=john /opt/john /opt/john
RUN set -eu; \
    ln -s /opt/john/john /usr/local/bin/john; \
    for t in zip2john rar2john; do ln -s /opt/john/$t /usr/local/bin/$t; done

# ttyd: static arm64 binary (serves the shell over HTTP).
RUN curl -fsSL -o /usr/local/bin/ttyd \
        https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.aarch64 \
    && chmod +x /usr/local/bin/ttyd

# git-dumper + PyJWT helpers + jwt_tool's own requirements.
RUN pip3 install --no-cache-dir --break-system-packages \
        git-dumper pyjwt requests termcolor cprint pycryptodomex ratelimit

# jwt_tool (not on PyPI): pinned commit, wrapped as a command.
ARG JWT_TOOL_COMMIT=3bc7407cf2222d6a821dcc19c776e5a1b1cb9a9b
RUN set -eu; \
    git init -q /opt/jwt_tool && cd /opt/jwt_tool; \
    git fetch -q --depth 1 https://github.com/ticarpi/jwt_tool.git "${JWT_TOOL_COMMIT}"; \
    git checkout -q FETCH_HEAD && rm -rf .git; \
    printf '#!/bin/sh\nexec python3 /opt/jwt_tool/jwt_tool.py "$@"\n' > /usr/local/bin/jwt_tool; \
    chmod +x /usr/local/bin/jwt_tool

# Non-root player, with a writable /work for per-connection scratch dirs.
RUN useradd -m -s /bin/bash player \
    && mkdir -p /work && chown player:player /work
COPY shell.sh /usr/local/bin/player-shell
COPY grab.sh /usr/local/bin/grab
COPY selftest.sh /usr/local/bin/selftest
RUN chmod +x /usr/local/bin/player-shell /usr/local/bin/grab /usr/local/bin/selftest

USER player
# jwt_tool writes ~/.jwt_tool/jwtconf.ini on its first run and stops there.
# Do that run now, so a player's first command does real work.
RUN jwt_tool >/dev/null 2>&1 || true
WORKDIR /work
EXPOSE 7681

# -W = writable (accept keyboard input). Each client lands in player-shell,
# which hands it a fresh workspace.
CMD ["ttyd", "-p", "7681", "-W", "/usr/local/bin/player-shell"]
