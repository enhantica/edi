#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# macOS: undo maintenance_swap.sh, run with the installation folder as $1: the kept bundle goes back in place.
t="$1"
cur="$t/MaintenanceTool.app"
[ -n "$t" ] && [ -d "$cur.old" ] || exit 0
rm -rf "$cur" && mv "$cur.old" "$cur"
status=$?
rm -rf "$cur.new"
exit $status
