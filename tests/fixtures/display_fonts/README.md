These cmap ranges come from the bundled font files, independently read by FreeType,
not from the app's display-glyph checker. `generate.py` is the only writer. The
SHA-256 of each face binds its ranges to the font bytes; the pinned archive hash
binds the base faces when core-only CI has not fetched the app resources. A font
or archive change requires regenerating this reference after app configuration.

A zero glyph index is missing, even when a platform can find a replacement. See
[FreeType's character mapping reference](https://freetype.org/freetype2/docs/reference/ft2-character_mapping.html).
Runtime Qt gates additionally check the fonts actually used by shaping, including
fallbacks, against the packaged resources. These references make no claim about
arbitrary user-supplied Unicode or characters from external translations.

Each face's weight comes from the font's OS/2 `usWeightClass`, using the
[OpenType table specification](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#usweightclass).
The coverage gate matches both this weight and the nonzero glyph mapping; the Qt
witness also compares the face actually selected by shaping.
