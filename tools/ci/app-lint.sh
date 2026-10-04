#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# The app's lint gate (gate 2):
#   1. qmllint over edi's QML, resolved against the modules app-build generated (build/app/qml) — the
#      base's modules and edi.app with its registered types. It fails on qmllint's exit status (a fatal
#      error, an unreadable file, a crash) as well as on any warning line; neither alone is enough.
#      The base's own QML is not linted: edi builds it unmodified and does not own its findings.
#   2. One change signal per property: every property that is not CONSTANT notifies (a NOTIFY signal, or
#      a Qt bindable property), and no NOTIFY signal serves two Q_PROPERTYs of one class, those it
#      inherits included, so an edit re-evaluates only the bindings of the property that changed (the
#      owner's per-property rule, I3). It reads moc's record of every class the app build processed (the
#      metatypes JSON that qt_add_qml_module generates), never the C++ source: moc has already applied
#      the declaration grammar, so no spelling of a declaration escapes it (
#      conductor breaker decision d7d6b297d). An absent, unreadable or empty record fails. The
#      notify-or-bindable rule is this check's last extension: it completes the breaker's
#      conversion, and the check reads nothing but moc's record.
set -euo pipefail
cd "$(dirname "$0")/../.."
qmllint="${EDI_APP_QMLLINT:-${CONDA_PREFIX:?run this in the app pixi environment}/lib/qt6/bin/qmllint}"
if [ ! -d build/app/qml/edi/app ]; then
    echo "app-lint: build/app/qml has no edi.app module - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
mapfile -t files < <(find app/qml -name '*.qml' | sort)
log=build/app/app-lint.log
status=0
"$qmllint" -I build/app/qml "${files[@]}" > "$log" 2>&1 || status=$?
warnings=$(grep -c '^Warning' "$log" || true)
if [ "$status" -ne 0 ] || [ "$warnings" -ne 0 ]; then
    cat "$log" >&2
    echo "app-lint: qmllint exited $status with $warnings warning line(s) over app/qml" >&2
    exit 1
fi
# The module's own record (a multi-config build adds a configuration suffix); the plugin's is another target's.
shopt -s nullglob
metatypes=(build/app/app/meta_types/qt6edi_app_module_metatypes.json build/app/app/meta_types/qt6edi_app_module_*_metatypes.json)
shopt -u nullglob
if [ "${#metatypes[@]}" -ne 1 ] || [ ! -s "${metatypes[0]}" ]; then
    echo "app-lint: expected one non-empty metatypes record of edi_app_module under build/app/app/meta_types, found: ${metatypes[*]} - run 'pixi run -e app app-build' first" >&2
    exit 1
fi
notify=$(python3 - "${metatypes[0]}" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as record:
        classes = {c["qualifiedClassName"]: c for f in json.load(record) for c in f.get("classes", [])}
except (OSError, ValueError, KeyError, TypeError) as error:
    sys.exit(f"app-lint: cannot read {path} ({error!r}) - the NOTIFY check read nothing")
if not any(c.get("properties") for c in classes.values()):
    sys.exit(f"app-lint: {path} records no property - the NOTIFY check read nothing")


def properties(name, seen=()):
    """A class's properties by name, those it inherits from a class moc processed first, its own last."""
    if name not in classes or name in seen:
        return {}
    found = {}
    for base in classes[name].get("superClasses", []):
        found.update(properties(base.get("fullyQualifiedName", base["name"]), seen + (name,)))
    found.update({p["name"]: p.get("notify") for p in classes[name].get("properties", [])})
    return found


silent = [
    f"{name}::{p['name']}"
    for name, c in sorted(classes.items())
    for p in c.get("properties", [])
    if not p.get("constant") and not p.get("notify") and not p.get("bindable")
]
if silent:
    sys.exit("app-lint: properties that can change but notify nothing (neither NOTIFY nor BINDABLE): " + " ".join(silent))
shared = []
for name in sorted(classes):
    signals = [s for s in properties(name).values() if s]
    shared += [f"{name}::{s}" for s in sorted({s for s in signals if signals.count(s) > 1})]
if shared:
    sys.exit("app-lint: NOTIFY signals serving more than one property (one signal per property): " + " ".join(shared))
count = sum(len(c.get("properties", [])) for c in classes.values())
print(f"{count} properties in {len(classes)} classes, from moc's metatypes; each non-constant one notifies")
PY
)
echo "app-lint: ${#files[@]} QML file(s), qmllint exit 0 and no warnings; one NOTIFY signal per property ($notify)"
