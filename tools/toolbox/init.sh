#!/bin/sh
# toolbox-init: container entrypoint, runs once as root before ttyd.
#
# Hides every player's processes (and so their command lines) from the other
# players: /proc is remounted with hidepid=invisible, so a user only sees
# their own processes. gid=0 keeps them visible to root's group, i.e. the
# login wrapper, the watchdog and `toolbox-admin`, which must count them.
#
# Remounting needs CAP_SYS_ADMIN. docker-compose.yml grants it (plus
# CAP_SETPCAP) for this step only: both are then removed from the bounding
# set, so ttyd, the wrappers and every player's shell can never use them.
# If the remount is refused, the terminal still works, the command lines are
# just visible, and the log and `toolbox-admin liste` say so. That happens on
# hosts whose Docker applies its default AppArmor profile, which forbids
# mounts (check on the Pi: cat /sys/module/apparmor/parameters/enabled).
# The AppArmor profile is deliberately kept, so the hiding is skipped there.
mkdir -p /run/toolbox && chmod 700 /run/toolbox
if mount -o remount,hidepid=invisible,gid=0 /proc 2>/dev/null \
   || mount -o remount,hidepid=2,gid=0 /proc 2>/dev/null; then
  echo "oui" >/run/toolbox/hidepid
  echo "toolbox-init: /proc hidepid on, players only see their own processes"
else
  echo "non" >/run/toolbox/hidepid
  echo "toolbox-init: WARNING could not remount /proc with hidepid; players can see" \
       "each other's command lines (see handouts/HOSTING.md)" >&2
fi
# players' Unix names = their pseudos: write /etc/passwd + /etc/group (on the
# volume) before anything looks a user up
/usr/local/bin/player-shell --sync-users
exec setpriv --bounding-set=-sys_admin,-setpcap -- "$@"
