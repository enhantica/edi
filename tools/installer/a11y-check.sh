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
reports="$HOME/Library/Logs/DiagnosticReports"
mkdir -p "$reports"
before="$(ls "$reports" 2>/dev/null | sort)"

# The client needs the accessibility permission; without it there is nothing to check.
if ! osascript -e 'tell application "System Events" to get name of UI elements of process "Finder"' >/dev/null 2>"$logs/permission.txt"; then
  echo "a11y-check: the accessibility client is not permitted on this machine:"
  cat "$logs/permission.txt"
  exit 3
fi

target="$(mktemp -d)/EasyDiffraction"
"$binary" --script "$(cd "$(dirname "$0")" && pwd)/a11y_walk.qs" A11yTarget="$target" --verbose >"$logs/installer.log" 2>&1 &
pid=$!

# The client: every half second, every UI element of the installer's windows and its selected children.
client() {
  while kill -0 "$pid" 2>/dev/null; do
    osascript >>"$logs/client.log" 2>&1 <<EOF
tell application "System Events"
  if exists process "$process" then
    tell process "$process"
      repeat with w in windows
        repeat with e in (entire contents of w)
          try
            get value of attribute "AXSelectedChildren" of e
          end try
        end repeat
      end repeat
    end tell
  end if
end tell
EOF
    sleep 0.5
  done
}
client &
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
sleep 3  # the crash reporter writes its report after the process ends

new="$(comm -13 <(echo "$before") <(ls "$reports" 2>/dev/null | sort) | grep -i "$process" || true)"
for report in $new; do cp "$reports/$report" "$logs/"; done
echo "a11y-check: installer exit $status after ${waited}s; new crash reports: ${new:-none}"
if [ -n "$new" ] || [ "$status" -ge 128 ]; then
  for report in $new; do grep -m5 -E 'QMacAccessibilityElement|Exception Type' "$reports/$report" || true; done
  exit 1
fi
exit 0
