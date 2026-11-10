#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The web app carries no AI assistant (ADR-0068 §web build; the owner, 2026-11-04): a linked kit must hold none of the
# assistant's code, QML or resources. Run after wasm-build on one kit's app folder:
#   tools/ci/wasm-assistant-check.sh build/wasm/multithread/app
# Looks for the assistant's own names in the linked edi_app.wasm, edi_app.js and any .data file: C++ symbols and
# type names (codex_agent, AssistantViewModel, …), the QML components (AssistantPanel.qml, …) and the resource
# prefixes (/edi/assistant/). A hit names the file and the marker. Exit 1 on any hit, 2 when the kit is not built.
set -euo pipefail
app_dir=${1:?the kit app build folder, e.g. build/wasm/multithread/app}
wasm=$(find "$app_dir" -maxdepth 2 -name edi_app.wasm | head -1)
if [ -z "$wasm" ]; then
    echo "wasm-assistant-check: no edi_app.wasm under $app_dir" >&2
    exit 2
fi
dir=$(dirname "$wasm")
markers=(codex_agent CodexAgent AssistantViewModel AssistantWorkReport AssistantHistory assistant_skill_import
         AssistantPanel.qml AssistantWorking.qml AssistantMessage.qml AssistantComposer.qml AssistantPlan.qml
         AssistantQuestion.qml AssistantTrial.qml AssistantSkillsDialog.qml AssistantConnectionDialog.qml
         /edi/assistant/ AssistantWorking.svg AssistantSpinner.svg)
hits=0
for file in "$wasm" "$dir"/edi_app.js "$dir"/*.data; do
    [ -f "$file" ] || continue
    for marker in "${markers[@]}"; do
        if grep -q -a -F -- "$marker" "$file"; then
            echo "wasm-assistant-check: ${file##*/} holds $marker" >&2
            hits=$((hits + 1))
        fi
    done
done
if [ "$hits" -gt 0 ]; then
    echo "wasm-assistant-check: $hits assistant marker(s) in the web kit at $dir" >&2
    exit 1
fi
echo "wasm-assistant-check: no assistant code, QML or resources in $(basename "$dir")/edi_app.wasm ($(stat -c %s "$wasm") bytes)"
