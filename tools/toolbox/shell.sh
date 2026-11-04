#!/bin/bash
# player-shell: what ttyd runs for every browser connection (as root), and
# also `toolbox-admin` (organizer commands, same file, see below).
#
# One personal, persistent space per player:
#  - The terminal asks for a pseudo and a password. The first time, the pseudo
#    is created with the password the player chooses; afterwards only that
#    password opens it. A wrong password just says so (no lockout).
#  - Each pseudo is bound for good to one of 24 seats (uid 2001..2024), whose
#    Unix user is NAMED after the pseudo (whoami = pseudo), with a private home
#    /work/<pseudo> (0700, on the toolbox-data volume, so it survives
#    restarts). /work cannot be listed. Unclaimed seats are joueurNN.
#    Other players cannot read the files, kill the processes, or touch the
#    shell setup (root-owned, read-only rcfile) of someone else, and cannot
#    see their processes or command lines either (/proc hidepid, set up by
#    toolbox-init before ttyd starts; root's group still sees everything).
#  - The shell runs inside tmux: closing the tab or losing the Wi-Fi only
#    detaches it. Logging in again from any browser reattaches the same
#    session: same windows, same running programs, same files.
#  - Each player is capped at SEAT_NPROC processes, files of FILE_MB and a
#    home of QUOTA_MB. A watchdog (this script, --watchdog) ends a session
#    whose home keeps growing past the quota or that is stuck at the process
#    cap (fork bomb), so one player cannot fill the Pi's disk or pin its CPU.
#    Ending a session never deletes files.
#
# The container keeps only CAP_SETUID/SETGID (switch user), CAP_CHOWN (hand a
# new home over) and CAP_KILL (ttyd's hang-up, the watchdog), with
# no-new-privileges: the players' shells have no capabilities at all.
set -u
umask 077

SEATS=24
SEAT_NPROC=64
FILE_MB=300
QUOTA_MB=300
HOMES=/work                   # toolbox-data volume
ACCOUNTS=/work/.comptes       # root only: "<seat> <password hash>" per pseudo
STATE=/run/toolbox            # tmpfs, root only: lock, watchdog pid

show_banner() {
cat <<'BANNER'
──────────────────────────────────────────────
 DÉCAFLOP, boîte à outils de l'équipe
──────────────────────────────────────────────
 Outils installés
   git, git-dumper, binwalk, foremost,
   exiftool, john, hashcat, tshark, ffuf,
   unzip, xxd, jq, curl, wget, python3

 Les services sont sur l'IP du Pi.
 curl/wget pour récupérer un fichier :
   wget http://<IP-du-Pi>:<port>/<chemin>
 Pour un partage protégé par mot de passe :
   grab <url-du-fichier> [identifiant]

 Cet espace est à vous seul et il est gardé :
 fermez l'onglet, revenez avec le même pseudo
 et mot de passe : fichiers et programmes
 sont toujours là.
 Molette : défiler. Maj + glisser : copier.

 En ligne (via Cloudflare), ce terminal n'a
 ni internet ni IP du Pi : visez le service
 par son nom interne, port 5000, le même
 que son sous-domaine (site, share, idor,
 sqli, jwt, git, ssti, sapgw), par exemple
   wget http://share:5000/<chemin>
BANNER
}

if [ "${1:-}" = "--banner" ]; then         # from the player's rcfile, as the player
  show_banner
  echo " Joueur : ${PSEUDO:-?}   Espace : $HOME"
  echo
  exit 0
fi

mkdir -p "$STATE" && chmod 700 "$STATE"
mkdir -p "$ACCOUNTS" && chmod 700 "$ACCOUNTS"

as_seat() { setpriv --reuid="$1" --regid="$1" --clear-groups -- "${@:2}"; }
seat_uid() { echo $((2000 + 10#$1)); }      # fixed per seat, whatever its name

# Unix name of a seat = its player's pseudo (joueurNN while unclaimed); home is
# /work/<name>. /etc/passwd and /etc/group are symlinks (see the Dockerfile) to
# files rebuilt by sync_users from the image's system accounts + the seats.
seat_name() {
  local f
  for f in "$ACCOUNTS"/*; do
    case "$f" in *.new) continue ;; esac
    [ -f "$f" ] && [ "$(cut -d' ' -f1 "$f")" = "$1" ] && { basename "$f"; return 0; }
  done
  echo "joueur$1"
}
seat_home() { echo "$HOMES/$(seat_name "$1")"; }
ETC=/work/.etc
sync_users() {   # rewrite passwd/group (call under lock, or before ttyd starts)
  local n name uid
  mkdir -p "$ETC" && chmod 755 "$ETC"
  cp /etc/toolbox/passwd.base "$ETC/passwd.new"
  cp /etc/toolbox/group.base "$ETC/group.new"
  for n in $(seq -w 1 "$SEATS"); do
    name="$(seat_name "$n")"; uid="$(seat_uid "$n")"
    echo "$name:x:$uid:$uid:$name:$HOMES/$name:/bin/bash" >>"$ETC/passwd.new"
    echo "$name:x:$uid:" >>"$ETC/group.new"
  done
  chmod 644 "$ETC/passwd.new" "$ETC/group.new"
  mv "$ETC/passwd.new" "$ETC/passwd" && mv "$ETC/group.new" "$ETC/group"
}
reserved_name() {  # system account/group names, numbers, and joueurNN are not pseudos
  case "$1" in *[!0-9]*) ;; *) return 0 ;; esac
  case "$1" in joueur[0-9]*) return 0 ;; esac
  cut -d: -f1 /etc/toolbox/passwd.base /etc/toolbox/group.base | grep -qxF -- "$1"
}
seat_procs() {   # number of processes of uid $1 (one fork, not one per process)
  find /proc -mindepth 1 -maxdepth 1 -name '[0-9]*' -uid "$1" 2>/dev/null | wc -l
}
end_session() {  # kill every process of seat $1 (its tmux too); files are kept
  as_seat "$(seat_uid "$1")" /bin/bash -c 'kill -KILL -1' 2>/dev/null
}
home_mb() {      # disk use of seat $1's home, in MB (measured as that user)
  as_seat "$(seat_uid "$1")" /usr/bin/du -sm "$(seat_home "$1")" 2>/dev/null | cut -f1
}

# Passwords: scrypt, read on stdin (never on a command line, so never visible
# in /proc), compared in constant time.
pw_hash() {
  python3 -I -c 'import hashlib,os,sys
p=sys.stdin.buffer.read(); s=os.urandom(16)
print("scrypt$"+s.hex()+"$"+hashlib.scrypt(p,salt=s,n=2**14,r=8,p=1).hex())'
}
pw_check() {     # $1 = stored hash, password on stdin
  STORED="$1" python3 -I -c 'import hashlib,hmac,os,sys
_,s,h=os.environ["STORED"].split("$")
d=hashlib.scrypt(sys.stdin.buffer.read(),salt=bytes.fromhex(s),n=2**14,r=8,p=1).hex()
sys.exit(0 if hmac.compare_digest(d,h) else 1)'
}

account_seat() { cut -d' ' -f1 "$ACCOUNTS/$1" 2>/dev/null; }
account_hash() { cut -d' ' -f2 -s "$ACCOUNTS/$1" 2>/dev/null; }

lock()   { exec 9>"$STATE/.lock"; flock 9; }
unlock() { flock -u 9; exec 9>&-; }

new_seat() {     # first seat no pseudo owns yet (call under lock)
  local n used
  used=" $(cat "$ACCOUNTS"/* 2>/dev/null | cut -d' ' -f1 | tr '\n' ' ') "
  for n in $(seq -w 1 "$SEATS"); do
    case "$used" in *" $n "*) ;; *) echo "$n"; return 0 ;; esac
  done
  return 1
}

ensure_home() {  # $1 = seat
  local ws u
  ws="$(seat_home "$1")"; u="$(seat_uid "$1")"
  if [ ! -d "$ws" ]; then
    mkdir -m 700 "$ws" && chown "$u:$u" "$ws"
  fi
}

wipe_dir() {     # $1 = seat, $2 = a directory of that seat: empty it, as that user
  local u
  u="$(seat_uid "$1")"
  as_seat "$u" /bin/chmod -R u+rwX "$2" 2>/dev/null
  as_seat "$u" /usr/bin/find "$2" -mindepth 1 -delete 2>/dev/null
}
wipe_home() { wipe_dir "$1" "$(seat_home "$1")"; }

# ---------------------------------------------------------------- users
# At container start (toolbox-init, before ttyd): rename homes from the old
# /work/joueurNN layout to /work/<pseudo>, then write passwd/group.
if [ "${1:-}" = "--sync-users" ]; then
  for f in "$ACCOUNTS"/*; do
    [ -f "$f" ] || continue
    case "$f" in *.new) continue ;; esac
    s="$(cut -d' ' -f1 "$f")"; new="$HOMES/$(basename "$f")"
    if [ -d "$HOMES/joueur$s" ] && [ ! -e "$new" ]; then mv "$HOMES/joueur$s" "$new"; fi
  done
  sync_users
  exit 0
fi

# ---------------------------------------------------------------- watchdog
if [ "${1:-}" = "--watchdog" ]; then
  trap '' HUP
  echo $$ >"$STATE/watchdog.pid"
  declare -A last_mb=() stuck=()
  while sleep 5; do
    for f in "$ACCOUNTS"/*; do
      [ -f "$f" ] || continue
      seat="$(cut -d' ' -f1 "$f")"; uid="$(seat_uid "$seat")" || continue
      procs="$(seat_procs "$uid")"
      if [ "$procs" -eq 0 ]; then stuck[$seat]=0; continue; fi
      # stuck at the process cap twice in a row: a fork bomb, end it
      if [ "$procs" -ge $((SEAT_NPROC - 2)) ]; then
        stuck[$seat]=$(( ${stuck[$seat]:-0} + 1 ))
        if [ "${stuck[$seat]}" -ge 2 ]; then end_session "$seat"; stuck[$seat]=0; fi
        continue
      fi
      stuck[$seat]=0
      # over the quota AND still growing: end the session (files are kept,
      # the player logs back in and deletes what they don't need)
      mb="$(home_mb "$seat")"; [ -n "$mb" ] || continue
      if [ "$mb" -gt "$QUOTA_MB" ] && [ "$mb" -gt "${last_mb[$seat]:-0}" ]; then
        end_session "$seat"
      fi
      last_mb[$seat]="$mb"
    done
  done
  exit 0
fi

start_watchdog() {
  local pid i
  lock
  pid="$(cat "$STATE/watchdog.pid" 2>/dev/null)"
  if [ -z "$pid" ] || ! grep -qa -- '--watchdog' "/proc/$pid/cmdline" 2>/dev/null; then
    rm -f "$STATE/watchdog.pid"
    setsid -f "$0" --watchdog </dev/null >/dev/null 2>&1
    for i in 1 2 3 4 5 6 7 8 9 10; do
      [ -s "$STATE/watchdog.pid" ] && break
      sleep 0.1
    done
  fi
  unlock
}

# ---------------------------------------------------------------- organizer
# docker compose exec toolbox toolbox-admin liste | mdp <pseudo> | supprimer <pseudo>
if [ "$(basename "$0")" = "toolbox-admin" ]; then
  cmd="${1:-}"; who="${2:-}"
  case "$cmd" in
    liste)
      echo "Processus des autres joueurs cachés (hidepid) : $(cat "$STATE/hidepid" 2>/dev/null || echo '?')"
      printf '%-24s %-5s %8s  %s\n' PSEUDO UID ESPACE PROCESSUS
      for f in "$ACCOUNTS"/*; do
        [ -f "$f" ] || continue
        s="$(account_seat "$(basename "$f")")"
        printf '%-24s %-5s %6sMo  %s\n' "$(basename "$f")" "$(seat_uid "$s")" \
          "$(home_mb "$s")" "$(seat_procs "$(seat_uid "$s")")"
      done ;;
    mdp)
      [ -f "$ACCOUNTS/$who" ] || { echo "Pseudo inconnu : $who"; exit 1; }
      lock; account_seat "$who" >"$ACCOUNTS/$who.new" && mv "$ACCOUNTS/$who.new" "$ACCOUNTS/$who"; unlock
      echo "Mot de passe de $who effacé : il en choisira un nouveau à sa prochaine connexion (fichiers gardés)." ;;
    supprimer)
      [ -f "$ACCOUNTS/$who" ] || { echo "Pseudo inconnu : $who"; exit 1; }
      s="$(account_seat "$who")"
      lock
      end_session "$s"
      wipe_home "$s"
      rmdir "$(seat_home "$s")" 2>/dev/null
      rm -f "$ACCOUNTS/$who"
      sync_users                                 # the seat is joueurNN again
      unlock
      echo "Compte $who supprimé, son espace est vidé." ;;
    *)
      echo "usage: toolbox-admin liste | mdp <pseudo> | supprimer <pseudo>"; exit 1 ;;
  esac
  exit 0
fi

# ---------------------------------------------------------------- login
start_watchdog
cat <<'EOF'
──────────────────────────────────────────────
 DÉCAFLOP, terminal d'équipe : connexion
──────────────────────────────────────────────
 Prenez le même pseudo que sur le tableau des
 scores. Première fois : le pseudo est créé
 avec le mot de passe que vous choisissez.

EOF
seat=""
while [ -z "$seat" ]; do
  read -rp " Pseudo : " pseudo || exit 0
  pseudo="$(printf '%s' "$pseudo" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  if ! printf '%s' "$pseudo" | grep -qE '^[a-z0-9][a-z0-9_.-]{1,23}$'; then
    echo " 2 à 24 caractères : lettres, chiffres, . _ -"
    continue
  fi
  if [ ! -f "$ACCOUNTS/$pseudo" ] && reserved_name "$pseudo"; then
    echo " Ce nom est réservé au système. Choisissez-en un autre."
    continue
  fi
  stored="$(account_hash "$pseudo")"
  if [ -n "$stored" ]; then                      # existing pseudo: check password
    read -rsp " Mot de passe : " pw || exit 0; echo
    if printf '%s' "$pw" | pw_check "$stored"; then
      seat="$(account_seat "$pseudo")"
    else
      echo " Mot de passe incorrect."
      sleep 1
    fi
    continue
  fi
  if [ -f "$ACCOUNTS/$pseudo" ]; then            # reset by the organizer
    echo " Mot de passe réinitialisé par l'organisateur : choisissez-en un."
  else
    echo " Nouveau pseudo « $pseudo » : choisissez un mot de passe"
    echo " (6 caractères minimum). Notez-le : lui seul rouvre cet espace."
  fi
  read -rsp " Mot de passe : " pw || exit 0; echo
  read -rsp " Encore une fois : " pw2 || exit 0; echo
  if [ "${#pw}" -lt 6 ]; then echo " Trop court."; continue; fi
  if [ "$pw" != "$pw2" ]; then echo " Les deux saisies diffèrent."; continue; fi
  hash="$(printf '%s' "$pw" | pw_hash)"
  lock
  if [ -n "$(account_hash "$pseudo")" ]; then
    unlock; echo " Ce pseudo vient d'être pris. Choisissez-en un autre."; continue
  fi
  s="$(account_seat "$pseudo")"
  if [ -z "$s" ] && ! s="$(new_seat)"; then
    unlock; echo " Plus de place sur ce terminal, prévenez l'organisateur."; sleep 5; exit 1
  fi
  if [ ! -f "$ACCOUNTS/$pseudo" ] && [ -d "$HOMES/joueur$s" ]; then
    wipe_dir "$s" "$HOMES/joueur$s"              # leftovers of an unclaimed seat
    rmdir "$HOMES/joueur$s" 2>/dev/null
  fi
  new_account=0; [ -f "$ACCOUNTS/$pseudo" ] || new_account=1
  echo "$s $hash" >"$ACCOUNTS/$pseudo.new" && mv "$ACCOUNTS/$pseudo.new" "$ACCOUNTS/$pseudo"
  [ "$new_account" = 1 ] && sync_users           # the seat's Unix name is now the pseudo
  unlock
  seat="$s"
done
unset pw pw2 stored hash

user="$pseudo"                                   # Unix name = pseudo (see sync_users)
uid="$(seat_uid "$seat")"
ws="$HOMES/$user"
ensure_home "$seat"
sock="$ws/.tmux-session"

# a session stuck at the process cap (fork bomb) cannot be reattached: restart it
if [ "$(seat_procs "$uid")" -ge $((SEAT_NPROC - 2)) ]; then
  echo " Votre session était saturée : elle redémarre (fichiers gardés)."
  end_session "$seat"
elif as_seat "$uid" /usr/bin/tmux -S "$sock" has-session 2>/dev/null; then
  read -rp " Session retrouvée. [Entrée] la reprendre, [n] en ouvrir une neuve : " again || exit 0
  case "$again" in n|N) end_session "$seat" ;; esac
fi
mb="$(home_mb "$seat")"
if [ -n "$mb" ] && [ "$mb" -gt "$QUOTA_MB" ]; then
  echo " Attention : votre espace dépasse ${QUOTA_MB} Mo (${mb} Mo)."
  echo " Supprimez des fichiers, sinon la session sera fermée s'il grossit encore."
  sleep 3
fi

# exec: from here on this PID is the player's tmux client, so ttyd's hang-up
# (tab closed, Wi-Fi lost) only detaches it; the tmux server keeps running.
ulimit -S -u "$SEAT_NPROC" && ulimit -H -u "$SEAT_NPROC"
ulimit -S -f $((FILE_MB * 1024)) && ulimit -H -f $((FILE_MB * 1024))
cd "$ws"
exec setpriv --reuid="$uid" --regid="$uid" --clear-groups -- /usr/bin/env -i \
  HOME="$ws" USER="$user" LOGNAME="$user" SHELL=/bin/bash PSEUDO="$pseudo" \
  TERM="${TERM:-xterm-256color}" LANG=C.UTF-8 TMPDIR="$ws" \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  HISTFILE="$ws/.bash_history" \
  /usr/bin/tmux -u -f /etc/toolbox/tmux.conf -S "$sock" new-session -A -s jeu
