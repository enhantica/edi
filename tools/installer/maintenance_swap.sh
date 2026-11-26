#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: put the maintenance tool an update unpacked into maintenancetool/ in place of the installed one (edi ADR-0106).
# Run by the tool component's update operation with the installation folder as $1 and that operation's own token as
# $2. Safe to run again after any failure: the staged bundle is first renamed to MaintenanceTool.app.new, the installed
# one is kept as MaintenanceTool.app.old with the token beside it, and a failure puts the installed bundle back before
# exiting. A backup with another token was left by an earlier, finished update (an older control script does not remove
# it) and is stale: it goes before the installed bundle is kept. The control script removes the backup once the update
# has succeeded; maintenance_restore.sh puts back only a backup with its own token.
t="$1"
token="$2"
cur="$t/MaintenanceTool.app"
old="$cur.old"
owner="$cur.old-token"
new="$cur.new"
staged="$t/maintenancetool/MaintenanceTool.app"
restore() {
    if [ ! -d "$cur" ] && [ -d "$old" ] && [ "$(cat "$owner" 2>/dev/null)" = "$token" ]; then mv "$old" "$cur"; fi
    exit 1
}
[ -n "$t" ] && [ -d "$t" ] && [ -n "$token" ] || exit 1
if [ -d "$old" ] && [ "$(cat "$owner" 2>/dev/null)" != "$token" ]; then
    rm -rf "$old" "$owner" || exit 1
fi
if [ -d "$staged" ]; then
    rm -rf "$new" && mv "$staged" "$new" || restore
fi
# Nothing new to put in place (no staged bundle, and no .new left by an earlier attempt).
[ -d "$new" ] || restore
if [ -d "$old" ]; then
    # An earlier attempt of this operation kept the installed bundle already: what is in its place now is not it.
    rm -rf "$cur" || restore
elif [ -d "$cur" ]; then
    printf '%s\n' "$token" > "$owner" && mv "$cur" "$old" || restore
fi
mv "$new" "$cur" || restore
rmdir "$t/maintenancetool" 2>/dev/null
exit 0
