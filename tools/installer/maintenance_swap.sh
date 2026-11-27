#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: put the maintenance tool an update unpacked into maintenancetool/ in place of the installed one (edi ADR-0106).
# Run by the tool component's update operation with the installation folder as $1. Safe to run again after any failure:
# the staged bundle is first renamed to MaintenanceTool.app.new, the installed one is kept as MaintenanceTool.app.old
# (a backup an earlier attempt left is never replaced), and a failure puts the installed bundle back before exiting.
# The backup goes only once the update has succeeded (Installer.qs).
t="$1"
cur="$t/MaintenanceTool.app"
old="$cur.old"
new="$cur.new"
staged="$t/maintenancetool/MaintenanceTool.app"
restore() {
    if [ ! -d "$cur" ] && [ -d "$old" ]; then mv "$old" "$cur"; fi
    exit 1
}
[ -n "$t" ] && [ -d "$t" ] || exit 1
if [ -d "$staged" ]; then
    rm -rf "$new" && mv "$staged" "$new" || restore
fi
# Nothing new to put in place (no staged bundle, and no .new left by an earlier attempt).
[ -d "$new" ] || restore
if [ -d "$old" ]; then
    # An earlier attempt kept the installed bundle already: what is in its place now is not it.
    rm -rf "$cur" || restore
elif [ -d "$cur" ]; then
    mv "$cur" "$old" || restore
fi
mv "$new" "$cur" || restore
rmdir "$t/maintenancetool" 2>/dev/null
exit 0
