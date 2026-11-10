# ADR-0007: Visible, scrollable equations across browsers

Date: 2026-10-30
Status: implemented

The existing Physics pages use MathJax SVG and Zensical's native arithmatex styling. On mobile WebKit, the theme's min-content child width and generic SVG percentage maximum form a cyclic intrinsic-size constraint. The display SVG collapses to its one-pixel minimum while its surrounding block retains vertical space. Inline maths stays visible.

Keep MathJax, its scientific content and native text size. Override only the display-layout seam: the arithmatex block owns horizontal scrolling; its MathJax child has intrinsic max-content width and at least the available width; SVGs keep their natural width rather than a percentage maximum. Short equations remain centred and long equations scroll. Version the stylesheet URL for existing browser caches.

The prior all-page check only required generated SVG markup. It now also refuses invisible display dimensions. `checks/math_browser.py` checks visible dimensions, scrolling and page overflow across desktop/mobile, light/dark, Chromium/WebKit. Its WebKit control disables the fix to reproduce the original collapse, then restores it and requires visible equations. Linux WebKit is a browser-engine regression check, not a claim of testing a physical iPhone.
