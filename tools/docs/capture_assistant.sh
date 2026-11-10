#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Capture the Application's AI assistant tutorial (tools/docs/assistant_tutorial.js) into OUTPUT, in
# THEME (light or dark). Needs a ChatGPT sign-in the app can reuse and the network. The two input
# files are the collection's onboarding pair, fetched fresh.
set -euo pipefail
cd "$(dirname "$0")/../.."
output=${1:?usage: capture_assistant.sh OUTPUT [light|dark]}
theme=${2:-light}
inputs=/tmp/edi-assistant-tutorial
mkdir -p "$inputs"
base=https://raw.githubusercontent.com/enhantica/edi-data/main
curl -fsS -o "$inputs/tutorial-lbco.cif" "$base/structures/tutorial-lbco.cif"
curl -fsS -o "$inputs/tutorial-hrpt.xye" "$base/data/tutorial-hrpt.xye"
script=$(mktemp --suffix=.js)
sed "s/\"theme:light\"/\"theme:$theme\"/" tools/docs/assistant_tutorial.js > "$script"
bash tools/docs/capture-gui.sh "$output" --docs-script "$script"
