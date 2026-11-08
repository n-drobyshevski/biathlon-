# Terminal d'équipe — a Linux shell in the browser (ttyd) with the CTF toolkit
# pre-installed, for players on locked-down laptops. Built natively on arm64.
#
# Isolation: NO repository, flags or challenge source mounted. It only reaches
# the challenge services over the LAN. Every player logs in with a pseudo and
# password and gets their OWN Unix user (named after the pseudo) with a private,
# persistent home and a tmux session that survives a closed tab or lost
# Wi-Fi: see shell.sh. ttyd itself runs as root so it can switch to the
# player's user, but docker-compose.yml drops every capability except
# SETUID/SETGID/CHOWN/KILL (SYS_ADMIN/SETPCAP too, but only for toolbox-init,
# which drops them before ttyd starts), sets no-new-privileges and a read-only
# root filesystem; the players' shells have no capabilities at all.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# CLI toolkit used across the challenges (carving, exif, pcap-strings, cracking,
# git, http). Build-time apt/pip/download needs internet — do it during prep.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget git python3 python3-pip \
        binwalk foremost libimage-exiftool-perl john \
        hashcat pocl-opencl-icd ocl-icd-libopencl1 \
        tshark binutils \
        unzip xxd jq nano less openssh-client tmux \
    && rm -rf /var/lib/apt/lists/*

# ttyd: static binary (serves the shell over HTTP). arm64 on the Pi; the
# x86_64 build is picked automatically when building on an x86 laptop.
ARG TARGETARCH
RUN case "$TARGETARCH" in amd64) a=x86_64 ;; *) a=aarch64 ;; esac \
    && curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.$a" \
    && chmod +x /usr/local/bin/ttyd

# ffuf: web fuzzer (IDOR id-walk on 04, directory/parameter recon). Single Go
# binary; ffuf's release arch names match Docker's TARGETARCH (amd64/arm64).
RUN case "$TARGETARCH" in amd64) a=amd64 ;; *) a=arm64 ;; esac \
    && curl -fsSL "https://github.com/ffuf/ffuf/releases/download/v2.1.0/ffuf_2.1.0_linux_$a.tar.gz" \
        | tar -xz -C /usr/local/bin ffuf \
    && chmod +x /usr/local/bin/ffuf

# git-dumper (challenge 11) + PyJWT helpers (challenge 10).
RUN pip3 install --no-cache-dir --break-system-packages git-dumper pyjwt requests

# One Unix user per player (uid 2001..2024) whose NAME is the player's pseudo,
# home /work/<pseudo>. /work itself is root-owned 0711: players can enter their
# own home but cannot list the others. docker-compose.yml mounts the
# toolbox-data volume there (a new volume starts as a copy of this empty, 0711
# directory).
RUN mkdir -p /work /etc/toolbox && chmod 0711 /work
COPY shell.sh /usr/local/bin/player-shell
COPY grab.sh /usr/local/bin/grab
COPY bashrc tmux.conf /etc/toolbox/
COPY init.sh /usr/local/bin/toolbox-init
RUN chmod 0755 /usr/local/bin/player-shell /usr/local/bin/grab /usr/local/bin/toolbox-init \
    && ln -s player-shell /usr/local/bin/toolbox-admin \
    && chmod 0644 /etc/toolbox/bashrc /etc/toolbox/tmux.conf

# Players' Unix names follow their pseudos, so passwd/group are rebuilt at run
# time (read-only image): the system accounts are kept here as a base, and
# /etc/passwd + /etc/group point to the copies toolbox-init / player-shell
# write on the volume (/work/.etc, world-readable like any /etc/passwd).
# Keep this the LAST step that needs user names at build time.
RUN cp /etc/passwd /etc/toolbox/passwd.base && cp /etc/group /etc/toolbox/group.base \
    && ln -sf /work/.etc/passwd /etc/passwd && ln -sf /work/.etc/group /etc/group

# Curated wordlists for john / hashcat (challenges 09 and 10): short on purpose, so a
# crack finishes in seconds on the Pi. World-readable; root-owned so players cannot edit them.
COPY wordlists/sap_default.txt wordlists/jwt_secrets.txt /usr/share/wordlists/
RUN chmod 644 /usr/share/wordlists/sap_default.txt /usr/share/wordlists/jwt_secrets.txt

WORKDIR /work
EXPOSE 7681

# -W = writable (accept keyboard input), -O = refuse WebSockets from another
# origin, -m 20 = at most 20 terminals. Each client lands in player-shell,
# which logs the player in. (docker-compose.yml repeats this command.)
# toolbox-init runs first: it hides each player's processes from the others
# (/proc hidepid), then drops the capabilities that needed, and starts ttyd.
ENTRYPOINT ["/usr/local/bin/toolbox-init"]
CMD ["ttyd", "-p", "7681", "-W", "-O", "-m", "20", "/usr/local/bin/player-shell"]
