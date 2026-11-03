# Terminal d'équipe — a Linux shell in the browser (ttyd) with the CTF toolkit
# pre-installed, for players on locked-down laptops. Built natively on arm64.
#
# Isolation: runs as a non-root user with NO repository, flags or challenge
# source mounted (nothing to mount is declared in docker-compose.yml). It only
# reaches the challenge services over the LAN. Each browser connection gets its
# own scratch workspace (see shell.sh). Capped in docker-compose.yml.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# CLI toolkit used across the challenges (carving, exif, pcap-strings, cracking,
# git, http). Build-time apt/pip/download needs internet — do it during prep.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget git python3 python3-pip \
        binwalk foremost libimage-exiftool-perl john \
        tshark binutils \
        unzip xxd jq nano less openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ttyd: static arm64 binary (serves the shell over HTTP).
RUN curl -fsSL -o /usr/local/bin/ttyd \
        https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.aarch64 \
    && chmod +x /usr/local/bin/ttyd

# git-dumper (challenge 11) + PyJWT helpers (challenge 10).
RUN pip3 install --no-cache-dir --break-system-packages git-dumper pyjwt requests

# Non-root player, with a writable /work for per-connection scratch dirs.
RUN useradd -m -s /bin/bash player \
    && mkdir -p /work && chown player:player /work
COPY shell.sh /usr/local/bin/player-shell
RUN chmod +x /usr/local/bin/player-shell

USER player
WORKDIR /work
EXPOSE 7681

# -W = writable (accept keyboard input). Each client lands in player-shell,
# which hands it a fresh workspace.
CMD ["ttyd", "-p", "7681", "-W", "/usr/local/bin/player-shell"]
