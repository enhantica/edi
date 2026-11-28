#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Undo maintenance_swap.sh (edi ADR-0109), run with the same arguments:
#   maintenance_restore.sh <target> <token> <item> <probe>
# The kept item goes back only when this operation kept it in this same run (the mark beside it, see the swap). A
# later update undoing the operation once it was committed, or any other mismatch, leaves every item alone.
# With a fifth argument, copy, the kept item is the copy maintenance_swap.sh took with copy: it goes back only when
# no usable item is in place, and is dropped otherwise.
# IFW expands variable names between at signs in an operation's arguments, so this file has no at sign.

trap '' HUP INT TERM
# Under the same lock as the swap (see there).
if [ -z "$EDI_MAINTENANCE_LOCKED" ]; then
    [ -n "$1" ] && [ -d "$1" ] || exit 0
    EDI_MAINTENANCE_LOCKED=1
    EDI_MAINTENANCE_TOOL_PID=$PPID
    export EDI_MAINTENANCE_LOCKED EDI_MAINTENANCE_TOOL_PID
    lock="$1/.MaintenanceTool.lock"
    # The tool runs this as the text given to sh -c, with the same text as its name.
    set -- /bin/sh -c "$0" "$0" "$1" "$2" "$3" "$4" "$5"
    if [ -x /usr/bin/lockf ]; then
        /usr/bin/lockf -k -t 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" && exit 0
    elif command -v flock > /dev/null 2>&1; then
        flock -w 60 "$lock" "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" && exit 0
    fi
    exit 1
fi

t="$1"
token="$2"
item="$3"
[ -n "$t" ] && [ -n "$token" ] && [ -n "$item" ] || exit 0
cur="$t/$item"
tool="${EDI_MAINTENANCE_TOOL_PID:-$PPID}"
mark="$token $tool $(TZ=UTC0 LC_ALL=C ps -o lstart= -p "$tool" 2>/dev/null)"
[ -d "$cur.old" ] || exit 0
[ "$(cat "$cur.old-token" 2>/dev/null)" = "$mark" ] || exit 0
if [ "$5" = copy ] && [ -n "$4" ] && [ -f "$cur/$4" ]; then
    rm -f "$cur.old-token" && rm -rf "$cur.old"
    exit
fi
# The item in place leaves it in one rename and is removed only once the kept one is back; if that fails it returns.
rm -rf "$cur.drop" && { [ ! -e "$cur" ] || mv "$cur" "$cur.drop"; } || exit 1
if ! mv "$cur.old" "$cur"; then
    [ -e "$cur" ] || mv "$cur.drop" "$cur" 2>/dev/null
    exit 1
fi
rm -f "$cur.old-token"
rm -rf "$cur.drop" "$cur.new"
# A rolled back update leaves no empty staging folder; its claim goes with the tool component's cleanup.
rmdir "$t/maintenance-update" 2> /dev/null
exit 0
