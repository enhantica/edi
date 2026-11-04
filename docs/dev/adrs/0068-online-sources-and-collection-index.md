# 0068. Online sources and the collection index

- **Status:** Accepted
- **Date:** 2026-11-04
- **Implementation:** 🟡 Partially implemented — the app's Load ▾ From web… popup, the sources table, the index
  reader, the index generator, the CLI and Python readers and the Examples list from the collections; the collection
  repository and its mirror, and moving the bundled examples into it, wait for the owner
- **Priority:** High

## Context

Structures, experiments and measured data came only from files on disk. Users asked to load a structure from the
Crystallography Open Database and to reach the examples and tutorial data from every interface, including the web
app, which has no files of its own. EasyDiffraction will keep its own collection of structure CIFs, measured data in
several formats and whole projects in a public repository, mirrored at a stable address, and that collection should
also stand in for COD when COD cannot be reached. The collection is small, a few hundred entries at most, so it needs
no database server.

## Decision

- **One Load menu per page.** The Structure and Experiment pages each show one row of three buttons: Load ▾, Create,
  Duplicate. The Experiment menu has two groups, a full experiment and measured data for the selected experiment (or a
  new one when none is selected); each group offers From file… and From web…. The Structure menu offers the same two
  for a structure. Each item shows its formats or sources in grey after its name; anything longer is a tool tip. Load
  data… left the experiments table row; its Data file cell shows the file name or "— no data yet".
- **One popup.** From web… opens one dialog for all three kinds: a source selector at the top, the fields of the chosen
  source with ID first, Search, and a results table with a Kind column and a Load button per row. COD takes ID, formula
  (Hill notation), elements and space group; a collection takes ID, name, formula and space group for structures and
  ID, name, radiation, technique and instrument for experiments and data. Loading downloads the entry's file into a
  temporary file and hands it to the project's ordinary loaders, `loadStructure`, `loadExperiments` and `loadData`:
  there is no second reader. Measured data without a selected experiment creates one, taking the probe and beam mode
  from the entry's radiation and technique. When a source cannot be reached, the popup says so and offers the next
  source that holds the same kind. Unreachable is decided by the failure's class, never by a list of codes: a
  transport, proxy or server failure, or any 5xx answer; a 404 or a refused request is an answer, reported as such.
- **A sources table in Preferences.** Three rows are built in: COD (`https://www.crystallography.net/cod`),
  EasyDiffraction's collection on GitHub (`enhantica/edi-data`) and its mirror (`https://data.easydiffraction.org`).
  A row can be disabled; user rows, a name and a URL, can be added, edited and removed. The table persists in the
  settings file (`Online/sources`); a built-in row's name and URL come from the program, so an update can move them.
- **The index.** A collection is plain files in a git repository behind one base URL, with one generated
  `index.json` at its root; any static mirror serves it unchanged. The index is
  `{"schema": "edi-data-index/1", "entries": [...]}`; an entry has `id` (stable within the collection), `kind`
  (`structure`, `experiment`, `data` or `project`), optional `name`, `description`, `formula` (stored in Hill
  notation, when known), `elements` (the symbols present, Hill order; read from the formula when absent), `space_group`, `cell` (six numbers), `radiation`, `technique`, `instrument`, `facility` and `source`,
  and `files`, at least one `{path, format, sha256, bytes}` with the path relative to the base URL and the digest
  and size optional but checked when present. The reader in core, `edi/online_index.hpp`, refuses another schema,
  an unknown kind, a repeated id, a non-relative path, a malformed digest or size, or an entry without files, and
  searches an index by the fields above or finds an entry by id. The same reader serves the CLI and Python.
  `tools/data/build_collection.py` populates a collection folder from the bundled examples and the tutorial files,
  writes the index with the hashes, and checks a folder's index against its files; until the data repository
  exists the generated collection lives in `build/collection`, outside the repository.
- **COD through its own service.** A COD search calls `result?format=json` with `id`, `formula`, `el1`…`el8` and `sg`,
  and maps each answer row to an entry whose file is `<id>.cif`. Formula fields are normalised to Hill notation
  before they are sent or compared.
- **A seam for tests and demos.** `--online-source <id>=<url>` on the command line, repeatable, or
  `EDI_ONLINE_SOURCES=<id>=<url>;<id>=<url>` in the environment, points a source at another URL for the run; a
  `file:` URL names a folder holding `index.json` and the files it lists, so a test runs with no network. A COD
  source pointed at a folder is read as a collection. An override is shown in the table and never stored.

## Consequences

- Online loading reuses the file loaders, so a format the app reads from disk it reads from the web, and nothing else.
- The web app searches and loads through the browser's fetch; a source that forbids cross-origin requests shows as
  unreachable there and the popup offers the collection instead.
- The Examples list adds every enabled source's `project` entries to the bundled examples, each opened by
  downloading its archive; `edi.load_collection` and `edi collection list|find|fetch` read the same index.
- The collection repository, its mirror and moving the bundled examples into it follow once the repository exists;
  until then the two EasyDiffraction rows answer "cannot be reached" and the Examples list shows the bundled set.
