# 0069. Linked measured data

- **Status:** Accepted
- **Date:** 2026-11-04
- **Implementation:** 🟡 Partially implemented — several files at once from file and web, a scan reading a linked
  folder, Copy data into the project, data not found with Locate folder…, the Data on save setting and the large-save
  question are in the app; a single experiment's linked data file and collection data stored by id and digest and
  fetched at fit start remain
- **Priority:** High

## Context

Measured data entered a project only by copy: an experiment holds its data in its own `.edi`, and a scan read a
folder that had to sit inside the project. Users with hundreds of files, or with data in a shared folder, asked to
load several files at once and to keep large data where it is. crysta now lets a scan read a folder anywhere.

## Decision

1. Load measured data From file… and From web… take several files. For more than one, "Load N datasets as" offers
   separate experiments, each a copy of the selected experiment's setup named after its file, or one experiment with a
   scan, the selected experiment its template. Up to five files default to separate experiments, more to a scan.
2. A scan's files are copied into `scans/<name>` in the saved project, or linked: the scan reads their own folder.
   Separate experiments hold their data, or link it: each reads its own file where it is (`_data_source.path`). Linked
   files from a data collection keep the entry and the file's digest instead (`_data_source.collection_id`,
   `_data_source.digest`): the app downloads the file when a fit starts (or on Download), checks the digest, and keeps
   it in its cache, which serves the next opening. The rule is the same for every kind of data: a powder pattern
   and a single crystal's reflection file are copied or linked alike, a collection's file by entry and digest, and a
   scan's files are copied or linked as a folder. A scan of collection files is copied until a scan can name its
   files by entry and digest. A file of several datasets (a FullProf file's codes) is copied, one experiment each,
   since a link names a file and not one of its datasets. The choice is "Copy data into the project", on for up to 20 files and 50 MB,
   off above.
3. A linked folder is stored relative to the project when it can be and absolute otherwise; crysta re-expresses it
   when the project is saved elsewhere.
4. A project whose linked folder or file is missing still opens. The Experiment page shows "Data not found" with the
   folder and Locate folder…, or the selected experiment's file and Locate file…, which points it at the new place as
   one undoable change.
5. Data on save (Project page, Extras) says what a save does with a scan's linked files: include them, keep them
   linked, or ask on every save. Included files are copied into the saved project's `scans/<name>` and the written
   project reads them there; the open project points there only once the save succeeded, one undoable change, and a
   copy (Save a copy) leaves the open project as it was. It is kept by the app for the project's folder, as the last
   selection is (ADR-0031), not in the project's files; until chosen it includes the data up to 20 files and 50 MB
   and keeps it linked above. Each save is an operation made at its start (Save, Save as to a new or an existing
   folder or a .zip, Save a copy, the browser's Save, Save as and Download): it carries this decision, the plan it
   was made from and the state it read (the model, its revision, and a receipt of every input file's content), and a
   save started meanwhile makes its own. A moving save of a changed project is planned again; bytes copied that differ
   from the receipt refuse the save.
   A save holds its project from before its plan until its publication and every notification of it are done.
   Meanwhile edits, Undo, the assistant's changes, a fit start, another save, and opening, creating or closing a
   project refuse, saying the project is being saved. A question or a browser picker waiting on the user lets go of
   the project; the answer takes it again and checks the plan before anything is written. A change is committed
   before it is announced, so whatever reacts to an announcement reads the project as it now is.
   A save does not start while a fit runs or is still publishing its end.
   What a save carries is checked against the writer's own boundary, as crysta states it: every file it does
   not regenerate, the part of `project.edi` it keeps (also when the record is a link the save replaces), and each
   link, to a file or a folder, by the text it writes, with the bytes it reaches when it reaches a file.
   Every save is staged whole beside its destination, the project's own folder included, and checked in full. The
   check runs again right before the last writer. A folder is published by renaming the checked stage into place;
   no rename replaces anything, so a fresh destination that appeared meanwhile is refused, and an existing folder is
   moved aside first and put back if the stage cannot take its name. A .zip, a browser place or a download stores
   what a link to a file reaches: the stage's links are replaced by those bytes, checked against the receipt as
   they are written, before that writer reads it, and a link to a folder or to nothing is refused. Those three
   store the same members, by the stored-copy rule of ADR-0052, and the size question and the link check follow
   that rule, so nothing counted or checked is left out later and nothing left out is refused. The size question
   counts what the save writes, carried files included and, for those writers, what their links reach. Writing
   reports back into a project's .zip is an operation too: it holds the project, copies its folder into a stage
   checked against a receipt of every file, and writes the .zip from that stage.
   Fit and Download wait for the collection files of exactly the experiments that need them, each by its entry and
   digest, through every retry; a request is told it succeeded only once those experiments hold their data, and is
   refused when one of them leaves the project or names another entry.
6. A save that would write more than 100 MB asks first, counting what it writes: its generated files; every file
   it carries over when it writes the whole project (another place, a .zip, a browser place), a regenerated file
   counted once; and the linked files when they are included. With linked data: "This save writes 1.2 GB
   (240 files). Keep the data linked instead?" with Keep linked, Copy anyway and Cancel; without, Save and Cancel.
   Save into the project's own folder asks only when it would copy linked data. An answer belongs to the question it
   answers: a later question, or another project opened meanwhile, makes it do nothing.

## Consequences

A project with linked data needs that data on the machine that opens it. Included in a save, a linked experiment's
data is written into its experiment file and a linked scan's files into `scans/<name>`.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Copy everything always | Rejected by the owner (2026-11-04): large scans make projects and saves slow |
| Absolute paths only | Rejected: a project moved together with its data would break |
