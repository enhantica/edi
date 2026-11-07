# ADR-0017: Dark-theme application screenshots

Date: 2026-11-07
Status: accepted

## Prior art

Application screenshots were captured only in the light theme, so a dark documentation page showed bright images. ADR-0001 draws highlights over a captured image, using geometry from its capture.

## Decision

Each capture script runs twice, changing only `theme:light` to `theme:dark`, from one app binary. The dark run's images go to `assets/gui/<bundle>/dark/`, with `hashes.json`. Highlights keep using the light bundle's geometry, because both themes lay out the same controls.

A figure carries the dark image's hash in `data-gui-dark`. `gui-capture.js` swaps the image and enlarge-link address when the documentation theme changes, and the browser loads only the image it shows. Without scripts, the light image is shown.

`_check_dark` in `build.py` requires a dark image for every captured scene and refuses one that changed after import.

## Limits

The homepage hero and the interface previews on the entry pages come from separate captures and stay light for now.
