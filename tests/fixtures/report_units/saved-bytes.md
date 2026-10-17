Saved values and uncertainties use the documented decimal rounding rule. The old
input and saved hashes remain in their original manifests. `saved_iucr.py`
projects only an exact hash match from the retained saved-byte archive
through the independent Decimal oracle in `iucr_reference.py`. Existing
calculator, geometry and follower-flag adaptations are included before
matching that old hash. Paths, row order and all other bytes stay pinned.

`iucr-fullprof-before.zip` holds the original saved bytes for the two
five-bank NCAF examples absent from the older archive. Recover them with
`recover_saved_iucr.py --case <project-key> --saved-tree <ordinal-pin-tree>`.
The generator restores numeric lexemes from the input, requires every
complete recovered file to match its immutable old saved hash, then requires
the saved bytes to equal the independent IUCr projection. The current
writer cannot supply a new expected hash. Repeating a case replaces its
archive members deterministically.

The project-record adapter requires exactly one `_su_format.rule iucr_19`
line before comparing all remaining historical bytes. Missing, duplicated,
non-default and extra settings are rejected by the existing inventory gate.
No old fixture or historical hash is regenerated.

The archive also retains the scan structure with its later model-change pin.
Use `--original-tree` and `--file structures/cosio.edi` to archive that existing
witness: every selected file must already match its recorded whole-file hash.
