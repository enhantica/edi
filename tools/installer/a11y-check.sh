#!/usr/bin/env bash
# Runs a macOS installer through its pages while an accessibility client reads every window, as VoiceOver and other
# assistive tools do, and fails when the installer crashes. Usage: a11y-check.sh <installer .app> <log folder>
# [installer argument ...]: more arguments for the installer, such as A11yHideComponents=true. With --own-script the
# installer keeps its own control script and walks itself in its capture mode (Installer.qs), installing into a
# temporary folder: the check then covers what users get, not a replacement script. A maintenance tool walks the mode
# EDI_INSTALLER_MAINTENANCE_MODE names (add, update or remove). Any tree view the client meets fails the check too:
# the component tree is what crashed (edi #150), so none may show.
set -uo pipefail
app="$1"
logs="$2"
shift 2
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
own=0
if [ "${1:-}" = "--own-script" ]; then
  own=1
  shift
  mkdir -p "$logs/pages"
  where=(TargetDir="$target")
  case "$process" in MaintenanceTool*) where=() ;; esac
  # macOS bash 3.2 counts an empty array as unset under set -u, hence the +-form.
  EDI_INSTALLER_CAPTURE="$logs/pages" "$binary" ${where[@]+"${where[@]}"} "$@" --verbose >"$logs/installer.log" 2>&1 &
else
  "$binary" --script "$here/a11y_walk.qs" A11yTarget="$target" "$@" --verbose >"$logs/installer.log" 2>&1 &
fi
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
# The reader stops by itself once the installer is gone and prints its counts; it is killed only if it hangs.
for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$reader" 2>/dev/null || break; sleep 1; done
kill "$reader" 2>/dev/null
if grep -q "not permitted" "$logs/client.log"; then
  echo "a11y-check: the accessibility client is not permitted on this machine (grant it once in System Settings)"
  exit 3
fi
# The crash reporter writes its report a little after the process ends, in the user's or the system's folder.
# Searched after every exit, not only a signal: a crash can end in an ordinary exit status too.
new=""
for _ in $(seq "$([ "$status" -ge 128 ] && echo 60 || echo 5)"); do
  new="$(find "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports -newer "$marker" -type f \
    2>/dev/null | xargs grep -l "$process" 2>/dev/null || true)"
  [ -n "$new" ] && break
  sleep 1
done
for report in $new; do cp "$report" "$logs/"; done
trees="$(grep -c "AXOutline" "$logs/client.log" 2>/dev/null || true)"
trees="${trees:-0}"
echo "a11y-check: installer exit $status after ${waited}s; crash reports: ${new:-none}; tree views read: $trees"
# A walk proves something only when it finished and was read: the installer succeeded (the product's own walk ends
# with 0; the replacement walk script cancels at the last page, 3), the reader completed queries, and every page
# named in A11Y_EXPECT_PAGES was captured.
failed=0
# A maintenance tool that updated itself restarts and is closed by the walk (3); its Finished page must be captured.
expected_status=$([ "$own" = 1 ] && echo "${A11Y_EXPECT_STATUS:-0}" || echo "0 3")
case " $expected_status " in *" $status "*) ;; *) echo "a11y-check: the installer ended with $status"; failed=1 ;; esac
reads="$(sed -n 's/^a11y-client: \([0-9]*\) multiple-attribute queries$/\1/p' "$logs/client.log")"
if [ "${reads:-0}" -eq 0 ]; then echo "a11y-check: the reader completed no queries"; failed=1; fi
for page in ${A11Y_EXPECT_PAGES//,/ }; do
  if ! ls "$logs/pages/"*"-$page-"*.png >/dev/null 2>&1; then echo "a11y-check: page $page was not reached"; failed=1; fi
done
if grep -q "^layout-pages: 0$" "$logs/client.log"; then echo "a11y-check: no page was laid out to check"; failed=1; fi
if grep -q "edi resource missing" "$logs/installer.log"; then
  grep "edi resource missing" "$logs/installer.log"
  echo "a11y-check: the installer lacks one of its own resources"
  exit 1
fi
if [ "$trees" -gt 0 ] && [ "${A11Y_ALLOW_TREE:-}" != 1 ]; then
  echo "a11y-check: a tree view is on a page"
  exit 1
fi
# The layout rules the client checks on every page it reads (a11y_client.swift): one left edge, gaps on the spacing
# scale, no clipped text, no frame mostly empty.
if grep -q "^layout:" "$logs/client.log"; then
  grep "^layout:" "$logs/client.log"
  echo "a11y-check: a page breaks the layout rules"
  layout_failed=1
fi
if [ -n "$new" ] || [ "$status" -ge 128 ]; then
  for report in $new; do grep -m8 -E 'QMacAccessibility|Exception Type|Crashed|_AXXMIG' "$report" || true; done
  exit 1
fi
[ "$failed" = 1 ] && exit 1
exit "${layout_failed:-0}"
