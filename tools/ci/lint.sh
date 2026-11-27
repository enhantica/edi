#!/usr/bin/env bash
# The CI lint job's checks (.github/workflows/ci.yml), so a local run and CI agree. Every check runs and
# reports even when an earlier one fails; the exit status is 1 if any failed.
# Usage: lint.sh [style|policy]   (no argument: both, as `pixi run lint` and the pre-push hook run them)
set -u
style=(check format-check entity-path-check)
policy=(weakref-policy tutorial-exclusions tutorial-code notebook-outputs wheel-packages report-pattern-panes
        generated-regions category-census-check)
case "${1:-all}" in
    style) tasks=("${style[@]}") ;;
    policy) tasks=("${policy[@]}") ;;
    all) tasks=("${style[@]}" "${policy[@]}") ;;
    *) echo "usage: lint.sh [style|policy]" >&2; exit 2 ;;
esac
status=0
failed=()
# What CI may store and print of crysta's source, read from the workflows with any Python that has PyYAML.
if [ "${1:-all}" != style ]; then
    if ! python3 tools/ci/portable_paths.py; then
        status=1
        failed+=(portable-paths)
    fi
    with=(python3)
    python3 -c 'import yaml' 2>/dev/null || with=(pixi run python)
    if ! "${with[@]}" tools/ci/source_publishers.py; then
        status=1
        failed+=(source-publishers)
    fi
    # The workflows take the app key from edi's own secret, EDI_APP_KEY. An older branch must not bring
    # back the organisation secret's name.
    if grep -rn ENHANTICA_APP_KEY .github; then
        echo "lint: use secrets.EDI_APP_KEY, not ENHANTICA_APP_KEY" >&2
        status=1
        failed+=(app-key-name)
    fi
fi
for task in "${tasks[@]}"; do
    if ! pixi run "$task"; then
        status=1
        failed+=("$task")
    fi
done
if ((status)); then
    echo "lint: failed: ${failed[*]}" >&2
fi
exit $status
