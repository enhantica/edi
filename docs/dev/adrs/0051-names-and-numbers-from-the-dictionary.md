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
   (`label`, `units`, `tooltip`, `optionLabel`, `categoryTitle`, `written`, `display`, `valueSu`) and through the
   parameter items. A page asking for an item the dictionary lacks gets nothing shown and a warning, never a stand-in.
   `parameter_variants` gives each parameter the variant it reads by (an ADP's site type), for the app, the report,
   the CLI and Python alike.
2. **The parameter specs keep only their identity.** A spec keeps its category, name, units code, range and name lists;
   its display name, units, description and LaTeX come from the dictionary. `category_title.cpp`,
   `parameter_symbol.cpp` and the label functions in `selectors.cpp` are gone. This amends ADR-0010.
3. **Labels and tooltips.** A table header, a field title and a group title show the item's display name, and a
   header, field, cell or group names the item, or the category, in its tooltip (`WP: _atom_site.wyckoff_letter`,
   `Cell: _cell`). A selector's tooltip names the
   item and the stored token, and its values show their dictionary names. A displacement column takes the name of the
   site's type (`U₁₁`, `B iso`). The titles, icons and field names [ADR-0017](0017-app-gui-design.md) §3, §5, §8 and
   §21 chose are now dictionary values, not app code.
4. **What a number shows.**
   1. An input field, an editable cell, the slider and the Analysis table show the value exactly as a project save
      writes it under the project's s.u. rule, the s.u. in its own column, so they read as the Text tab does, exactly
      where the save writes a value exactly (crysta's save spelling), and a cell too narrow for the token shows the
      token's own digits in scientific notation. A field left as it was writes nothing.
   2. A read-only table, a readout, the report and the CLI show a value the space group fixes as its exact fraction, a
      value with an s.u. as `value(su)` by the project's rule, and any other value in its item's display format. The
      report and its CIF always use the IUCr rule. The report's labels and units, the CLI's Rwp and χ², the chart's
      point labels and read-outs (with a comma between thousands, [ADR-0021](0021-pattern-presentation.md)) and Python's
      `repr` and category `str` are the dictionary's too. These are the rules of
      [ADR-0037](0037-exact-fractions-and-constrained-values-on-screen.md), except that a constrained value without an
      s.u. takes its own item's format (amending its §2).
   3. A number with no dictionary item (a duration, a chart tick) keeps the app's own rule,
      and a value too wide for its cell still shows in scientific notation (owner, 2026-10-22).
   4. The report's Data table keeps one number of decimals for every row of an intensity column, chosen from the
      largest measured value, with no exponent (owner, 2026-10-13); its axis column, like the reflections table, takes
      its item's fixed format.
5. **A check keeps it so.** `tools/checks/display_sources.py` reads the app, the core and the Python library and
   fails on a rounding primitive outside the bridge (`fixed_text` and `std::to_chars` with a format included), on a
   literal that copies a dictionary name (a QML text or title given as a bare string included), and on an exception
   that no longer matches anything, over the Python bindings too. It reads the dictionary from crysta's source (the pinned fetch, or
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

### Assistant inspection reuses already-published native file spelling

FIRST ParameterRegistry::refreshSpelling and ParameterItem::refreshFileText already combine save_spelling(project), written_exactly and file_text(parameter, project.su_rule, exact). Assistant inspection reuses the resulting published fileValue/fileSu pair, not another invocation of save_spelling/file_text. The registry binds its existing whole publication to the exact original project/work stamps, rule and calculated-source identities; it remains unavailable during publication, failed/stale completion or a successor publication. No second numeric value/SU store or formatter is introduced.

Current canonical path/pointer/raw-value/SU/free/dependence and displayed raw fields must match before optional file_value/file_su are attached. An absent displayed SU maps to null; an engaged native zero remains the zero string. Raw numeric uncertainty remains independent of whether a fixed/constrained parameter's file spelling carries it. No inspection-time rounded-copy calculation, project Save, mutation, adoption or additional uncertainty estimate occurs.


### Written value/SU precision is shared by fields and table cells

The first number fitting owner is NumberText's native ApplicationInfo formatter, with
ParameterItem's published fileValue/fileSu pair from the existing display bridge. Narrowing
that pair must preserve the project's uncertainty-significant last digit. Generic compact
formatting may drop a whole token's trailing zeros when no precision is supplied; that
no-SU default cannot be applied to a positive-SU pair. The shared written-narrow operation
uses the existing decimal parser, SU rule/count and compact formatter. Explicit decimal
precision and nonzero exact digits form a lower bound, so an exact/symmetry spelling is
never truncated to the ordinary SU rule. Already-exponent/fraction tokens keep their
existing spelling; absent/zero SU does not invent a precision. A signed zero with positive
SU retains its sign and the SU's last digit in scientific form. This is display-only: no
new numeric rounding, file write, model value/SU/free change or additional estimate occurs.

Both ParameterCell and ParameterField use that same operation and existing measured fitting
procedure. The field's canonical value/menu and full edit token remain file-authoritative;
only its idle text selects the fitted display. The original clean-text/draft/IME/assistant
guards remain around text writes, and a full token is shown on hover when its display is
narrow or clipped. No-op edits still start from the complete original token. Table-cell
fitDigits scaling retains its original path. Both controls retain clipping without an
ellipsis when even the full significant scientific text exceeds the available room; they
do not discard a digit or change a model value to force a visual fit.

The prior implementation in both controls is owned by this correction, even where original
and migrated builds showed the same defect. The retired generic TableViewParameter menu
is not the application parameter cell and is not changed; the active ListViewParameter
titles/units and ParamTextField injection seam remain intact. Independent cases must retain
positive/zero/missing SU, signed/zero/exponent/exact spellings, rule changes, narrow/wide
transitions, full menu/edit/hover values and all draft/IME/current-owner controls. No source
change or current output by itself qualifies those obligations.
