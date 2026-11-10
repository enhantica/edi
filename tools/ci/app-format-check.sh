#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# qmlformat over edi's QML: the formatter changes nothing. `pixi run -e app app-format`
# applies it.
set -euo pipefail
cd "$(dirname "$0")/../.."
qmlformat="${CONDA_PREFIX:?run this in the app pixi environment}/lib/qt6/bin/qmlformat"
if [ "${1:-}" = "--apply" ]; then
    find app/qml -name '*.qml' -print0 | xargs -0 "$qmlformat" -i
    exit 0
fi
unformatted=0
while IFS= read -r file; do
    if ! "$qmlformat" "$file" | diff -q - "$file" > /dev/null; then
        echo "app-format-check: $file is not formatted" >&2
        unformatted=$((unformatted + 1))
    fi
done < <(find app/qml -name '*.qml' | sort)
if [ "$unformatted" -ne 0 ]; then
    echo "app-format-check: $unformatted file(s) differ from qmlformat - run 'pixi run -e app app-format'" >&2
    exit 1
fi
echo "app-format-check: every app/qml file is formatted"
