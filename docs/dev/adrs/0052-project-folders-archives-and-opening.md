# 0052. Project folders, archives and opening

- **Status:** Proposed
- **Date:** 2026-10-25
- **Implementation:** 🟡 Partially implemented — folders, archives, export, the open routes and the save sequence on
  the desktop app, the command line and Python, and the web app's places (decision 9); the web app's checks in a real
  browser are pending.
- **Priority:** High
- **Forward constraint (binding on new features):** a project is one folder; every surface reads and writes a project
  archive through the core's `project_archive` functions and saves through `adopt_saved_project` after the write, so
  no surface gets a second archive format or a save the others cannot reopen identically.

## Context

A project made in one app should open in another (owner, 2026-10-10): the desktop app, the web app, the command line
and Python each need to open a project from its folder, its `project.edi` or a `.zip`, and to hand it on as one file.
The web app had its own archive code on Qt's private zip classes, which the core cannot use (ADR-0009: the core is
Qt-free). A save rounds what it writes, so the open project must take the written values and the
calculated pattern must be recalculated from them, or the file and the screen disagree (owner, 2026-10-18 and
2026-10-24). Opening taurine took 2.5 s, 9.4 s the second time; nearly all of it was the pages being rebuilt and drawn,
not the project being read (measured with the app's software renderer, as on the test machines).

## Decision

1. **One folder.** A project is its folder (`project.edi`, `structures/`, `experiments/`, `analysis/`, `reports/`) on
   every surface.

1. **The archive.** A project archive is a `.zip` of the folder with each member named relative to it, deflated and
   carrying its file's time. Build and cache files are left out: any name starting with `.`, `build` and `__pycache__`
   folders, `*.pyc` and a save's `*.edi-staged` files. The core writes it (`project_archive_bytes`,
   `write_project_archive`) with miniz, compiled into the core. Reading accepts `project.edi` at the archive's top or
   inside its one top folder, so archives zipped by hand open too. Every member name is checked before anything is
   written: an absolute name, a drive, a backslash or a `..` component refuses the whole archive; a link is not
   unpacked.

1. **Opening.** `load_project` takes a folder, a `project.edi` (its folder) or a `.zip`. An archive unpacks into a new
   temporary folder. The archive is then the project's location (owner, 2026-10-25, reversing "an opened archive is
   never overwritten"): the project works in the unpacked folder and Save rewrites the archive from it, as for a
   project saved as a zip. In Python `Project.location` is the `.zip`, `save()` rewrites it and `save_as(folder)` moves
   the project to that folder, leaving the archive as it was. The command line is the exception: its `fit` and `calc`
   take a `.zip` too but write back only into `--output DIR`, since an input is never a command's output. Save opens Save project as only where writing back is
   impossible: a bundled example, an archive in a read-only place, or the browser's uploaded copy. The unpacked
   folder's other files, its reports among them, are carried into every save. There is one *Open project…*, the same on the
   desktop and in every browser (owner, 2026-10-25): a small dialog asks for a Folder or a Zip archive, then the
   matching chooser opens, a folder chooser for the project folder or a file chooser for a `.zip` (a chooser picks
   files or a folder, never both). No platform picks a `project.edi` file. A folder, a `project.edi` or a `.zip`
   dropped on the desktop window opens too. In this dialog and in Save project as, a choice the platform cannot do is
   disabled whole, its circle and its text, with no hover or press feedback, and its tooltip says why.

1. **Where the project is.** The Project page's Location is the project's folder or `.zip`, never an internal
   temporary path. A project with none of its own yet says what it came from: *Not saved yet: example \<title>*, *Not
   saved yet: opened from \<name>.zip* for an archive in a read-only place, *Not saved yet: a copy of \<folder>* for a
   read-only folder. The web app shows *In this browser only*, or the disk's folder or `.zip` by its name (decision 9).

1. **Unsaved changes and temporary folders.** Opening, creating or closing a project, or quitting, while the project
   has unsaved changes first asks to save or discard them (a project with nowhere to write yet opens Save as). Each
   temporary folder (an unpacked archive, a zip-saved project's working folder, a copy on its way into an archive)
   carries its process's id. The app releases a project's folder when the project is replaced, saved elsewhere or
   closed; a process removes the rest of its own when it ends; and each start of the app removes those a crashed
   process left (`remove_stale_archive_directories`).

1. **Save as, and export.** The desktop app has one *Save project as…* (owner, 2026-10-25). A small dialog first asks
   for the format, a folder or a zip archive, and whether to save a copy, keeping the project where it is; then the
   system's dialog asks where (a folder accepts with *Choose*, a `.zip` with *Save*). A project saved as a zip keeps
   the archive as its location: it works in a folder of its own and every later Save rewrites the archive from it. A
   copy is the project as it stands, written there, its values and location unchanged. `edi export <project> -o <file>.zip` and `Project.export_zip(path)` write the project's folder as last saved, as one archive; a project
   opened from an archive exports the unpacked folder, one with no folder yet a temporary save of it.

1. **The save sequence.** Every surface writes through crysta's writer (`save_project`), then calls
   `adopt_saved_project`: the open project takes the values a reopen reads, and, when they changed and the project held
   a calculation, it is calculated from them and written again. The file, the open project and a reopened project then
   agree, the calculated pattern and R factors included. In the app this is not an edit: the project stays unmodified
   with nothing to undo.

1. **Opening fast.** The pages let go of a project before it is replaced and are built again in the background, one
   after another in the order Project, Structure, Experiment, Analysis, Report (owner, 2026-10-25): asynchronous loaders
   that the app's own incubation controller builds in slices of about 50 ms per turn of the event loop, so input and
   drawing go on between slices. On taurine every tab is enabled about 3.2 to 3.5 s after a first open and 3.8 to 4.1 s
   after a second, against 8.6 to 9.5 s with Qt's own controller; 12 ms slices took about half as long again. Each app-bar tab stays disabled until its page is built, with the tooltip *Preparing
   this page…*; while pages build, the status bar shows *Opening project… N of M pages* with a progress bar in the fit
   area's place, gone once every page is built. A page past Project that was shown when another project opened gives
   way to the Project page. Opening another project meanwhile drops the pages being built, and the replaced project's
   worker is gone with it, so nothing of the first reaches the second. A Save while pages or the first calculation are
   pending runs the save sequence of decision 7 on the model, unaffected.

1. **The web app** (owner, 2026-10-25). Every project there has a place, and Save writes into it: no download and no
   dialog. The place is the browser's own storage (its origin private file system, which survives a reload), shown as
   *In this browser only*: an example, a new project and, in Firefox and Safari, a project opened from the disk (a
   folder or a `.zip` uploaded) are worked on there. The first Save of a project into it in a session shows a dialog
   with the warning icon, *Saved in this browser only. The browser may clear what it keeps; use Save project as… to
   keep a copy on your disk.*, with Save project as… and OK; later saves show a short notice. A browser may clear what
   it stores (its site data, or Safari's removal of sites unused for about a week). At start the app writes one small
   file to learn whether the browser keeps anything for it: where it does not (a private window may not; Safari
   answers *UnknownError*), Location reads that the project is only in this tab, Save saves nothing and says so in the
   same dialog, and nothing touches that storage again; a write that fails later does the same, in plain words. In
   Chrome and Edge, where the File System Access API exists, Open takes a folder or a `.zip` on the disk, which stays the project's place: Save writes it back, the files a save removed from the folder are removed
   there too, and an archive is rewritten whole. Save project as… always opens edi's own dialog. In Chrome and Edge it
   is the desktop's: a folder or a `.zip` the user picks becomes the place (or, with *Save a copy*, only receives
   one), the chooser starting where the project is and suggesting its name. In Firefox and Safari, Folder is shown
   disabled with a tooltip saying why, Zip archive is chosen and Save a copy is checked and disabled: OK hands a copy
   of the project, as a Save writes it, to the browser as a `.zip` named as the project came, leaving the project and
   the browser's storage as they are. The browser decides where downloads go, so replacing the original file goes
   through its own save dialog, which the notice says only for a project opened from a file. Open asks first for a
   folder or a `.zip`, then the browser's own chooser. Each place has a record in the browser's IndexedDB (kind, name,
   and the disk's handle), which Recent projects lists; a project's unsaved state is kept beside it three seconds
   after its last edit, so after a reload or a closed tab Recent projects offers *Continue where you left off* with
   those changes, until a Save or a discard drops them. The page writes the browser's storage from a worker with
   synchronous file handles, which Firefox and Safari have where they lack writable streams.

## Consequences

- A project moves between surfaces as one file, and the archive one surface writes is the archive every other writes.
- A save costs a reopen and, for a calculated project, one more calculation and write; never one per frame.
- Pages are built per project, so the first visit to a page after opening shows it pending for a moment.
- miniz joins the components edi ships (DEPENDENCIES.md).

## Alternatives considered

| Alternative                                                                        | Verdict (why rejected / deferred)                                                                                                                            |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Keep Qt's private zip classes in the web app                                       | Rejected: the core, the command line and Python cannot use them, and two archive implementations drift.                                                      |
| zlib with a hand-written zip container                                             | Rejected: more code to own than miniz, which brings both.                                                                                                    |
| Archives with one top folder, as the web app wrote them                            | Rejected for writing: members relative to the folder are what Python's `zipfile` and other tools produce from it; both layouts are still read.               |
| Separate *Open a project folder*, *Export project* buttons beside Open and Save as | Rejected by the owner (2026-10-25): six buttons whose differences are unclear; one Open and one Save as, with a format and a copy choice, do both jobs.      |
| Save the open project's unsaved changes into an export                             | Rejected for the command line and Python: export writes the project as saved, as the folder does. In the app, *Save a copy* writes the project as it stands. |
