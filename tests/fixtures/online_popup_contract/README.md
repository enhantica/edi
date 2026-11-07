# Popup contract fixtures

The popup contract of 2026-11-04 covers “the online popup’s results table,
fields and Load action”, “formula search for experiments, and every collection
entry carries its formula”, and “search popups follow the app’s design, and the
experiment Load menu shows tooltips”.

The COD answer is hand authored. Its two names and non-orthogonal cell distinguish
name filtering and all six lattice values. The DOI is an injected fixture link;
URL handlers intercept it, so no browser or network is used. The expected short
reference is `Smith et al., Phys. Rev. B 40, 34 (2026)`.

The formula index deliberately lists a substituted sample before the exact sample.
Its identifiers and names also sort in that order, so alphabetical sorting cannot
stand in for exact Hill-match priority. The closed formulas are LaCoO3 and
La0.5Ba0.5CoO3. Each kind also has a sample lacking La, which must be excluded.

The extra COD alpha-substituted row shares the requested elements but changes the
amounts. Its injected presence proves COD keeps exact formula filtering when the
collection reader changes to element matching.

| Existing assertion/actor | Before | After |
| --- | --- | --- |
| `check_from_web_opens_source_selector_data`, structure | COD fields ID, Formula, Elements, Space group; collection lacked Elements | Both have ID, Name, Formula, Elements, Space group |
| `check_from_web_opens_source_selector_data`, experiment and measured | ID, Name, Radiation, Technique, Instrument | Retain those fields and add Formula and Elements |
| `result` | The Kind cell identifies what loads | Model rows all match the popup’s own kind; dedicated column gates refuse Kind |
| `checkPreferences`, EasyDiffraction kinds | structures, experiments, data | structures, experiments, data, projects, matching the collection design |
| `check_disk_parity`, `check_new_target_import`, `check_late_delivery`, `check_outage_class`, `check_unavailable_http` | Per-row `load.0` button dispatches the file | Select the result, then use the bottom Load button; retain the same file, undo, late-owner, failure and alternate-source checks |
| `CollectionBoundarySession.check_integrity`, popup location file controls | Per-row load action | Same content and fallback checks through selection and bottom Load |
| WebAssembly HTTP driver | Per-row load icon | Select the independent fixture id, then bottom Load; HTTP index and file receipts retained |

The new tooltip gates observe each control’s own nonempty explanation, hover it
through pointer input, and toggle Preferences while the hover is held. Geometry
gates use both sources at the supported minimum and a wide viewport. The full
Main window separately checks four displacement rows: all Biso and mixed types;
its title must follow the displayed row count in either case.

The offscreen popup actor enables Qt’s `QT_QUICK_CONTROLS_HOVER_ENABLED` desktop
mouse seam. Tooltip transitions and timeout are controlled like the existing
tooltip style actor; no visible/opened state or production preference binding is
forced. Actual hover and the control’s own explanatory popup are observed.

Tooltip text from a control is only its ownership/roundtrip marker; the independent
oracle is the nonempty explanation and its visible response to Preferences. The
displacement fixtures prepare their common physical input once, then exercise
type changes, row removal, duplication and Undo through the public model actions.

The single-result action changed from selection plus bottom Load (or double
click) to an ordinary row click. The action still dispatches exactly one download
and one ordinary loader change, and one Undo restores the prior project. Formula
placeholder checks retain the two written examples without requiring an extra
third permutation in the limited field width.

Search continuation inputs exercise the count/list/detail protocol with 250
synthetic identities, three batches (100, 100, 50), and a failed middle batch.
Journal mappings are the ISO 4 forms explicitly specified for Physical Review B
and Journal of Solid State Chemistry. The local CSV feeds the standalone table
generator; the collection copy supplies the real popup, including an unlisted
journal that must retain its full title.

The COD Name witness now models the service's text-filtered answer and checks
that Name reaches its request. The earlier witness filtered an unfiltered JSON
answer in the client. Both retain exact Hill-formula query coverage. Blank
layout slots are excluded from semantic header counts; ID, Name, Formula, Space
group, Cell and Reference remain required. Source labels now use the full
database names. Deferred ownership gates call the shipped selected-row handler
in one event turn so the queued reply still follows the project change; the
separate pointer gate checks actual row input.

Search-input actors now select and replace the old field text before typing a
new ID, since searches persist within a session. A zero-result COD fixture
answers the count request with zero. The ordinary host injects one logical
collection source; ordered-location fallback remains in its dedicated injected
location actors. Menu tooltip actors exclude section headings, which are
non-actionable labels. Remembered-source checks activate the actual selector
handler before closing the popup.

Dependency-adoption cases invoke the shipped selected-row handler so pointer
loading failures do not mask their download and transaction checks. Both cases
supply the structure reply: reusing an existing structure forbids replacing or
duplicating it, not fetching its entry. The reuse control first changes a cell
length and requires that held structure to survive unchanged. Actual pointer
row loading remains a separate gate.
