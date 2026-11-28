#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# After a successful update, remove what maintenance_swap.sh kept and the staging folder (edi ADR-0109), run as
#   maintenance_cleanup.sh <target> <item> <probe>
# Only while a usable item is in place: otherwise the backup may be the only copy. With a fourth argument, release, run
# after a rolled back update, it only drops this run's claim on the staging folder and the folder if nothing else is in
# it; whatever the rollback left there, the app removes once this run's tool has exited.
# IFW expands variable names between at signs in its arguments, so this file has no at sign.

trap '' HUP INT TERM
# Under the same lock as the swap (see there), so it never removes a backup an update is still working with.
if [ -z "$EDI_MAINTENANCE_LOCKED" ]; then
    [ -n "$1" ] && [ -d "$1" ] || exit 0
    EDI_MAINTENANCE_LOCKED=1
    EDI_MAINTENANCE_TOOL_PID=$PPID
    export EDI_MAINTENANCE_LOCKED EDI_MAINTENANCE_TOOL_PID
    lock="$1/.MaintenanceTool.lock"
    # The tool runs this as the text given to sh -c, with the same text as its name.
    set -- /bin/sh -c "$0" "$0" "$1" "$2" "$3" "$4"
    if [ -x /usr/bin/lockf ]; then
        /usr/bin/lockf -k -t 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" && exit 0
    elif command -v flock > /dev/null 2>&1; then
        flock -w 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" && exit 0
    fi
    exit 1
fi

t="$1"
item="$2"
probe="$3"
[ -n "$t" ] && [ -n "$item" ] && [ -n "$probe" ] || exit 1
cur="$t/$item"
staging="$t/maintenance-update"
if [ "$4" = release ]; then
    # The claim the swap wrote in this run, read the same way.
    tool="${EDI_MAINTENANCE_TOOL_PID:-$PPID}"
    claim="claim $tool $(TZ=UTC0 LC_ALL=C ps -o lstart= -p "$tool" 2>/dev/null)"
    [ "$(cat "$staging/.claim" 2>/dev/null)" = "$claim" ] && rm -f "$staging/.claim"
    rmdir "$staging" 2> /dev/null
    exit 0
fi
[ -f "$cur/$probe" ] || exit 0
rm -rf "$cur.old" "$cur.old-token" "$cur.copy" "$staging"
# Updates before this release staged into maintenancetool/. On a case-insensitive disk that name is the Linux tool
# itself, so only a real folder goes.
if [ -d "$t/maintenancetool" ] && [ ! -L "$t/maintenancetool" ]; then rm -rf "$t/maintenancetool"; fi
exit 0
