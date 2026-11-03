#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail
cd "$(dirname "$0")/../.."
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 OUTPUT [--docs-script FILE]" >&2
    exit 2
fi
docs_app=${EDI_DOCS_APP:-$PWD/build/app/app/edi_app}
if [ ! -x "$docs_app" ]; then
    echo "Build edi_app first, or set EDI_DOCS_APP to its executable" >&2
    exit 2
fi
export EDI_CAPTURE_WIDTH=1480 EDI_CAPTURE_HEIGHT=800
source tools/ci/app-platform.sh
app_capture_platform docs-capture
"$docs_app" --docs-capture "$@"
