#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: undo maintenance_swap.sh, run with the installation folder as $1 and the operation's token as $2: the kept
# bundle goes back in place, only when this same operation kept it (its token beside it), never a stale one.
t="$1"
token="$2"
cur="$t/MaintenanceTool.app"
rm -rf "$cur.new"
[ -n "$t" ] && [ -n "$token" ] && [ -d "$cur.old" ] || exit 0
[ "$(cat "$cur.old-token" 2>/dev/null)" = "$token" ] || exit 0
rm -rf "$cur" && mv "$cur.old" "$cur" && rm -f "$cur.old-token"
