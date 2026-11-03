# ADR-0011: Shared badges and workflow symbols

Date: 2026-10-30
Status: accepted — owner requests consistency across all pages

Use the native tag registry's label, colour role and Font Awesome 5 icon/glyph wherever measurement badges appear. Keep icon-free tags icon-free when the GUI has no symbol. Glossary definitions and explicit short measurement labels use the shared badge renderer; code blocks, filenames and equations retain their original notation. Do not use the abbreviation CLI in user-facing prose; use Command Line.

Present experiment-label meanings as compact two-column tables grouped by purpose, fitting mode and measurement attributes. Keep existing definition anchors for incoming links. Avoid a heading and description that merely repeat one another.

The workflow diagram, stage table, stage links and workflow navigation use the same Material icons declared by ADR-0002. The SVG embeds the actual bundled icon paths rather than approximations or generated artwork. The responsive workflow uses the same component on the User guide entry page and workflow overview. Compact boxes fit the content column on wide screens; phones stack them vertically to keep every stage readable without cropping. The Stage table column sizes to its unbroken icon and name. Broad feature groups use the same stage symbols.

Strict builds validate links. Inspect coloured badges, native glyphs, all definition anchors, workflow stage links and vectors, responsive scrolling, dark/light themes and glossary/catalogue consistency. Renderers must be stable when run repeatedly.

2026-10-31 clarification: named interface links, top navigation and the mobile drawer reuse the existing homepage/feature-table symbols: globe for web, monitor for desktop, Python logo and square terminal for Command Line. Application uses globe and monitor together because it is one application available in both environments. Keep names alongside symbols, hide decorative vectors from assistive technology, and keep icon/text spacing explicit. A shared configuration supplies the interface icon names.

2026-11-01 clarification: table icon labels use separate atomic icon groups and text elements. Keep them beside one another when the cell has room; otherwise move the label below the intact icon group, with explicit horizontal and vertical spacing. Apply this to interface links, workflow stages and native GUI parameter labels. Navigation and prose retain their existing compact layout. This qualifies the unbroken Stage-cell preference above when space is constrained.
