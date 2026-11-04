#!/bin/bash
# player-shell: what ttyd runs for every browser connection.
#
# Isolation between players: this wrapper starts as root (ttyd needs nothing
# else), claims a free seat joueur01..joueur24 (one Unix user per seat, created
# in the Dockerfile), wipes that seat's home /work/joueurNN, then BECOMES that
# user's shell (exec, same PID, so ttyd's hang-up on tab close reaches it).
# Different Unix users means one player cannot read another's files (homes are
# 0700, /work is not listable), kill their processes, plant commands in a
# shared ~/.bashrc or read a shared history. A seat whose shell has ended is
# swept on the next connection: every process of that seat's user is killed
# and its home emptied, before anyone can be handed that seat again.
#
# A small root "reaper" (this same script, `--reap`, in its own session) waits
# for the seat's shell to end, then wipes the seat at once, so nothing a player
# leaves running keeps burning CPU after they close the tab.
#
# The container keeps only CAP_SETUID/SETGID (to switch user), CAP_CHOWN (to
# hand the home over) and CAP_KILL (so ttyd's hang-up reaches the player's
# shell), with no-new-privileges: the player's shell has no capabilities. Each seat is also capped at SEAT_NPROC processes, so a
# fork bomb only stalls its own terminal.
set -u
umask 077

SEATS=24
SEAT_NPROC=64
STATE=/run/toolbox            # tmpfs, root only: seat locks
mkdir -p "$STATE" && chmod 700 "$STATE"

as_seat() { setpriv --reuid="$1" --regid="$1" --clear-groups -- "${@:2}"; }

seat_uid() { id -u "joueur$1"; }

seat_busy() {   # $1 = seat number: is the shell that claimed it still running?
  # /proc, not `kill -0`: with every capability dropped, root may not signal
  # (even probe) another user's process. Owner check also guards PID reuse.
  local pid
  pid="$(cat "$STATE/$1/pid" 2>/dev/null)"
  [ -n "$pid" ] && [ -d "/proc/$pid" ] || return 1
  case "$(stat -c %u "/proc/$pid" 2>/dev/null)" in
    0|"$(seat_uid "$1")") return 0 ;;           # still the wrapper, or its shell
  esac
  return 1
}

wipe_seat() {   # $1 = seat number. Runs as the seat's own user: it can only
                # ever touch that seat's processes and files.
  local u ws
  u="$(seat_uid "$1")"; ws="/work/joueur$1"
  as_seat "$u" /bin/bash -c 'kill -KILL -1' 2>/dev/null
  [ -d "$ws" ] || return 0
  as_seat "$u" /bin/chmod -R u+rwX "$ws" 2>/dev/null
  as_seat "$u" /usr/bin/find "$ws" -mindepth 1 -delete 2>/dev/null
}

release_seat() {   # $1 = seat, $2 = the PID that claimed it
  exec 9>"$STATE/.lock"
  flock 9
  if [ "$(cat "$STATE/$1/pid" 2>/dev/null)" = "$2" ]; then
    wipe_seat "$1"
    rm -rf "$STATE/$1"
  fi
  flock -u 9
  exec 9>&-
}

if [ "${1:-}" = "--reap" ]; then   # --reap SEAT PID (started below, as root)
  trap '' HUP
  sleep 1
  while seat_busy "$2"; do sleep 2; done
  release_seat "$2" "$3"
  exit 0
fi

# ---- sweep finished seats, then claim a free one (under a lock: two tabs
#      opened at once never share a seat)
seat=""
exec 9>"$STATE/.lock"
flock 9
for n in $(seq -w 1 "$SEATS"); do
  [ -d "$STATE/$n" ] || continue
  if ! seat_busy "$n"; then
    wipe_seat "$n"                              # its player left: clean up
    rm -rf "$STATE/$n"
  fi
done
for n in $(seq -w 1 "$SEATS"); do
  if mkdir "$STATE/$n" 2>/dev/null; then
    echo $$ >"$STATE/$n/pid"                    # $$ stays the shell's PID (exec)
    seat="$n"
    break
  fi
done
flock -u 9
exec 9>&-
if [ -z "$seat" ]; then
  echo "Tous les terminaux sont occupés. Réessayez dans un instant."
  sleep 5
  exit 1
fi

user="joueur$seat"
uid="$(seat_uid "$seat")"
ws="/work/$user"
if [ ! -d "$ws" ]; then
  mkdir -m 700 "$ws" && chown "$uid:$uid" "$ws"
fi
wipe_seat "$seat"                               # belt and braces
setsid -f "$0" --reap "$seat" "$$" </dev/null >/dev/null 2>&1

cat <<'BANNER'
──────────────────────────────────────────────
 DÉCAFLOP, boîte à outils de l'équipe
──────────────────────────────────────────────
 Outils installés
   git, git-dumper, binwalk, foremost,
   exiftool, john, hashcat, tshark, unzip,
   xxd, jq, curl, wget, python3

 Les fichiers de preuve sont sur Intranet
 DécaFlop (port 8020) ; les services sur
 l'IP du Pi. curl/wget pour les récupérer :
   wget http://<IP-du-Pi>:<port>/<chemin>
 Pour le partage (login du challenge 01) :
   grab http://<IP>:8020/telecharger/<...>

 Ce terminal est à vous seul : personne
 d'autre ne voit vos fichiers, et tout est
 effacé après la fermeture de l'onglet.

 En ligne (via Cloudflare), ce terminal n'a
 ni internet ni IP du Pi : visez le service
 par son nom interne, port 5000, le même
 que son sous-domaine (site, share, idor,
 sqli, jwt, git, ssti, sapgw), par exemple
   wget http://share:5000/<chemin>
BANNER
echo " Espace de travail : $ws"
echo

# exec: from here on this PID is the player's shell, so closing the tab
# (ttyd sends SIGHUP) ends it, and the next connection sweeps the seat.
ulimit -S -u "$SEAT_NPROC" && ulimit -H -u "$SEAT_NPROC"
cd "$ws"
exec setpriv --reuid="$uid" --regid="$uid" --clear-groups -- /usr/bin/env -i \
  HOME="$ws" USER="$user" LOGNAME="$user" SHELL=/bin/bash \
  TERM="${TERM:-xterm-256color}" LANG=C.UTF-8 TMPDIR="$ws" \
  PATH=/usr/local/bin:/usr/bin:/bin \
  HISTFILE="$ws/.bash_history" \
  /bin/bash --rcfile /etc/toolbox/bashrc -i
