# ADR-0010: Native category icons across the reference and category guides

Date: 2026-10-30
Status: accepted — owner requests reuse of the GUI category symbols

The parameter reference already exported native category icons but displayed them only as part of numeric parameter labels. Category captions and reference headings had no symbol; broad workflow symbols were also repeated on specific category guides.

Render the category symbol beside every category caption in all four naming projections and beside category headings in the detailed reference, including their TOC entries. Category-specific application guides and their left-navigation entries use the same symbol. Broad workflow groups retain ADR-0002's Material icons. Keep visible text, stable anchors and the native parameter icon patterns.

Use the existing exported dictionary `icon` and Font Awesome 5 glyph/font assets. No separately chosen icon mapping or icon artwork is introduced. The reference renderer owns the explicit page-to-category associations and regenerates heading/navigation metadata after a fresh capture import. Fail if a declared native icon lacks a glyph. Icons are decorative to assistive technology; text names the category.

Validate generated references, stable links, actual font loading, correct symbols in all naming tabs and both navigation areas, and readable alignment at phone/desktop widths in both themes.

2026-10-31 clarification: navigation icons inherit their adjacent label colour with no independent fading, including hover and active states. Apply the same rule to SVG symbols and native Font Awesome glyphs.
