# 0052. Project folders, archives and opening

- **Status:** Proposed
- **Date:** 2026-10-25
- **Implementation:** 🟡 Partially implemented — folders, archives, export, the open routes and the save sequence on
  the desktop app, the command line and Python; the web app's archives come from the core. The web app's picked
  folder (the File System Access API) is pending.
- **Priority:** High
- **Forward constraint (binding on new features):** a project is one folder; every surface reads and writes a project
  archive through the core's `project_archive` functions and saves through `adopt_saved_project` after the write, so
  no surface gets a second archive format or a save the others cannot reopen identically.

## Context

A project made in one app should open in another (owner, 2026-10-10): the desktop app, the web app, the command line
and Python each need to open a project from its folder, its `project.edi` or a `.zip`, and to hand it on as one file.
The web app had its own archive code on Qt's private zip classes, which the core cannot use (ADR-0009: the core is
Qt-free). A save rounds what it writes (crysta ADR-0092), so the open project must take the written values and the
calculated pattern must be recalculated from them, or the file and the screen disagree (owner, 2026-10-18 and
2026-10-24). Opening taurine took 2.5 s, 9.4 s the second time; nearly all of it was the pages being rebuilt and drawn,
not the project being read (relay `knowledge/analysis/e04-t23-opening-measurement.md`).

## Decision

1. **One folder.** A project is its folder (`project.edi`, `structures/`, `experiments/`, `analysis/`, `reports/`) on
   every surface.

2. **The archive.** A project archive is a `.zip` of the folder with each member named relative to it, deflated and
   carrying its file's time. Build and cache files are left out: any name starting with `.`, `build` and `__pycache__`
   folders, `*.pyc` and a save's `*.edi-staged` files. The core writes it (`project_archive_bytes`,
   `write_project_archive`) with miniz, compiled into the core. Reading accepts `project.edi` at the archive's top or
   inside its one top folder, so archives zipped by hand open too. Every member name is checked before anything is
   written: an absolute name, a drive, a backslash or a `..` component refuses the whole archive; a link is not
   unpacked.

3. **Opening.** `load_project` takes a folder, a `project.edi` (its folder) or a `.zip`. An archive unpacks into a new
   temporary folder; the project then has no folder of its own (`path` empty) and reads its data from the unpacked one,
   so its first Save asks where to keep it (Python's `save` refuses, `save_as` sets it; the apps open Save as), and
   later saves go there. The unpacked folder's other files, its reports among them, are carried into the saved one.
   The CLI's `fit` and `calc` take a `.zip` too; they write back only into `--output DIR`, never into the archive.

4. **Export.** The Project page's *Export project*, `edi export <project> -o <file>.zip` and `Project.export_zip(path)`
   write the project's folder as last saved, as one archive. A project opened from an archive exports the unpacked
   folder; a project with no folder yet is written to a temporary one first. The web app downloads the same bytes.

5. **The save sequence.** Every surface writes through crysta's writer (`save_project`), then calls
   `adopt_saved_project`: the open project takes the values a reopen reads, and, when they changed and the project held
   a calculation, it is calculated from them and written again. The file, the open project and a reopened project then
   agree, the calculated pattern and R factors included. In the app this is not an edit: the project stays unmodified
   with nothing to undo.

6. **Opening fast.** The pages let go of a project before it is replaced and are built again in the background, the
   shown page first and the others once it is ready; a page on its way shows *Opening this page…*. Opening another
   project meanwhile drops the pages being built, and the replaced project's worker is gone with it, so nothing of the
   first reaches the second. A Save while pages or the first calculation are pending runs the save sequence of
   decision 5 on the model, unaffected.

7. **The web app.** It reads and writes archives through the core. It keeps zip download (Save) and folder or archive
   upload (Open) in every browser; in Chrome and Edge, where the File System Access API exists, a picked folder is
   written in place by later saves (pending).

## Consequences

- A project moves between surfaces as one file, and the archive one surface writes is the archive every other writes.
- A save costs a reopen and, for a calculated project, one more calculation and write; never one per frame.
- Pages are built per project, so the first visit to a page after opening shows it pending for a moment.
- miniz joins the components edi ships (DEPENDENCIES.md).

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep Qt's private zip classes in the web app | Rejected: the core, the command line and Python cannot use them, and two archive implementations drift. |
| zlib with a hand-written zip container | Rejected: more code to own than miniz, which brings both. |
| Archives with one top folder, as the web app wrote them | Rejected for writing: members relative to the folder are what Python's `zipfile` and other tools produce from it; both layouts are still read. |
| Save the open project's unsaved changes into an export | Rejected: export writes the project as saved, as the folder does; Save first to include changes. |
