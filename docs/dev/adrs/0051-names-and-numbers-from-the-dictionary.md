# 0051. Every name and number on screen comes from crysta's dictionary

- **Status:** Accepted
- **Date:** 2026-10-24
- **Implementation:** 🟡 Partially implemented — labels, tooltips, selector values, input fields, the slider, the
  Analysis table, the data and reflection tables, the agreement factors and the CLI scan summary read the dictionary;
  a number with no dictionary item keeps the app's own rule
- **Priority:** High
- **Forward constraint (binding on new features):** a label, selector value or number of a `.edi` item on any surface
  comes through the display bridge (`core/include/edi/display.hpp`). `tools/checks/display_sources.py` refuses a
  copied name or a rounding of its own, and an exception names its file, its text and the reason in
  `data/display-format-exceptions.json`.

## Context

edi named items from four places of its own: the hand-copied parameter specs of [ADR-0010](0010-parameter-metadata-and-vocabulary.md),
QML literals, an app table of group titles and icons, and nothing at all for selector values, so file tokens such as
`it1992` reached the screen. Numbers went through a stopgap that kept six significant digits everywhere, while
intensities, cell lengths and displacement parameters need different roundings (owner, 2026-09-28).

crysta's dictionary now holds every `.edi` item and category: a short display name, units, a description, a display
format for each numeric item, the options of each selector with their names, and a title and icon for each category.
crysta's SDK exposes it through its public C++ API. The owner asked for one source of names (2026-09-29), for labels
that follow the `.edi` categories with the `.edi` name in a tooltip (2026-10-12), and for input fields that show a
value as the file and the Text tab spell it (2026-10-24).

## Decision

1. **One bridge.** `core/include/edi/display.hpp` is the only place edi asks for a name or a number to show: an
   item's label, units, description and tooltip, a selector's options and their names, a category's title and icon,
   and a value as text. It is a thin layer over crysta and keeps no table. The app reaches it through `Session`
   (`label`, `units`, `tooltip`, `optionLabel`, `categoryTitle`, `written`, `display`) and through the parameter items.
2. **The parameter specs keep only their identity.** A spec keeps its category, name, units code, range and name lists;
   its display name, units, description and LaTeX come from the dictionary. `category_title.cpp`,
   `parameter_symbol.cpp` and the label functions in `selectors.cpp` are gone. This amends ADR-0010.
3. **Labels and tooltips.** A table header, a field title and a group title show the item's display name, and a
   header or field names the item in its tooltip (`WP: _atom_site.wyckoff_letter`). A selector's tooltip names the
   item and the stored token, and its values show their dictionary names. A displacement column takes the name of the
   site's type (`U₁₁`, `B iso`). The titles, icons and field names [ADR-0017](0017-app-gui-design.md) §3, §5, §8 and
   §21 chose are now dictionary values, not app code.
4. **What a number shows.**
   1. An input field, an editable cell, the slider and the Analysis table show the value exactly as a project save
      writes it under the project's s.u. rule, the s.u. in its own column, so they read as the Text tab does. A field
      left as it was writes nothing.
   2. A read-only table, a readout, the report and the CLI show a value the space group fixes as its exact fraction, a
      value with an s.u. as `value(su)` by the project's rule, and any other value in its item's display format. The
      report and its CIF always use the IUCr rule. These are the rules of
      [ADR-0037](0037-exact-fractions-and-constrained-values-on-screen.md), except that a constrained value without an
      s.u. takes its own item's format (amending its §2).
   3. A number with no dictionary item (a duration, a chart tick, a computed phase fraction) keeps the app's own rule,
      and a value too wide for its cell still shows in scientific notation (owner, 2026-10-22).
   4. The report's Data table keeps one number of decimals for every row of an intensity column, chosen from the
      largest measured value, with no exponent (owner, 2026-10-13); its axis column, like the reflections table, takes
      its item's fixed format.
5. **A check keeps it so.** `tools/checks/display_sources.py` reads the app, the core and the Python library and
   fails on a rounding primitive outside the bridge, on a literal that copies a dictionary name, and on an exception
   that no longer matches anything. It reads the dictionary from crysta's source (the pinned fetch, or
   `CRYSTA_CONSUMER_SRC`). This amends [ADR-0015](0015-edi-app-stack.md): the app's surfaces consume the bridge.

## Consequences

A name or a rounding is changed once, in crysta's dictionary, and every surface follows: the app, the CLI, the report
and Python. A field shows the same text as the file, so editing never starts from a rounded value. Some visible text
changes with this: selector values read as names (`X-ray`, not `xray`), the measured range's step is labelled `step`,
and the chart's measured axis reads `TOF` where it read `time-of-flight`.

The app now depends on the dictionary carried by the pinned SDK: a label exists only once crysta ships it. The
exception list must stay short and reasoned; a new entry is a decision, not a fix for a red check.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep edi's tables and check them against the dictionary | Rejected: two copies kept in step by a gate are still two copies, and the QML literals had no table to check. |
| Round in QML with the dictionary's formats | Rejected: QML rounds ties differently from C++ and Python, so the surfaces would disagree. |
| Show the display format in input fields | Rejected (owner, 2026-10-24): a field would differ from the file and the Text tab, and an edit would start from a rounded value. |
