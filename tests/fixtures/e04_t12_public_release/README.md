# Public-release acceptance references

The oracle transcribes the content review dated 2026-10-03, sections 0–9. Its digest identifies the complete report;
its counts are historical measurements, not exact assertions about later trees. The linked-library names were
observed with `ldd` on the existing application on that date. They augment the review's section 9 list, and do not
claim that a future binary has the same link set. The live link-set gate uses the current application when built.
System-library redistribution and platform-specific bundles still need manual review.

The visible local script interfaces exercised by the acceptance gates are:

- `python tools/public-release/scan.py --tree PATH`: secrets scan; a credential finding exits nonzero.
- `python tools/public-release/scrub.py --tree PATH`: re-runnable content scrub of a disposable local tree.
- `python tools/public-release/snapshot.py --source LOCAL_GIT_REPO --output NEW_LOCAL_PATH`: snapshot `main`, scrub,
  apply the reviewed preparation, and make a fresh single-commit local repository. It must not mutate the source.
- `docs/dev/public-release-checklist.md`: the settings and owner-operated cutover checklist.

These operations are local. Repository creation, remote pushes, renames and visibility changes are outside the
fixture contract. The synthetic snapshot source has two commits and changes an ordinary user document between
snapshots; acceptance requires the newer content, a repeatable scrub and a clean single-commit output.

The workflow gates inspect checked-in job policy. They do not claim live hosted CI or deployed Pages evidence.
A final operator check must read those results and settings through GitHub's API. Likewise, the content pattern
check supplements, rather than replaces, the final reviewed secrets scanner and redistribution-rights review.

The retained history archive replaces commit-object lookups with immutable
inventories and pinned bytes. `freeze_history.py` is an authoring command with
explicit pre-release revisions, never a runtime gate. Its directory census
keeps the complete original population as path hashes, so obsolete document
names need not appear in the public tree. API witnesses, public headers and
old example inputs remain independently pinned. The saved-metadata authoring
command first reproduces every old input and output digest, then checks that
all physical output files stay byte-identical after the descriptive edit.
Both sets of digests are retained; original numerical regression pins stay fixed.

`clean_history_metadata.py --report history-metadata.json` adapts descriptive
archive members after verifying their original retention hashes. Its write-once
receipt names each member and archive before and after. The cleaner rejects
changes to crystallographic records, executable Python, native tokens and
regression assertions. Only the hashes of adapted local metadata follow the
edit; original production-closure hashes and scientific data bytes stay fixed.
The same metadata adapter runs when `freeze_history.py` authors a new freeze,
including private design citations, upstream source pointers and personal run
paths. The compatibility ZIP receives the same adaptation, with saved-file
retention hashes updated without changing its accepted population or outcomes.

`author_pearl_header.py` runs FullProf only at authoring time, requires a
converged fit, keeps every measured numerical data row, and commits the output
with executable, invocation and before/after digests. No test launches it.
The FreeType link gate follows the FTL's preferred copyright attribution with
an actual year; it does not demand a different library's acknowledgement.
