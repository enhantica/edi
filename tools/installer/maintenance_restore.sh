#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: undo maintenance_swap.sh, run with the installation folder as $1 and the operation's token as $2. The kept
# bundle goes back only when this operation kept it in this same run (the mark beside it, see the swap). A later
# update undoing the operation once it was committed, or any other mismatch, leaves every bundle alone.
t="$1"
token="$2"
cur="$t/MaintenanceTool.app"
mark="$token $PPID $(LC_ALL=C ps -o lstart= -p "$PPID" 2>/dev/null)"
[ -n "$t" ] && [ -n "$token" ] && [ -d "$cur.old" ] || exit 0
[ "$(cat "$cur.old-token" 2>/dev/null)" = "$mark" ] || exit 0
# The bundle in place leaves it in one rename and is removed only once the kept one is back; if that fails it returns.
rm -rf "$cur.drop" && { [ ! -e "$cur" ] || mv "$cur" "$cur.drop"; } || exit 1
if ! mv "$cur.old" "$cur"; then
    [ -e "$cur" ] || mv "$cur.drop" "$cur" 2>/dev/null
    exit 1
fi
rm -f "$cur.old-token"
rm -rf "$cur.drop" "$cur.new"
