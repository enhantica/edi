# 0080. The case record

- **Status:** Accepted
- **Date:** 2026-11-08
- **Implementation:** 🟡 Partially implemented — the record's builder, its check and the collection writing it; the
  pins and the generated tutorials follow
- **Priority:** High
- **Forward constraint (binding on new features):** a tutorial, docs page or collection entry learns a case's files,
  start, pinned values and tutorials from its record, built by `tools/checks/case_records.py`; nothing keeps its own
  list of cases or copies a value the record holds.

Extends [One example catalogue](0048-one-example-catalogue.md) and
[Online sources and the collection index](0068-online-sources-and-collection-index.md).

## Context

The owner asked for one case, one example and one tutorial per interface, kept in step (2026-11-07): each case of the
collection has an example project with one start that is not yet fitted, a Python notebook, a built-in tutorial in the
app, a docs page for the app and a docs page for the command line, and the example fits to the same values from the
command line, Python and the app. ADR-0048 already made one registry (`docs/user/cli/projects.yml`) and one project
per case, with the tutorial file named by the case id. What is missing is one place that says, for each case, which
files a tutorial teaches from, which values a fit must reach, and which tutorials exist, so that the generated
artefacts read it instead of restating it, and a check can refuse a case that lacks any of them.

## Decision

1. **The cases.** A case is a registry row with `user-facing: true`, as ADR-0048 has it. There are 23, 21 fitted and two
   simulations: ADR-0048's catalogue without the Si time-of-flight and NaCl X-ray simulations, which are removed with
   their projects, tutorials and collection entries, and with a single-crystal simulation of the Tb₂Ti₂O₇ HEIDI case,
   its structure and instrument without measured data, so the simulations are one powder (`pd-neut-cwl_lbco_simulation`)
   and one single crystal. `pd-neut-cwl_yap-spodi_3k` and
   `pd-neut-cwl_yalo3-al2o3-spodi` hold the same measurement, so they are one case, `pd-neut-cwl_yalo3-al2o3-spodi`,
   matched to diffraction-lib's `refine-yap-3k`; the other is not a case and has no tutorial. The scan case is
   `pd-neut-cwl_cosio-d20_scan-213f`; `pd-neut-cwl_cosio-d20_scan` stays a fixture and leaves the collection.
2. **What is written, and where.** A record is built, never written by hand, from what the repository already holds:

   | field | from |
   |---|---|
   | `id`, `order` | the registry row and its place among the cases |
   | `title`, `nav_title` | two titles (the owner, 2026-11-08): the page title, the row's `title:`, `<sample> on <instrument>` (`Co₂SiO₄ on D20`), as the breadcrumb section already names the technique; and the one-line navigation title, `<short sample name> <code>` from the row's `short-name:` and the case id's technique code (`Co₂SiO₄ pd-neut-cwl`, `YAlO₃+Al₂O₃ pd-neut-cwl`). The docs' navigation, the tutorial pages and the app's Tutorials list use them; the check refuses a case without both, or two cases of one section with one navigation title |
| `diffraction_lib` | the row's `diffraction-lib: <tutorial>` (diffraction-lib has this case, `match: same`) or `follows-diffraction-lib: <tutorial>` (a case without one takes that tutorial's outline, `match: follows`) |
   | `structures`, `experiments` | the project's `structures/*.edi` and `experiments/*.edi`, as the collection's entry ids `<id>-<stem>` |
   | `data` | the measured pattern of each of the project's experiments that holds one, which `build_collection.py populate` exports as a plain `x y sy` file, as the collection's entry ids `<id>-<experiment>-data`; a tutorial loads its data from there |
   | `tags` | the case's tags as the app's Examples list shows them, in its order: each a facet, value and label (`{facet, value, label}`), the facets and labels from `app/examples/tags.json` and the values the catalogue derives from the case's project (`app/examples/metadata.json`, `tools/dev/example_metadata.py`). The record is their one source: the app's Examples list and Tutorials dialog, the docs tutorial and examples pages and each notebook's header show exactly these, with the same names, colours and icons, and a check compares every surface with the record (the owner, 2026-11-08) |
| `section`, `section_icon` | the tutorial section every interface groups the case under, and its Font Awesome icon, in this order (the owner, 2026-11-08): Getting started (`rocket`, the case whose structure is built by hand), Simulation (`calculator`), Multiple datasets (`layer-group`, a joint or scan fit), Single crystal (`cube`), else Powder (`chart-area`); the first rule that holds decides, from the record's own `structure_from` and `tags`. The overview pages, the navigation, the app's lists and the notebooks show these names and icons |
| `structure_from`, `data_from` | the row's `structure-by-hand: true` (the structure is built step by step: `hand`; else loaded from the collection's CIF: `collection`) and `data-from-file: true` (the data also come from a file on the user's disk: `[collection, file]`; else `[collection]`), the same on every interface (the owner, 2026-11-08; the command line cannot build a structure yet, so its page loads the starting project there) |
| `pin` | the `regression-pin` quantities of the case's `expected.json`, with its `source.pins` block: the edi commit the values came from and the reason they were last changed |
   | `tutorials` | by the case id: `docs/user/tutorials/<id>.ipynb`, the app's built-in tutorial `<id>`, `docs/user/app/<id>.md`, `docs/user/cli/<id>/index.md` |

   The pins are regression pins: they show that the three interfaces and later versions agree, not that the values
   are right. Correctness stays with the FullProf references in the same `expected.json` (ADR-0048 §10).
3. **One builder, one check.** `tools/checks/case_records.py` builds every record and refuses a case without one of
   its fields or artefacts, naming the case and what is missing. `tools/checks/example_catalogue.py` runs it, so the
   `cli-projects` task fails on a partial case. An artefact a later step of the work adds (the built-in tutorials,
   the app pages) joins the check in the change that adds it.
4. **The collection carries the record.** `tools/data/build_collection.py index` writes each case's record into its
   project entry as `case`, schema `edi-case/1`. ADR-0068's readers ignore fields they do not know, so an installed
   app keeps reading the index. The notebooks, the app's tutorials and the docs pages are generated from the records
   where they can be. A tutorial loads its case's structure and data from the collection by the record's ids,
   never from a file downloaded by hand (the owner, 2026-11-08); a case whose tutorial loads a CIF has that CIF published
   as its structure entry.

## Consequences

- A case cannot be added, renamed or dropped in one place only: the registry, the project, `expected.json` and the four
  tutorials are checked together.
- The collection says, for each example, which structure and data files teach it and which values it reaches.
- `pd-neut-cwl_yap-spodi_3k` needs a page, provenance, notebook and catalogue entry as every case has.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A hand-written `case.json` per case | Rejected: it would restate the registry, the project and `expected.json`, and drift from them |
| A new `case` kind in `index.json` | Rejected: ADR-0068's reader refuses an unknown kind, so every installed app would stop reading the index |
| A separate pin file | Rejected: `expected.json` already holds the CLI's regression pins; the case pins extend it |

### Catalogue addition coverage

The later TbTi simulation and CoSiO HEiDi additions participate in the source-text
and displayed-field app witnesses alongside the retained cases. Their source-only
generators add input expectations without refreshing earlier measured or calculated
values. The registry and app metadata preserve the independent current inventory
order: simulations first, then powder fits/scans and the declared single-crystal
cases. Source-hash transitions for the two CoSiO powder cases admit only the
previously approved ADP free flags and removal of the retired stop-rule field;
all prior experimental and displayed-value expectations remain exact.
