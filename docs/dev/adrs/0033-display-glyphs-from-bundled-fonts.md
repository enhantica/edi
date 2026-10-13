# Display glyphs from bundled fonts

Status: Accepted

## Context

The app bundles its fonts so text looks the same on every platform (ADR-0015 §10): PT Sans and
PT Mono for text, Noto Sans and Noto Sans Mono substituted behind them for the characters they
lack, and Font Awesome 5 Solid for icons. When the font drawing a character has no glyph for it,
Qt searches the platform's fonts. On macOS that search goes through FreeType and logs "Failed to
create FreeType font engine" once per face it tries, and the glyph it finds differs from one
platform to the next.

Three places reached the platform this way. The Wyckoff position list showed thirds, sixths and
eighths, which PT Sans does not have. The legends drew their marks as box-drawing characters and a
black circle, which no bundled font in the PT Sans chain has. And the parameter table measured its
free column's arrow with a `TextMetrics` whose font named only the icon family, so Qt resolved a
face without the glyph and went looking for it, although the arrow itself drew correctly.

## Decision

1. Every character the app displays exists in the bundled font that draws it, at the face it is
   drawn with. No text depends on a platform font. A list or label that needs a character its
   default font lacks names a bundled font that has it; the Wyckoff list is drawn in Noto Sans.
2. Legend marks are never characters of a text font. A pattern series' mark is a drawn line in
   the series' colour and width, and a structure's Bragg ticks are a drawn vertical line; the
   legend model carries the shape (`line` or `tick`) and the width, and `IconLine` draws it, so
   the marks look the same on desktop and on the web. The structure view's legend shows each
   element with the atom icon the Atom sites table shows, in the element's colour for the
   selected scheme.
3. A text or font metrics object that measures an icon copies its font from the item that draws
   the icon (`font: arrow.font`), never builds one from the family name alone.

## Consequences

`tools/checks/display_glyphs.py` reads the string literals of the app and the core, works out
which bundled font draws each non-ASCII character, reads the fonts' character maps and records
the result, with the weight of the drawing face, in `data/display-glyphs.json`. Its `--check`
fails when a character is new or gone, when one is in no bundled font of the chain that draws it,
or when a metrics object measures an icon in a font of its own. A site drawn in another font
than PT Sans is named in the tool. The app's display-font tests (`test_display_fonts`,
`test_bundled_display_fonts`) gate these rules.

A new character in a displayed string needs either a bundled font that has it or a new census
entry naming the font that draws it, and a new legend mark needs a shape, not a glyph.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| Keep the legend glyphs and draw them in Noto Sans Mono | Rejected: that font's black circle is much smaller than the dot drawn before, and the marks would still depend on font metrics |
| A drawn filled circle for each element | Replaced by the atom icon, so the legend matches the Atom sites table |
| Bundle a symbol font for the legend marks | Rejected: another font to load for four marks that are simpler as shapes |
| Accept the platform fallback | Rejected: the glyphs differ by platform and macOS logs a warning for each face tried |
