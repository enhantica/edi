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
 tests/system/py/test_scan_screen.py`. Builds are private and use the linked
published SDK and its matching Git source. To reuse qualified builds, set
`EDI_SCAN_SCREEN_DESKTOP_RECEIPT` and `EDI_SCAN_SCREEN_BROWSER_RECEIPT` to their
`receipt.json` files. Receipts bind production source and executable bytes.
