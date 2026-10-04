#  identity references

`baseline.json` and `baseline.zip` are a write-once REGRESSION BASELINE, generated
before any product implementation changed. They do not claim numerical correctness.
`generate.py` extracts the main-reachable fork point, attempts the project loader
on **every tracked directory**, and records every acceptance and refusal.
Candidate directories are identified by SHA-256 of their relative path, checked
against the complete fork-point directory inventory; accepted projects keep their
readable paths. This avoids copying obsolete operation vocabulary from rejected
legacy directory names. This inventory-only representation was adapted after the
freeze; all accepted inputs, saved bytes, hashes and old save refusals are unchanged. Accepted
input trees and every available saved output are frozen in the archive. Individual
saved-file hashes and the loaded extension hash live in the manifest.

The generator and gate prove ancestry against `refs/remotes/origin/main`, which
CI fetches even when its detached checkout has no local `main` branch. The gate
needs the anchor's tree and its ancestry to that fetched ref. A shallow clone
works when it contains that proof; otherwise it refuses, never skips or accepts
`HEAD` instead. The CI jobs executing this gate declare `fetch-depth: 0`.

The generation command is recorded in each manifest. Authoring ran that command
through `/tmp/-baseline-run.py`, using preserved installed extensions and
package sources; the wrapper only disabled editable rebuild and selected the
preserved artifacts. A git diff proved their product sources equal to the named
fork points. The persistent execution logs are
`<author-runs>/-freeze-crysta.log` and `<author-runs>/-freeze-edi.log`.

The population is fixed, including hidden tiers. A subsequent refusal never removes
an entry. One accepted project in each repo was already unsaveable at the fork
point: crysta's PbSO4 reconstruction and edi's LiF app example. Their old writers
refused calculation-only saves. Those entries retain their exact old refusal and
have **no byte baseline**; they are explicitly reported outside the five byte
comparison groups, not counted as identical saved output.

Edi updates wall-clock metadata during save. The comparison preserves raw frozen
bytes but masks only the values of `_metadata.created` and
`_metadata.last_modified` in `project.edi`, following the existing saved-tree
contract. Every filename, other metadata field, whitespace, comment and token
remains compared. The identity-delimiter classifier is independent of both product
parsers. Its negative controls change a physical value, an identity value, a
non-identity quoted token, literal embedded quotes and a comment.

Independent lexical references:

- [IUCr CIF 1.1 syntax](https://www.iucr.org/what-we-do/digital-standards/cif/cif1/file-syntax),
  paragraphs 9–19 and 22–25: matching single-line delimiters, whitespace-sensitive
  closing quotes, no backslash escaping, text-field boundaries and the ASCII character set.
  The token-spelling table is hand-written from these rules and packet D6 precedence.
- Literal canonical fit-state slot names are from `data/dictionary/parameters.yaml`
  in crysta, never from the slot walk being tested.
- [C++ path append](https://eel.is/c++draft/fs.path.append), paragraphs 2–3,
  [Python pathlib operators](https://docs.python.org/3/library/pathlib.html#operators),
  and [Microsoft filename rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)
  supply the root-name, device and alias witnesses.

`alias_observer.c` is an executable Linux escape witness: when the writer reaches
its second entity output, it asks the filesystem to create a hard-link alias of
the first and proves inode/device equality before recording arrival. The ordinary
writer must refuse create-new and leave the published destination unchanged.
This exercises the writer's real I/O entry without inventing a new helper API.
The separate platform probe asks Windows for an actual short path and checks
filesystem equivalence; on other hosts it probes a case variant. No obtained alias
is reported explicitly. Linux execution does not prove Windows path semantics or
8.3 generation. The domain-refusal branch still executes on Linux.
