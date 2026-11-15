# 0087. A series of joint fits: loading its files and linking its data

- **Status:** Proposed
- **Date:** 2026-11-15
- **Implementation:** ⬜ Not implemented
- **Priority:** High
- **Forward constraint (binding on new features):** a series is stored as its data folder and one file pattern per
  experiment; nothing stores, reads or hashes a file per point at selection, open or save.

Builds on ADR-0026 (scan datasets), ADR-0052 (project folders) and ADR-0069 (linked measured data), whose rules and
defaults this ADR keeps.

## Context

A temperature series on a multi-bank instrument has one file per bank per temperature: for 1,000 temperatures and
100 banks, 100,000 files. crysta's sequential driver now fits such a series as one joint fit per point: the scan
declares its data folder and one file pattern per experiment, and the text a pattern's `*` matches is the point. edi
must load the files into that shape, keep its rules for linked data (ADR-0069: copy or link, defaults by size, a
warning before a large save, data not found with Locate), and answer what was left open for linked data: a missing,
moved or changed file in a series, at open and during a fit, and who builds the Save as dialog's Measured data row.

Prior art surveyed: data paths relative to the project or working folder (MAUD, CCSL); a series read in place by
default, copied on request (diffraction-lib's `copy_data=False`, "avoids surprising large copies for thousand-file
series"); a missing linked file searched for beside the project and then asked for (GSAS-II's image files); content
checked by SHA-256 on open (RietX, PhaseSmith, both of which copy the data into the project). Data embedded in the
project: GSAS-II powder data, Z-Rietveld, SasView, cryspy. NeXus containers read in slices (scippnexus, Mantid).

## Decision

1. **Loading.** Load measured data From file… and From folder… take many files. "Load N datasets as" (ADR-0069 point
   1) gains a third choice, **a series of joint fits**, offered when the file names fall into two or more groups of
   equal size: edi replaces, in each name, the first run of digits that differs between names with `*`, and names
   sharing the result form one group, one experiment per group. The dialog shows "B experiments × P points" and each
   group's pattern; the user may edit the patterns. Each experiment is a copy of the selected experiment's setup,
   named after its group, and the experiments form an experiment set (ADR-0086). The grouping reads names only, on a
   worker; the first point's file of each experiment is read as that experiment's template data.
2. **What is saved.** The scan's `data_dir` and, per experiment, its file pattern; no per-file entry, read or hash at
   Save (the owner's rule for scans, kept here).
3. **Copy or link.** The series folder is copied into `scans/<name>` or linked as a folder, by ADR-0069's rules and
   defaults unchanged (copy on for up to 20 files and 50 MB, the question above 100 MB), counting every file the
   patterns match. One link per series: the folder. A series of collection files waits for collection scans.
4. **Missing, moved or changed files.**
   - At open: a missing folder shows Data not found with Locate folder… (ADR-0069 point 4); a moved folder is located
     the same way. A point whose experiment has no file, or two, is listed as incomplete in the dataset list, and
     crysta skips it.
   - During a fit: a file that has gone, cannot be read or is malformed makes crysta skip that point and list it with
     the cause; the series goes on.
   - A file whose content changed is not detected: no file is hashed (point 2). Its row names the file; a Reset fits
     it again. A single experiment's linked file keeps the receipt ADR-0069 gives it.
5. **The Save as dialog's Measured data row.** For a project with linked data the dialog shows "Measured data: Copy
   into the project / Keep linked", preset from Data on save and the size defaults. It is the per-save decision
   ADR-0069 point 5 already makes, shown in the dialog; built with this ADR, consumed as it is by later work that
   links collection data.
6. **The open questions for linked data, answered.** How a project references outside data: ADR-0069 (relative when
   it can be, absolute otherwise, a collection entry with its digest), and for a series its folder and patterns. What
   Save, Save as, Export and a zip do: ADR-0069 and ADR-0052, plus point 5. Missing, moved or changed: point 4.
   Fetching during a fit over a collection: one download per experiment at fit start (ADR-0069); a series of
   collection files is later work. Performance at 100,000 files: listing only, ADR-0026.

## Consequences

- A WISH temperature series loads in one step and saves as a few lines.
- A changed file in a linked series is fitted as it now is; users who replace data files in place should Reset.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A link per file or per point | Rejected: Save and open would cost per file, against the owner's rule for scans |
| Hash every series file at open, as RietX and PhaseSmith do on load | Rejected: 100,000 reads before anything shows |
| Ask the user to arrange files one folder per point | Rejected: data arrive as one folder per run with bank suffixes |
| Embed series data in the project | Rejected (ADR-0069): large series make projects and saves slow |

## Published sources

- M. Könnecke et al., *The NeXus data format*, J. Appl. Cryst. 48, 301–305 (2015), doi:10.1107/S1600576714027575.
