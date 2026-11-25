#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Call every assistant tool in the app without a model (tools/dev/assistant_peer.py), each with all sidebar groups
# folded first, and report each call. The shipped app holds none of this; a developer's own target does. Usage, in the
# app environment after app-build:
#   cmake --build build/app --target edi_app_assistant_demo -j 4
#   tools/dev/assistant-tools.sh lbco|scan|spoiled on|off OUTPUT
# on and off: Show actions. The LBCO run starts with no project and takes the two files from the edi-data collection
# (build/edi-data); the scan run opens docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f. spoiled: the controls of some steps
# are covered, absent, disabled or hold their click back. EDI_ASSISTANT_INACTIVE=1 leaves the window inactive, as it is
# in the background, and =first until a project is open: each step shown meanwhile must be done without showing.
set -euo pipefail
cd "$(dirname "$0")/../.."
project=${1:?lbco or scan} show=${2:?on or off} output=${3:?the output folder}
app=${EDI_APP:-build/app/app/edi_app_assistant_demo}
collection=${EDI_LOCAL_COLLECTION:-$PWD/build/edi-data}
rm -rf "$output"
# The app's own data folder exists, as after a first start: files are attached before the connection makes it.
mkdir -p "$output/settings/EasyDiffraction/EasyDiffraction" "$output/documents"
output=$(cd "$output" && pwd)
export EDI_ASSISTANT_SPOILED=$([ "$project" = spoiled ] && echo 1 || echo 0)
echo "XDG_DOCUMENTS_DIR=\"$output/documents\"" >"$output/settings/user-dirs.dirs"
export XDG_CONFIG_HOME="$output/settings" XDG_DATA_HOME="$output/settings"
export EDI_ASSISTANT_PEER_DIR="$output" EDI_CODEX_DEVELOPMENT_EXECUTABLE="$PWD/tools/dev/assistant_peer.py"
export EDI_ASSISTANT_SHOW=$([ "$show" = on ] && echo 1 || echo 0) EDI_ASSISTANT_PROJECT="" EDI_ASSISTANT_FILES=""
export EDI_ASSISTANT_INACTIVE=${EDI_ASSISTANT_INACTIVE:-}
if [ "$project" = scan ]; then
    EDI_ASSISTANT_PROJECT=pd-neut-cwl_cosio-d20_scan-3f
else
    mkdir "$output/inputs"
    cp "$collection/structures/tutorial-lbco.cif" "$output/inputs/lbco.cif"
    cp "$collection/data/tutorial-hrpt.xye" "$output/inputs/hrpt.xye"
    EDI_ASSISTANT_FILES="$output/inputs/lbco.cif|$output/inputs/hrpt.xye"
fi
export QT_LOGGING_RULES="${QT_LOGGING_RULES:-}"
source tools/ci/app-platform.sh
EDI_CAPTURE_WIDTH=1480 EDI_CAPTURE_HEIGHT=800 app_capture_platform assistant-tools
code=0
timeout "${EDI_ASSISTANT_RUN_LIMIT:-2400}" "$app" >"$output/app.log" 2>&1 || code=$?
python tools/dev/assistant_report.py "$output" "$show" "$code"
