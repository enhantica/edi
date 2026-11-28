#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: put the maintenance tool an update unpacked into maintenancetool/ in place of the installed one (edi ADR-0106).
# Run by the tool component's update operation with the installation folder as $1 and that operation's own token as
# $2. Safe to run again after any failure: the staged bundle is first renamed to MaintenanceTool.app.new, the installed
# one is kept as MaintenanceTool.app.old with a mark beside it, and a failure puts the installed bundle back before
# exiting. The mark is the token and the process running the update (the maintenance tool, with its start time), so
# maintenance_restore.sh puts the bundle back only in the run that kept it: a later update undoing this operation once
# it was committed changes nothing. Any other backup is stale and goes, but only while a usable tool is in place;
# otherwise it is the only copy (an update stopped between the renames) and this operation keeps it as its own.
# The control script removes the backup once the update has succeeded; an older control script leaves it.
t="$1"
token="$2"
cur="$t/MaintenanceTool.app"
old="$cur.old"
owner="$cur.old-token"
new="$cur.new"
staged="$t/maintenancetool/MaintenanceTool.app"
mark="$token $PPID $(LC_ALL=C ps -o lstart= -p "$PPID" 2>/dev/null)"
usable() { [ -f "$1/Contents/MacOS/MaintenanceTool" ]; }
ours() { [ -d "$old" ] && [ "$(cat "$owner" 2>/dev/null)" = "$mark" ]; }
# Whatever is in the tool's place leaves it in one rename, so a removal cut short never leaves part of a bundle there
# that looks like a usable tool.
aside() { rm -rf "$cur.drop" && { [ ! -e "$cur" ] || mv "$cur" "$cur.drop"; }; }
restore() {
    if ! usable "$cur" && ours; then aside && mv "$old" "$cur" && rm -f "$owner"; fi
    exit 1
}
[ -n "$t" ] && [ -d "$t" ] && [ -n "$token" ] || exit 1
if [ -d "$old" ] && ! ours; then
    if usable "$cur"; then
        rm -f "$owner" && rm -rf "$old" || exit 1
    else
        printf '%s\n' "$mark" > "$owner" || exit 1
    fi
fi
if [ -d "$staged" ]; then
    rm -rf "$new" && mv "$staged" "$new" || restore
fi
# Nothing new to put in place (no staged bundle, and no .new left by an earlier attempt).
[ -d "$new" ] || restore
if [ -d "$old" ]; then
    # This operation keeps the installed bundle already: what is in its place now is not it.
    aside || restore
elif [ -d "$cur" ]; then
    printf '%s\n' "$mark" > "$owner" && mv "$cur" "$old" || restore
fi
mv "$new" "$cur" || restore
rm -rf "$cur.drop"
rmdir "$t/maintenancetool" 2>/dev/null
exit 0
