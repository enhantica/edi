# Current dev assistant native integration

This is the existing independent real-Main host and deterministic native service
fixture restored from assistant `77ba02de3547c1884bd52c5eefa554cc58ff4ae3`, with a
default-Codex branch and read-only native/report observations. It loads production
`edi.app/Main` and its actual engine-owned Session, view model, controls and editor.
The offline stdio peer supplies pinned Codex 0.162.1 protocol events and observes
actual returned tool results; it never supplies scientific state or runs a model.

Target `assistant_real_owner_probe` belongs in the one implementation-owned kit.
Its CMake file is added after the app target in the ordinary root configure;
the current dev source assembly requires the product root as CMAKE_SOURCE_DIR.
It refuses standalone configuration and omits this native target for Emscripten.
Tests do not create another environment or build.
Its library dependencies follow the ordinary current app through `edi_app_module`
and the actual exported `crysta::crysta` target; the historical private
`crysta::process_defaults` target is not an installed SDK contract.
Use `EDI_ASSISTANT_UI_PROBE` for the exact binary and `EDI_APP_TEST_RUNNER` for
existing ordinary dev actors. Tests fail loudly when the required binary is absent.

The initial native tests use the unchanged frozen diffraction-lib Estimate oracle
and its nondefault settings, actual native pre-action state for Undo, and planted
unrelated bytes for report conservation. OFF/ON target refusal and continuation,
actual Estimate/save/reload, and automatic settled-step/final reporting are distinct
from source/resource conformance. The final-message gate is entirely within the
tests-owned peer: it waits for an explicit owned marker before completing its
provider turn, allowing observation of a real settled-step capture first.

No runtime test has passed merely because these sources collect or compile. Each
run must identify the production head, actual runner/module and engine/runtime
inputs. In particular, the separately elected local unchanged Crysta development
source does not become the declared pinned SDK or CI/release qualification. Old
assistant binaries/results are historical and cannot qualify the new dev app.

The finite review-6 gates reuse `edi_tests` with filter
`--test-case='E11 restore*,E11 bounded*,E11 preview*'`. The same graph adds
`assistant_owner_preview_probe`, using the same doctest main and current core
adapter, with only worker/preview translation units compiled in their supported
`EDI_WORKER_OWNER_THREAD=1` mode. Run it with `--test-case='E11 preview*'`.
Its effective commands must prove mode 1, and the ordinary carrier must prove
mode 0. This is a native diagnostic of that mode, not a browser build witness.
The frozen stamp codec comes from committed pre-integration dev e782; its visible
generator records the original SHA-256 and relocates exports without changing
the byte traversal. It is independent of the new bounded-capture implementation.
No scheduling-exception contract is inferred for asynchronous threaded delivery;
throwing scheduling Post cases belong to the supported owner-thread mode.

The finite research peer uses the official Codex `rust-v0.162.1` contract at
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`: `WebSearchItem.ts`,
`v2/WebSearchAction.ts`, `v2/ThreadItem.ts` and started/completed notifications
under `codex-rs/app-server-protocol/schema/typescript/`. Search/Open/Find are
actions of `webSearch`; results remain opaque JSON, including future fields and
unavailability evidence. No typed status/refusal/citation field is invented.
The process-exit fixture is an actual nonzero local peer termination; it does
not claim a provider/search service ran.

Interpreted actors also reuse actual manual Qt keyboard/IME input, the ordinary
FileDialog methods and current model controls. Postwrite Estimate failures are
raised from the real `projectEdited` publication callback and inspect the real
applied/Undo boundary. Busy-report sequencing occurs before queued owner
delivery; it neither polls a held writer nor adds a production test seam. Raw
Qt/QML stderr is retained. Undefined hook/property coding errors fail separately
from deliberate native tool refusals; other warnings remain available for audit.
