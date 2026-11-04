#!/usr/bin/env bash
# check-pi.sh — read-only pre-event check of the host the lab runs on.
#
# The players' isolation relies on kernel features Docker can silently drop:
# without the memory cgroup, every mem_limit in docker-compose.yml is ignored
# ("Your kernel does not support memory limit capabilities ... Limitation
# discarded"), so one hashcat run or SSTI payload can eat the whole Pi.
# Raspberry Pi OS ships with that cgroup OFF. This script changes nothing; it
# prints OK / FIX lines with the exact fix. See handouts/HOSTING.md.
set -u
cd "$(dirname "$0")/.."
fail=0
ok()  { printf '  OK   %s\n' "$1"; }
fix() { printf '  FIX  %s\n       -> %s\n' "$1" "$2"; fail=1; }

cmdline=/boot/firmware/cmdline.txt
[ -f "$cmdline" ] || cmdline=/boot/cmdline.txt

echo "Kernel and Docker"
if grep -qw memory /sys/fs/cgroup/cgroup.controllers 2>/dev/null \
   || [ -d /sys/fs/cgroup/memory ]; then
  ok "memory cgroup on (mem_limit is enforced)"
else
  fix "memory cgroup OFF: Docker ignores every mem_limit" \
      "add 'cgroup_enable=memory cgroup_memory=1' to $cmdline (same line), reboot, then: docker compose up -d --force-recreate"
fi
if grep -qw pids /sys/fs/cgroup/cgroup.controllers 2>/dev/null || [ -d /sys/fs/cgroup/pids ]; then
  ok "pids cgroup on (fork bombs are capped)"
else
  fix "pids cgroup OFF: pids_limit is ignored" "update the Pi's kernel (sudo apt full-upgrade), reboot"
fi
if command -v docker >/dev/null; then
  warn="$(docker info 2>&1 | grep -iE 'WARNING: No (memory|swap|cpu|pids)' || true)"
  if [ -z "$warn" ]; then ok "docker info shows no resource-limit warning"
  else fix "docker info: $(echo "$warn" | tr '\n' ' ')" "see the memory cgroup line above"; fi
fi

echo "Terminal (toolbox)"
if [ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null)" = "Y" ]; then
  printf '  NOTE AppArmor is on: players will see each other'"'"'s command lines (hidepid refused)\n'
else
  ok "AppArmor off: players cannot see each other's processes"
fi
if docker compose ps -q toolbox 2>/dev/null | grep -q .; then
  state="$(docker compose exec -T toolbox cat /run/toolbox/hidepid 2>/dev/null)"
  [ "$state" = "oui" ] && ok "toolbox: processes hidden (hidepid on)" \
    || printf '  NOTE toolbox: hidepid=%s (see docker compose logs toolbox)\n' "${state:-?}"
  # Docker stores 0 when it had to discard the limit at creation time
  lim="$(docker inspect -f '{{.HostConfig.Memory}}' "$(docker compose ps -q toolbox)" 2>/dev/null)"
  if [ "${lim:-0}" -gt 0 ] 2>/dev/null; then
    ok "toolbox memory cap applied ($((lim / 1048576)) MB)"
  else
    fix "toolbox has no memory cap (created while the memory cgroup was off)" \
        "after fixing the cgroup: docker compose up -d --force-recreate"
  fi
else
  printf '  NOTE toolbox not running: start the lab, then run this again\n'
fi

echo "Memory"
if [ "$(awk '/SwapTotal/ {print $2}' /proc/meminfo)" -gt 0 ] 2>/dev/null; then
  ok "swap on ($(awk '/SwapTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo))"
else
  fix "no swap" "enable zram (handouts/HOSTING.md, Resource budget)"
fi

[ "$fail" = 0 ] && echo "All good." || echo "Fix the FIX lines, then run this again."
exit "$fail"
