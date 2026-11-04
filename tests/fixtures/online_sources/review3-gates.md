# Review 3 gate references and adaptations

Baseline: edi `1b14d72e`. The replay worktree uses that immutable production tree,
a frozen Python extension, an independently built Qt test runner and the pinned SDK.
Only test transport replies are scripted; the shipped parsers, download callbacks,
project adoption, tutorial actions and archive opener execute normally. HTTP fixture
requests stay inside the scripted transport. No external network is used.

Correctness references are the collection design note in relay
`knowledge/design/edi-online-data-collection.md`, committed fixture file bytes,
SHA-256 and ZIP member inventories, the unchanged owner catalogue selection and
scan checksum oracle, and state/ownership invariants. Tutorial inputs deliberately
use a cell length of 3.77 and a three-point pattern beginning at 21.5 with intensity
117.25 and uncertainty 0.75. These are fixture inputs, not production-derived pins.

| Before | After | Preserved intent |
| --- | --- | --- |
| Examples id `collection/easydiffraction/lbco-hrpt-project` | Bare id `lbco-hrpt-project` | Same origin `HRPT @ PSI`, same populated archive project |
| Selected scan payloads embedded in desktop/web QRC | Selected scan payloads downloaded in collection ZIPs | Exact independent filenames, checksums, complete dataset/metadata inventory |
| Resource observer mutates bundled payload addresses | Resource observer mutates downloaded archive/index addresses and live metadata linkage | Prefix, target, alias, metadata, index, hidden-resource and library/interface escapes still exercised |
| Bundled example copy worker | Collection fetch into ordinary archive opener | Writable independent working files, unchanged source ZIP and Save As |
| Preview exclusion plus required bundle call | Preview exclusion plus metadata-only resource declaration | Owner selection/order and exclusion of temporary look-check projects |

The cohesive archive/resource controls move from
`tests/integration/py/test_scan_extended_contract.py` to
`tests/system/py/test_scan_collection_delivery.py` with their leaf names and parameters
preserved. The local measured producer/archive fixture exceeds the integration bound;
the system tier retains both quick and full cadence. Explicit frozen-identity
migrations record every moved witness. The preview exclusion gate retains its name.

The public-surface adaptation from the preceding tests turn classifies `Collection`,
`Collection.entries`, `Collection.fetch`, `Collection.find`, `Collection.search`,
`Collection.source` and `load_collection` as reviewed public collection inputs.
The complete committed-surface inventory and calculation-option checks remain.

The existing unit-3 gates retain the design-note schema oracle, shared exact index,
Python/CLI/app parity and WebAssembly HTTP fixture coverage. The preceding turn also
replayed every 5xx and all four named server/proxy errors across search, index and
file download; those gates remain unchanged.

The single-source update follows relay decision `3e0ad149d`: before, the source
selector and Preferences expected separate EasyDiffraction and mirror rows; after,
the selector expects one EasyDiffraction row. Socket-free transports inject replies
for the two owner-declared ordered locations. Python and CLI intercept URL reads;
the app restores default location configuration only after both transports are
installed. Primary success and 404 controls prevent unconditional retry. Deferred
mirror answers also exercise the pending state before success or exhaustion.

Qt host fixtures live in separate system modules so each module's recorded setup
cost corresponds to the one host that module starts. The archive controls pay both
shared producer/resource fixtures together, matching the runtime writer's cost
accounting. Failed product gates remain explicit `UNMEASURED:failed-in-this-run`
rows rather than receiving the duration of their early refusal.
