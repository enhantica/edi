# 0069. Linked measured data

- **Status:** Accepted
- **Date:** 2026-11-04
- **Implementation:** 🟡 Partially implemented — several files at once from file and web, a scan reading a linked
  folder, Copy data into the project, and data not found with Locate folder… are in the app; a single experiment's
  linked data file, collection data stored by id and digest and fetched at fit start, the Include data on save
  setting and the 100 MB save warning remain
- **Priority:** High

## Context

Measured data entered a project only by copy: an experiment holds its data in its own `.edi`, and a scan read a
folder that had to sit inside the project. Users with hundreds of files, or with data in a shared folder, asked to
load several files at once and to keep large data where it is. crysta now lets a scan read a folder anywhere.

## Decision

1. Load measured data From file… and From web… take several files. For more than one, "Load N datasets as" offers
   separate experiments, each a copy of the selected experiment's setup named after its file, or one experiment with a
   scan, the selected experiment its template. Up to five files default to separate experiments, more to a scan.
2. A scan's files are copied into `scans/<name>` in the saved project, or linked: the scan reads their own folder. The
   choice is "Copy data into the project", on for up to 20 files and 50 MB, off above.
3. A linked folder is stored relative to the project when it can be and absolute otherwise; crysta re-expresses it
   when the project is saved elsewhere.
4. A project whose linked folder is missing still opens. The Experiment page shows "Data not found" with the folder
   and Locate folder…, which points the scan at the new place as one undoable change.

## Consequences

A project with linked data needs that data on the machine that opens it. Separate experiments still copy their data,
since an experiment's file has no data path field yet; collection data is downloaded, not stored by id and digest.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Copy everything always | Rejected by the owner (2026-11-04): large scans make projects and saves slow |
| Absolute paths only | Rejected: a project moved together with its data would break |
