# Finder disk image spacing

`finder-tab-bar.json` records edges measured in the November 27, 2026 Finder
capture of the 26.17 installer, supplied with the report about the short bottom
padding. Finder's tab bar was visible. Coordinates are pixel rows in the
original 1024 × 780 capture. The window was 800 pixels wide for a 400-point
view. Bottom edges are exclusive.

The central window strip gives its top and bottom edges. The transition from
tab bar to artwork at the right gives the content top. Dark central text
gives the instruction's first row and Finder label's last row. The installer
icon's midpoint is measured across its top and bottom edges. The two margins
in that capture are 36 points above the instruction and 14 below the label.

The offline gate uses the observed Finder chrome and icon-to-label distance,
then measures the instruction against the actual background at each pixel
density and the window settings passed to dmgbuild. To measure a fresh Finder
capture directly, pass its visible artwork rectangle in image pixels to:

```sh
python -m tests.fixtures.installer.disk_image.measure screen.png X Y WIDTH HEIGHT
```

Set the top of the rectangle to the first artwork row below the tab bar and
the bottom to the end of the Finder window. The measurement accepts two points
of difference for pixel rounding at the text edges.
