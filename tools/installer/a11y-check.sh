#!/usr/bin/env bash
# Runs a macOS installer through its pages while an accessibility client reads every window, as VoiceOver and other
# assistive tools do, and fails when the installer crashes. Usage: a11y-check.sh <installer .app> <log folder>
set -uo pipefail
app="$1"
logs="$2"
mkdir -p "$logs"
binary="$(find "$app/Contents/MacOS" -maxdepth 1 -type f -perm -u+x | head -1)"
[ -n "$binary" ] || { echo "a11y-check: no executable in $app"; exit 2; }
process="$(basename "$binary")"
marker="$logs/.started"
touch "$marker"

here="$(cd "$(dirname "$0")" && pwd)"
# The client, compiled once: it asks each element for several attributes in one call, selected children among them.
swiftc -O -o "$logs/a11y-client" "$here/a11y_client.swift" || { echo "a11y-check: the client did not compile"; exit 2; }

target="$(mktemp -d)/EasyDiffraction"
"$binary" --script "$here/a11y_walk.qs" A11yTarget="$target" --verbose >"$logs/installer.log" 2>&1 &
pid=$!
sleep 2

"$logs/a11y-client" "$pid" >"$logs/client.log" 2>&1 &
reader=$!

waited=0
while kill -0 "$pid" 2>/dev/null && [ "$waited" -lt 300 ]; do sleep 1; waited=$((waited + 1)); done
if kill -0 "$pid" 2>/dev/null; then
  echo "a11y-check: the installer did not finish its walk in 300 s"
  kill "$pid" 2>/dev/null
  status=124
else
  wait "$pid"; status=$?
fi
kill "$reader" 2>/dev/null
if grep -q "not permitted" "$logs/client.log"; then
  echo "a11y-check: the accessibility client is not permitted on this machine (grant it once in System Settings)"
  exit 3
fi
# The crash reporter writes its report a little after the process ends, in the user's or the system's folder.
new=""
if [ "$status" -ge 128 ]; then
  for _ in $(seq 60); do
    new="$(find "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports -newer "$marker" -type f \
      2>/dev/null | xargs grep -l "$process" 2>/dev/null || true)"
    [ -n "$new" ] && break
    sleep 1
  done
fi
for report in $new; do cp "$report" "$logs/"; done
echo "a11y-check: installer exit $status after ${waited}s; crash reports: ${new:-none}"
if [ -n "$new" ] || [ "$status" -ge 128 ]; then
  for report in $new; do grep -m8 -E 'QMacAccessibility|Exception Type|Crashed|_AXXMIG' "$report" || true; done
  exit 1
fi
exit 0
