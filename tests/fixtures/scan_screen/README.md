# Scan patterns on a screen

This producer adds passive receipts to the committed application host. It loads
`Main` from the production QML module, opens the bundled cooling scan, and uses
the real Analysis pattern chart. Desktop observations use the normal OpenGL
capture platform; browser observations use Qt's multithread kit in the pinned
headless Chromium. No replacement fit worker or chart is used.

A receipt records the series seen at scene synchronization and the subsequent
frame swap. Dataset identity comes from independently saved measured columns,
using the existing scan fixture's documented axis and uncertainty conversions.
The worker receipt records actual completed files before their GUI delivery.
Calculated series hashes witness changes; they are observations, not numerical
correctness references or golden values.

The Extras control is found through its four displayed options. The observer
activates its actual QML handler. Each mode has a fresh private machine settings
store; a second host invocation saves the choice, and a third reads it after a
restart. Browser runs reload the same origin in one isolated context, and use a
fresh context for each machine.

Adaptive mode temporarily shows Evolution, then returns to Pattern while the
worker is running. The first resumed pattern must reach at least the newest
completed file at release. Every-pattern mode must draw each file in order;
about-once-per-second mode must have at least one live drawing and at least one
second between successive live drawings; only-at-the-end mode draws only the
final file after completion. All modes must settle on the final file.

Run the system module with `pixi run python -m pytest
 tests/system/py/test_scan_screen.py`. Desktop uses the delivered normal
`build/app/app/edi_app`; receipt preparation does not compile it. It must carry
the canonical `edi-build-commit:<full sha>\n` marker produced by
`cmake/build_commit.cmake` with `MARKER` and `MARK_DIRTY` enabled. The marker
must identify clean checkout HEAD. Missing, stale, dirty, conflicting identities
and uncommitted source inputs are refused. Receipt hashes cannot replace that
binary witness; cached and supplied receipts recheck it before and after capture.

The browser builds privately from `git archive <source_sha>` using the linked
published SDK and matching Git source. Uncommitted working-tree changes are
excluded. `source-policy.json` and the receipt's `source_policy` explicitly name
that revision and exclusion; fixture instrumentation is recorded separately.
To reuse qualified builds, set
`EDI_SCAN_SCREEN_DESKTOP_RECEIPT` and `EDI_SCAN_SCREEN_BROWSER_RECEIPT` to their
`receipt.json` files. Receipts bind production source and executable bytes.
