# 0039. Project output

- **Status:** Accepted
- **Date:** 2026-10-17
- **Implementation:** ✅ Implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a new writer of anything under a project folder, in the core, the
  app or the Python library, calls the engine's `crysta/project_output.hpp` or `edi._project_output`; it never opens,
  appends, renames or removes a project file with the filesystem's own calls, and a source scan refuses one that does.

## Context

edi writes into a project's folders outside the engine's save: Save report (core, Python, command line and app),
the command line's calc write-back, and the app's scan files in `analysis/` (the run record, the results it restores
or sets aside on Undo). Each kept its own rules for links and temporary files, and each repair reached only the
writers it named, so a link at a folder, a second name of an outside file at a temporary name, or an unchecked
removal kept turning up in the next writer.

## Decision

Every file edi writes, renames or removes under a project folder goes through one module per language, which keeps
the engine's rules for project output:

1. A folder written into is the project's own: a link standing at it, or at any folder between the project and it,
   is first replaced by a folder of the project's own linking each entry of the folder it named.
2. A temporary file is created new: whatever stands at its name (a link, a second name of another file, a leftover)
   is removed first, and the file is opened exclusively, so its bytes never reach a file another name shares.
3. A file is replaced by renaming its complete temporary over it. The temporary goes beside the file, or in the
   project folder when a folder on the way is a link, so a failed write leaves the project and whatever a link names
   as they were.
4. Every removal, write, rename and close is checked; a refused write throws, naming the file.

The core and the app call the engine's project-output functions (`crysta/project_output.hpp`) directly, so they write
exactly as the engine's save does; a report file the engine refuses is reported as a `std::runtime_error`. The Python
module, `edi._project_output`, keeps the same rules for `Report.save_html` and the calc write-back. A path the caller
names outside the project (an explicit `save_html` path) is written the same way, with its own folder as the root.

Not project output, and written as before: the app's own settings and configuration, the temporary copies it opens
an example or a read-only project from, the browser's virtual files, the demo's captures, and the scratch folder a
save prepares its texts in before the engine writes the project.

## Consequences

- One place to review for every project writer, in each language.
- The report writers, the calc write-back and the scan files share the temporary names and the refusal behaviour of
  the engine's writers.
- Scan files written by the engine itself (a scan fit's results, provenance and notes) follow the engine's rules
  directly; edi does not write them.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A separate edi implementation of the rules in C++ | Rejected: two implementations of one rule drift; the engine's is already the save's. |
| An edi C++ module passing each call on to the engine's | Rejected: a second layer adds names a source scan must allow and nothing the engine's functions lack. |
| Keep each writer's own handling and add sites as reviews find them | Rejected: each round found another writer. |
