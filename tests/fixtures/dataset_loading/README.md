# Dataset selection and save choices

The inputs are hand-authored four-point x/y/uncertainty files. Each file has the
same point count and distinct intensities, so a stale projection can look ready
without belonging to the requested row. Expected points always come from those
files, never from the live selected model.

| Witness | Before | After |
| --- | --- | --- |
| Scan row selection | Wait for four points, already true for the preceding row | Wait for the requested catalogue identity, completed calculation/read and edit-ready projection; then compare every point |
| Template promotion | Promote immediately after selecting another row | Wait for that row's completed view and compare its independent points before promotion; retain one-Undo restoration |
| Missing linked source | Save a small linked input using the default Include all choice | Explicitly choose linked-only, save, move the original folder, reopen, locate and compare every retained point |
| Relocated row | Wait for four points after relocation | Wait for the chosen identity and completed projection before the unchanged full point comparison |
| Replacement consumers | Wait for a four-point pattern after import | Wait for read/projection readiness, then retain the independent replacement and Undo comparisons |

A separate Include-all roundtrip saves the same linked inputs, moves the source
folder and reopens every included dataset. It must have no missing-data marker
and must retain every independently authored x/y/uncertainty value. This keeps
copying and linking as explicit, separately checked owner choices.
