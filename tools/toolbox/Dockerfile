# Terminal d'équipe — a Linux shell in the browser (ttyd) with the CTF toolkit
# pre-installed, for players on locked-down laptops. Built natively on arm64.
#
# Isolation: NO repository, flags or challenge source mounted (nothing to mount
# is declared in docker-compose.yml). It only reaches the challenge services
# over the LAN. Every browser connection gets its OWN Unix user (seat
# joueur01..joueur24) and private home, wiped when the tab closes: see
# shell.sh. ttyd itself runs as root so it can switch to the seat's user, but
# docker-compose.yml drops every capability except SETUID/SETGID/CHOWN/KILL, sets
# no-new-privileges and a read-only root filesystem; the players' shells have
# no capabilities at all.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# CLI toolkit used across the challenges (carving, exif, pcap-strings, cracking,
# git, http). Build-time apt/pip/download needs internet — do it during prep.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget git python3 python3-pip \
        binwalk foremost libimage-exiftool-perl john \
        hashcat pocl-opencl-icd ocl-icd-libopencl1 \
        tshark binutils \
        unzip xxd jq nano less openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ttyd: static binary (serves the shell over HTTP). arm64 on the Pi; the
# x86_64 build is picked automatically when building on an x86 laptop.
ARG TARGETARCH
RUN case "$TARGETARCH" in amd64) a=x86_64 ;; *) a=aarch64 ;; esac \
    && curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.$a" \
    && chmod +x /usr/local/bin/ttyd

# git-dumper (challenge 11) + PyJWT helpers (challenge 10).
RUN pip3 install --no-cache-dir --break-system-packages git-dumper pyjwt requests

# One Unix user per terminal seat (uid 2001..2024), home under /work. /work
# itself is root-owned 0711: players can enter their own home but cannot list
# the others. docker-compose.yml mounts a fresh tmpfs there with the same mode.
RUN for n in $(seq 1 24); do \
        i=$(printf %02d "$n"); id=$((2000 + n)); \
        groupadd -g "$id" "joueur$i" \
        && useradd -M -u "$id" -g "$id" -d "/work/joueur$i" -s /bin/bash "joueur$i" \
        || exit 1; \
    done \
    && mkdir -p /work /etc/toolbox && chmod 0711 /work
COPY shell.sh /usr/local/bin/player-shell
COPY grab.sh /usr/local/bin/grab
COPY bashrc /etc/toolbox/bashrc
RUN chmod 0755 /usr/local/bin/player-shell /usr/local/bin/grab \
    && chmod 0644 /etc/toolbox/bashrc

WORKDIR /work
EXPOSE 7681

# -W = writable (accept keyboard input), -O = refuse WebSockets from another
# origin, -m 20 = at most 20 terminals. Each client lands in player-shell,
# which hands it its own seat. (docker-compose.yml repeats this command.)
CMD ["ttyd", "-p", "7681", "-W", "-O", "-m", "20", "/usr/local/bin/player-shell"]
