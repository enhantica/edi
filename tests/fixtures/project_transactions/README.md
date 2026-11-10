# Save and open transaction observer

Inputs: the committed edi tree, its pinned SDK installed at `build/crysta-prefix`, and the app and default Pixi environments. The builder archives committed sources; it ignores uncommitted production changes and refuses when those differ from the checkout.

```sh
export CCACHE_DIR=/tmp/edi-transaction-ccache
export CI=true
export GITHUB_ACTIONS=true
export GITHUB_EVENT_NAME=push
export GITHUB_WORKSPACE="$PWD"
pixi run -e app python -m tests.fixtures.project_transactions.build \
  --root "$PWD" --sdk "$PWD/build/crysta-prefix" \
  --output "$PWD/build/transaction-observer"
export EDI_TRANSACTION_RECEIPT="$PWD/build/transaction-observer/observer/receipt.json"
export PYTHONPATH="$PWD/tools/checks${PYTHONPATH:+:$PYTHONPATH}"
export EDI_FIXTURE_COST_LOG="$PWD/build/transaction-observer/fixture-costs.json"
pixi run python -m pytest tests/system/py/test_project_transactions.py \
  tests/system/py/test_save_exact_values.py tests/system/py/test_save_mixed_backgrounds.py \
  -vv --durations=0 -p fixture_costs
```

The browser observations use the pinned Chromium and Node toolchains resolved by the browser fixture. The Session observer holds asynchronous browser I/O and dataset reads at the native link boundary. It can also obstruct a real readback or refuse a selected delegated write; the other production operations still execute. The browser-handle observations execute the production JavaScript in Chromium.

The save-policy matrix observes each native Save, Save as, fresh/existing folder
and archive, copy, and browser save/download entry at the real Session boundary.
Ask must precede publication to a user destination; an operation may first
freeze an owned private cache. Cancel preserves input bytes and scientific state. Explicit Include all and Keep linked are checked
against independent input-file hashes and their physical source directory.
Both already-copied and linked payloads above the declared warning threshold
must ask. A matching answer controls the staged core writer. These observations
prove prepared contents, not the final browser transport or a packed browser UI.
The separate folder-reopen actors cover final publication and relocation.

Previously the dataset actor used point count as readiness, promoted a template
while its selected row could still be loading, and relied on the default save
policy for a linked-relocation case. It now waits for selected file identity,
completed calculation and a ready projection, explicitly chooses Keep linked,
and separately reopens an Include-all save after moving the source. All
independently authored point comparisons remain.

Continuation cases deliver current, stale, stray and reversed save replies after
project or source replacement, including safe admission refusal. Tutorial
actors independently exercise success and failure across repeated Next, Back,
Stop/restart, tutorial/project/source replacement and concurrent Save files.
Signal identity is a routing observation; physical stale-write protection needs
the additional operation-boundary witnesses.

The builder selects an exact public namespace/name and compares every overload
with the compiler's typed observer definitions. Nested helpers cannot stand in
for a boundary and a newly added overload cannot silently escape observation.
The host dispatcher latches a lost transport before another request or wait;
its unit controls exercise exited, timed-out and consumed-exit conditions.

Operation-boundary controls hold the actual checked collection transport. Two
independent local collections carry different complete file bytes; reversed
success and failure must leave the current operation's files intact and usable
by a later real loader. A canceled operation may not write or notify.

A listener on every actual model signal requests a second save while the first save is
still on the stack, both with the same project and a replacement owner. The
nested operation must ask independently or explicitly refuse before preparing
bytes. A surviving outer writer retains its original linked-data decision.
Ordinary route delegation remains covered by the save-policy matrix.

Held-value controls attach to every actual parameter change signal before any
page listener, plus general project publication and reflection-table signals.
Powder, single-crystal and shown-scan inputs still update their real chart
sources while held. Settled and busy release orders must publish one value
change and one general update, with one Undo for the whole operation.
The pointer actor previously assumed the first selected row was editable and
used the general recalculated signal as its chart receipt; it now selects a
known editable row through ordinary input, observes the chart source directly,
and requires zero general notifications while held.

The canceled-completion receipt also counts actual writable QFile opens and
QIODevice writes called by the copied app objects; those calls delegate to real
Qt. This distinguishes no write from a transient write later removed. A full
private-temporary-tree byte comparison includes hidden files, while complete
current input bytes are independently compared with the source collection.
Typed Qt reference sets must match before a call is redirected.

The nested decision is judged at the public request and actual writer boundaries.
A surviving outer writer must retain its original choice after the nested owner
changes the project's policy. Internal planning helpers can move into the save
operation without changing that contract. The ordinary editable source is used
for source replacement so startup overrides cannot hide that action.

Both tutorial staging and Save files exercise cancellation with and without a
successor, and both completion orders. A current Save files request retains its
explicitly chosen destination; no new request is needed to make an old source
operation stale.

An admitted request may freeze an owned cache before its independent question.
The reentry witness therefore checks user destinations, backing inputs and
browser publication while that question is pending; it does not reject private
cache materialization. A refused admission may not prepare data using the
outer operation's decision.

The pointer fixture prepares the actual project, Analysis page and selected row
once before actuation. Its measured setup cost is banked as a module fixture;
the drag case measures pointer press, moves, release and Undo separately.

Snapshot controls mutate the scientific model while a real save question or
browser picker is outstanding. They also change external input bytes without
changing size or modification time, add/remove an input, or grow it beyond the
large-save boundary. An output must retain the planned model and original bytes,
or obtain a fresh decision for the changed model and inventory. Explicit refusal
preserves the external source. All original save routes retain their separate
successful policy controls. Private operation caches before a question are
allowed; the older cancel witness now checks user destinations and publication.

Linked experiment controls first persist an admitted source A, then use the
ordinary file receiver, a copied or linked separate batch, or a scan conversion
and replacement with distinguishable authored source B. Every original save
route is exercised for powder and constant-wavelength/TOF reflections, keeping
links or including all data. The observer reopens the actual native destination
or materializes the actual browser write payload; an intermediate staging path
is never the final identity oracle. Include-all moves both original folders
before another reopen. Missing-source controls use the real Locate receiver.
Unsaved-model arrangements preserve a relative link's physical identity before
clearing its location, rather than inventing a broken relative source.

Default-policy controls count real source files and their exact byte sizes.
They include separate powder/reflection inputs, scans and a scan template that
explicitly links a distinct external experiment file. Saved and unsaved models
share the thresholds and explicit-preference controls. A required scan metadata
line remains valid while comment padding reaches each byte boundary.

Full-experiment ingress has a distinct file base: a native experiment declaration
in another folder links source B relatively. Its final saved link and measured
rows must resolve from that declaration's base. Reflection batch controls also
retain every nonempty dataset in an authored FullProf file, including repeated
indices, negative measurements and per-row TOF wavelengths. CW observations use
its five measured columns; a redundant wavelength column is not a row-layout
expectation.


The entry census in the neighboring operation-boundaries fixture starts with the
actual Session, project, search and Fit public headers. It separates project,
query, tutorial-file and report-output ownership. A new public entry requires an
explicit disposition; the census is an escape inventory, not a behavioral oracle.

Late-content actors mutate independently authored input bytes after planning or
at a delegated copy boundary. Complete inventories include hidden entries,
regular files, directories and symlink identities. Pipe, newline and Unicode
path spellings retain their ordinary filesystem meaning. Actual Qt and standard
filesystem calls from every linked static archive delegate unchanged; the actor
observes copied bytes and the actual rename, archive and browser-write frontier.
A recursive standard-library copy has entry and return observations; per-file Qt
copies also expose an interior mutation point. An unchanged-input control must
actually publish. Content refusal preserves the entire old user destination.
Raw linked scan inputs exercise ordinary in-place saves as well as copied trees.

Ownership actors retire a request from an actual synchronous subscriber, before
the publisher unwinds. Joined fetches independently retain X and Y dependencies,
including Fit, Download, Stop, partial failure and replacement. File producers
exercise examples, tutorial-aside examples, single and batch checked web inputs;
query cancellation has its own generation rather than a project-lifetime rule.
Only checked local file transport is delivered; uninjected HTTP refuses loudly.
The assistant chooser actor injects the local accepted callback into the real
Session chooser protocol and ordinary save entry, without claiming to exercise
an assistant service or permission producer.

Held-edit actors query dirty truth without emitting ordinary change signals,
then exercise actual native close/Open/Create/example guards, pending browser
opens, release, save and one Undo. The native actor receipt requires every
requested data row and the ordinary per-row initialization and cleanup.

A replay against the declared SDK is qualification evidence. A separate build
against a frozen local SDK can diagnose newer committed app boundaries when the
declared pin lacks their model fields; its receipt must name that limitation and
must never be reported as a pinned or exact-current-head replay.


Archive checks use the declared archive format: dot entries and cache artifacts
are excluded and supported file links are materialized. The output oracle reads
the produced archive bytes at the actual atomic publication primitive. Browser
checks compile the real serialization statements with only their external byte
sink and refusal delivery injected. A raw staging folder is not its archive.
Native folder publication still retains the complete carried inventory.

An attempted owner replacement is distinct from an admitted replacement. An
explicit busy refusal may preserve the original owner, whose operation must
then finish correctly. If the owner actually retires, no stale write or report
is permitted. Current-request controls require real completion and exact input
bytes. Ordinary Save and direct public save delegation share those boundaries.
