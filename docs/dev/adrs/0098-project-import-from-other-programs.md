# 0098. Import projects from other programs

- **Status:** Proposed
- **Date:** 2026-11-21
- **Implementation:** ✅ The shared base with the cryspy, FullProf and GSAS-II importers and the cryspy and FullProf
  exporters; GSAS-II has no exporter yet (ADR-0097)
- **Priority:** High
- **Forward constraint:** A new program joins by adding one importer to the base. The session, the GUI and the
  loader never test for one program's files, and crysta gets no option that exists only to match one program.

## Context

Users start from projects made in cryspy, FullProf and GSAS-II. The cryspy importer
([ADR-0099](0099-cryspy-project-import.md)) was written on the base. The FullProf
([ADR-0096](0096-fullprof-project-import.md)) and GSAS-II ([ADR-0097](0097-gsas-ii-project-import.md)) importers were
written separately. Each found its own files in the loader and named and described its project its own way, and
one of them lost parameter metadata by replacing whole parameters during conversion.

## Decision

1. **One base.** `edi/project_import.hpp` holds the list of importers. An importer gives the program's name,
   the file suffixes it reads, and a conversion from a file to a new project. The Load project menu lists them in
   this order: cryspy, FullProf, GSAS-II. Another program can register an importer. A suffix that another importer
   already reads is refused. The app builds the menu's import entries and their file chooser from this list, so a
   registered importer appears there with no change to the GUI. Every import first asks about unsaved changes, as
   opening a project does.
2. **Detection.** The project loader asks the base whether a file belongs to an importer (by suffix, ignoring case,
   longest suffix first) before it tries the EasyDiffraction formats. The session uses the same test for recent
   projects. Neither one names a program.
3. **Shared steps after each conversion.**
   - The project is named after the source file without its suffix, using datablock name rules.
   - Its description records the source as `Imported from <program>: <file>` unless the importer wrote a more
     exact one.
   - Every parameter must carry its metadata (name, units, limits). A peak slot takes its own metadata back. Any
     other parameter without metadata is refused, naming the program and the datablock. This is how the class of
     error fixed in the GSAS-II importer is kept out of every importer.
   - The peak parameters must match the declared profile.
4. **Conversion report.** An importer refuses what it cannot convert with a message that names the source item,
   before the project is adopted. Notes that do not stop the import go to the loader's warning channel.
   An item converted with a different calculation is noted there too, naming the program, the item and the
   experiment; the loader's warning channel reaches the caller's sink, a sourced sink with the file's name, or
   stderr. The importer's ADR lists all refused, dropped or approximated items (point 6).
5. **Round-trip check.** `check_import_roundtrip` saves an imported project, opens it again and compares the value,
   the free flag and the metadata of every parameter. A free value with an s.u. is compared as the writer rounds it,
   to the s.u.'s last digit under the project's rule; any other value to six significant digits. Corpus tools and
   tests use it. Opening a file does not run it.
6. **Convert to what crysta already has.** An importer maps the other program's model onto crysta's existing
   models. crysta has no program-specific options and no maths that only reproduces one program. Any difference or
   missing feature is listed in the importer's ADR under "What EasyDiffraction does not have". If it is needed
   later, it is added to crysta as a general feature that every project can use.

7. **Export.** The same header lists the exporters, `project_exporters()`: a program's name, the menu's hint and a
   writer that creates a new directory holding a copy. Save project as offers them, always as a copy, in the order
   cryspy, FullProf; `export_project` picks one by name. A writer refuses by name what the other program cannot
   hold rather than writing it approximately. GSAS-II has no writer yet, so its entry stays disabled.

## Consequences

- Adding a program means writing one conversion plus its ADR, with no session or loader changes.
- Imported projects are named, described and checked the same way whatever their source.
- Some imported projects calculate differently from their source program, and the importer's ADR records why.
  Results match only where the models are the same.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Keep each importer's own detection in the loader and the session | Rejected: every new program would touch shared code, and the checks drift apart. |
| Add options to crysta that copy one program's calculation (FullProf's FCJ limit, Bérar–Baldinozzi point evaluation, IRF split) | Rejected by the owner: program-specific maths in crysta. The FullProf branch's crysta changes were reverted. |
| Run the round-trip check on every import | Deferred: it writes a full project to disk. Tools and tests run it instead. |
