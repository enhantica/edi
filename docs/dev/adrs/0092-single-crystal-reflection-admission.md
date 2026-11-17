# 0092. Which single-crystal reflections a fit uses

- **Status:** Accepted
- **Date:** 2026-11-16
- **Implementation:** 🟡 Partially implemented — model, file items, edits, the Experiment page controls, the table's
  statuses and the statistics; the Report and the assistant's project summary follow
- **Priority:** High

## Context

A single crystal's fit used every measured reflection above the fit's cutoff (ADR-0050). Users need to leave out
reflections by their indices or by a range, leave out systematic absences or keep them, and merge equivalents, with
Rint and R-sigma reported. crysta's admission does all of it once per fit, in order: excluded by indices, excluded by
range, absent, merged, then the cutoff on the merged F². edi holds the settings, edits them and shows the result.

## Decision

1. **Model and file.** A single crystal carries `_reflns.merge` (`none`, `point_group`, `laue_class`) and
   `_reflns.absences` (`exclude`, `include`), each absent until set (absent: none, include); its `_excluded_region`
   rows name their axis, `d_spacing` or `sin_theta_over_lambda`; and `_excluded_reflection` lists reflections left
   out by their indices (with their equivalents under the merge mode). A time-of-flight single crystal merges
   nothing. A powder refuses the axis column and `_excluded_reflection`. The reader checks every item by crysta's
   rules, and the save goes through crysta's writer, which also writes the counts, Rint and R-sigma and each
   reflection's include status.
2. **Edits** (each one undo step): the merge mode, the absences setting, a region appended with its axis or its axis
   changed, and `toggle_excluded_reflection`, which adds the reflection's indices or removes them.
3. **Experiment page.** Above the reflection table, the merge and absences selectors, then the counts (measured,
   unique, used, excluded, absent), Rint and R-sigma (a dash when undefined), and a warning when the absences' mean
   I/σ is above 3. The table's last column shows each reflection's status (used, below the cutoff, excluded, absent)
   with the reason in its tooltip; a click there excludes the reflection by its indices or puts it back. The
   Excluded regions group of a single crystal has an axis column.
4. **One source.** The view reads `edi::reflection_admission`, which calls crysta's admission on the project the
   fit would build: no path in edi chooses or merges reflections itself.

## Consequences

- What a fit used, and why, is visible before and after the fit.
- A file without the new items behaves and saves as before.
- The admission is computed again on each edit of the experiment; its cost is one pass over the reflections.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| A per-row excluded flag in the reflection loop | Rejected: the measured rows stay as read; the exclusion is a list the user edits. |
| Exclude raw indices before merging | Rejected: SHELXL's OMIT names the reduced class, so the reflection's equivalents go too. |
| Merge time-of-flight repeats at one wavelength | Deferred: needs repeat detection by wavelength. |
