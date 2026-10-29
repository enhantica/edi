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
   folders, `*.pyc` and a save's `*.edi-staged` files. A member is named by where it is in the folder: a link to a
   file is archived as that file under the link's name, and a link to a folder or to nothing refuses the archive. The
   core writes it (`project_archive_bytes`,
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
   with nothing to undo. A project still being built (no structure yet, or an experiment without data) is read back the
   same way: the loader's rules for a whole project are lifted for the readback, so its written values are adopted
   too. A calculation can give an infinite value (a peak width of 1e20, say), which no number in a
   file spells, either in the calculated columns or in the residual derived from them. Such an experiment is not a
   result, by crysta's one test: it is written uncomputed, it has no R factors, and every calculation, the save's own
   and any later one, leaves it calculated with no values, so no view shows them. A NaN is a point that was not
   calculated, as before.

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


### 2026-10-28: Open publication belongs to its original replacement

The assistant port made Session replacement return actual publication/currentness. Ordinary
Open/Open-copy now propagate that result; a false result may follow a genuine partial adoption.
Original receiver/target/replacement identity also fences archive/read-only/example/web location
bookkeeping and failure notifications. A stale outer Open cannot decorate a successor with its
origin, location or error, nor delete staging after another actual replacement. Unadopted local
candidates can be retired, while actual adopted state is never rolled back to manufacture no effect.

The original complete-only GUI Open policy below is superseded by the owner's construction-state
roundtrip requirement (2026-10-28). FIRST load_project now has an explicit Construction role for
ordinary Session Open/Open-copy and Text scratch reload. Saved empty, structure-only and
not-yet-loaded experiment states restore their actual members, with no placeholders or promised
unserialized UI selection. Present data/grid/category/scan/template/relation content and held
structure links still pass the original parser/integrity checks. This is distinct from saved-value
readback, whose prior reference policy is unchanged. The original default load_project overload,
Python/CLI consumers and strict captured assistant-result loader retain complete-model semantics.
Folder/project-record/archive, read-only/example/web/recovery and session restoration converge on
the same ordinary Session role. The older app6 refusal identified that former completeness policy,
not writer corruption. Actual partial-state roundtrip/tab qualification remains required.

Picked-file and stored/recovery Open answers share that same guarded webOpenAnswer continuation.
Recovery marks only its actual successfully adopted current target unsaved. Shared openRequest
checks receiver/project/request again after setLastError notifications, and a stale/duplicate
answer never removes an accepted or successor's staging root. Only a still-current failed parse
with genuinely unadopted local staging may clean it up; no false publication result is rollback.

Replacement cleanup proves filesystem independence as well as currentness. The existing archive
owner exposes, read-only, the exact recorded ancestor its remover would delete; Session retains
that ownership while any current project/file/scan/data/retained-result closure still uses it.
Canonical ancestors and filesystem equivalence cover same roots, descendants and alias spellings.
An unresolved closure keeps ownership safely; it never causes deletion or a scientific veto.
Actual pending Open source is part of that proof before outer archive/web origin bookkeeping,
including an archive inside an older root whose unpacked work folder is elsewhere. Retention is
cleanup authority only and does not give a successor another project's displayed origin or Save
location. Later independent replacement/closure reclaims genuinely unused registered roots.
Active retired publication stacks keep their reads until deferred destruction; cleanup retries
through the existing QObject lifetime. Session stops/deletes its owned model workers before
archive cleanup or QTemporaryDir member destruction, so automatic temporary ownership cannot
remove their backing files first. No directory relocation, new registry or whole-loader change
is introduced.


### 2026-10-28: live retirement and pending Open source lifetime

Retirement stops old presentation; only ProjectViewModel destruction closes its fit and joins
the Worker. Every live Session child therefore contributes its actual backing closure, including
idle retired models. Replacement preowns both old temporary-root obligations before callbacks and
a QPointer-based unwind obligation schedules an idle retired model even when publication is
superseded. Active publication scopes retain their original deferred destruction rule. Actual
destruction retries the existing root cleanup; final Session teardown still joins workers first.

An actual Open source stays in scoped Session ownership through the original caller's final
archive/web/location bookkeeping, including nested Open scopes and same-owner SaveAs callbacks.
Scope release removes only that original dependency and retries ordinary unused-root reclamation.
The actual current model's pathChanged writes also carry a Session-private identity. Open permits
its own workIn notification, but an additional genuine path write retires the old continuation,
even if the project pointer is unchanged. It cannot reinstall an old archive origin over a
completed SaveAs. Replacement/project identity, explicit SaveAs effects, loader completeness,
filesystem permissions and displayed origin policy remain unchanged.


### 2026-10-28: independent ordinary preparation copies

Read-only folder and bundled-example Open each prepare a fresh root through the
existing archive temporary owner. The Session remembers that root before copying,
and scope exit invokes its normal closure/lifetime cleanup. Repeated IDs or source
basenames never reuse/delete an old destination. Open-copy refuses an existing
target or a target physically beneath its source rather than removing that tree.
A failed preparation leaves the original current backing and worker untouched; an
adopted or still-live model retains its actual new root until ordinary release.

Example identity, read-only source, demo path masking and SaveAs behavior keep
their original presentation and normal adoption owners. The old shared fixed-name
QTemporaryDir destination is replaced by the same registered temporary owner used
elsewhere in Session, with no second directory registry, loader or science rule.

### Verify the final adopted value/s.u. state

Review126 (hub `826f6a232d4689509f3872785d442e509f55cca9`) records successful ordinary Save with current La0.5/s.u.83 while the original structure file holds1(83). The native nonzero IUCr fallback had crossed its own half-rounding boundary, so the second serialization changed the first adopted value. The shared native formatter is corrected at that FIRST owner; app file-value/SU and Text still use it, with no number shadow store or assistant formatter.

The FIRST adopt_saved_project additionally checks the final original files after its rewrite, through the same SavedValues reader used by ordinary adoption. Exact parameter identities, numeric values/s.u.s and the separately adopted bank setting must agree with the current model under that original reader's relation semantics before success returns. It is an actual persisted readback, not equality of formatted strings or a scratch export. A project without results and without a rewrite already has its initial readback; changed/incomplete projects retain that original load role, not a new whole-project requirement. Calculated projects retain the original deferred-estimate recalculation/agreement refresh and failure restoration. A final mismatch is an ordinary Save failure with its existing partial-file/unsaved handling; it is never marked saved or silently refitted.

Normal current Save, Save As, folder/ZIP and Save a copy already pass through these original core owners (a copy adopts its own temporary project, not the live original). Native const/adopting writer, Text and optional file-value consumers share the central pair fix. No retry loop, scientific veto, fitted-value seed, extra permission or model-quality conclusion is introduced. The large uncertainty remains unresolved scientific information. Actual disk/current/calculation agreement and ordinary pair/half-boundary/incomplete behavior require independent qualification; this source change alone does not establish it.
