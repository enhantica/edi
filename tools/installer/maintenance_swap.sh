#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Put the item an update unpacked into maintenance-update/ in place of the installed one (edi ADR-0109): the macOS
# Maintenance Tool bundle, or the Linux tool's Qt runtime. Run by the tool component's operation as
#   maintenance_swap.sh <target> <token> <item> <probe>
# where <item> is the folder's name in the installation folder <target>, <token> the operation's own mark and <probe>
# a file inside the item that shows it is usable. Safe to run again after any failure: the staged item is first
# renamed to <item>.new, the installed one is kept as <item>.old with a mark beside it, and a failure puts the
# installed item back before exiting. The mark is the token and the maintenance tool's process with its start time,
# so maintenance_restore.sh puts the item back only in the run that kept it: a later update undoing this operation
# once it was committed changes nothing. Any other backup is stale and goes, but only while a usable item is in place;
# otherwise it is the only copy (an update stopped between the renames) and this operation keeps it as its own.
# maintenance_cleanup.sh removes the backup once the update has succeeded.
# With a fifth argument, claim, it only marks the staging folder as this run's before the update unpacks into it, so the
# app leaves the folder alone while this run's tool lives (edi ADR-0109).
# With a fifth argument, copy, it only keeps a copy of the usable item as the backup with the same mark and puts
# nothing new in place. The first Linux update off a release whose app component carried the runtime runs it before
# the Framework undoes that component; maintenance_restore.sh with copy settles it afterwards.
# IFW expands variable names between at signs in an operation's arguments, so this file has no at sign.

# A closing terminal must not stop the renames half way.
trap '' HUP INT TERM
# Everything below runs under the lock the app and the other scripts take too, so the app never restores a backup
# while an update is between two renames. The lock belongs to this process tree, not to the maintenance tool, so it
# holds even when the tool is force quit, and the kernel drops it when the tree is gone.
if [ -z "$EDI_MAINTENANCE_LOCKED" ]; then
    [ -n "$1" ] && [ -d "$1" ] || exit 1
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
probe="$4"
[ -n "$t" ] && [ -d "$t" ] && [ -n "$token" ] && [ -n "$item" ] && [ -n "$probe" ] || exit 1
cur="$t/$item"
old="$cur.old"
owner="$cur.old-token"
new="$cur.new"
staging="$t/maintenance-update"
claim="$staging/.claim"
staged="$staging/$item"
# The tool's start time in UTC, read the same way as the undo reads it, so the undo of this run matches whatever
# time zone either runs in.
tool="${EDI_MAINTENANCE_TOOL_PID:-$PPID}"
started="$(TZ=UTC0 LC_ALL=C ps -o lstart= -p "$tool" 2>/dev/null)"
mark="$token $tool $started"
usable() { [ -f "$1/$probe" ]; }
ours() { [ -d "$old" ] && [ "$(cat "$owner" 2>/dev/null)" = "$mark" ]; }
# Whatever is in the item's place leaves it in one rename, so a removal cut short never leaves part of an item there
# that looks usable.
aside() { rm -rf "$cur.drop" && { [ ! -e "$cur" ] || mv "$cur" "$cur.drop"; }; }
# On failure IFW rolls back and its undo of the unpacking cannot remove the staging folder the staged item has left.
restore() {
    if ! usable "$cur" && ours; then aside && mv "$old" "$cur" && rm -f "$owner"; fi
    rmdir "$staging" 2> /dev/null
    exit 1
}
if [ "$5" = claim ]; then
    # Complete before it gets its name, so the app never reads half a claim.
    mkdir -p "$staging" && printf 'claim %s\n' "$tool $started" > "$claim.new" && mv "$claim.new" "$claim" || exit 1
    exit 0
fi
if [ -d "$old" ] && ! ours; then
    if usable "$cur"; then
        rm -f "$owner" && rm -rf "$old" || exit 1
    else
        printf '%s\n' "$mark" > "$owner" || exit 1
    fi
fi
if [ "$5" = copy ]; then
    # Hard links where cp makes them (GNU), else a plain copy: either survives the undo deleting the item's files.
    # The copy gets its final name only once complete and marked.
    if ! ours && usable "$cur"; then
        rm -rf "$cur.copy" || exit 1
        cp -al "$cur" "$cur.copy" 2> /dev/null || { rm -rf "$cur.copy" && cp -pR "$cur" "$cur.copy"; } || exit 1
        printf '%s\n' "$mark" > "$owner" && mv "$cur.copy" "$old" || exit 1
    fi
    exit 0
fi
if [ -d "$staged" ]; then
    rm -rf "$new" && mv "$staged" "$new" || restore
fi
# Nothing new to put in place (no staged item, and no .new left by an earlier attempt).
[ -d "$new" ] || restore
if [ -d "$old" ]; then
    # This operation keeps the installed item already: what is in its place now is not it.
    aside || restore
elif [ -d "$cur" ]; then
    printf '%s\n' "$mark" > "$owner" && mv "$cur" "$old" || restore
fi
# A first installation has nothing to keep: the staged item just moves in.
mv "$new" "$cur" || restore
# The staged item has left the staging folder; anything still in it (a Finder .DS_Store, say) is debris.
rm -rf "$cur.drop" "$staging"
exit 0
