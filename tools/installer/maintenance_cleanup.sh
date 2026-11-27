#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# After a successful update, remove what maintenance_swap.sh kept and the staging folder (edi ADR-0108), run as
#   maintenance_cleanup.sh <target> <item> <probe>
# Only while a usable item is in place: otherwise the backup may be the only copy.
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
    set -- /bin/sh -c "$0" "$0" "$1" "$2" "$3"
    if [ -x /usr/bin/lockf ]; then
        /usr/bin/lockf -k -t 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" && exit 0
    elif command -v flock > /dev/null 2>&1; then
        flock -w 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" && exit 0
    fi
    exit 1
fi

t="$1"
item="$2"
probe="$3"
[ -n "$t" ] && [ -n "$item" ] && [ -n "$probe" ] || exit 1
cur="$t/$item"
[ -f "$cur/$probe" ] || exit 0
rm -rf "$cur.old" "$cur.old-token" "$cur.copy" "$t/maintenancetool"
