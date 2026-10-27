# Assistant integration protocol

The public interface is `core/include/edi/assistant.hpp`; provider-specific Qt transport lives under `assistant/native/`. The controller is owner-thread only. Its borrowed Project and Worker must outlive attachment and pending deliveries. Host hooks forward public events, dispatch transport asynchronously and apply the closed typed Edit through the existing editor. `attach`, external `notify_changed`, cancellation and connection changes revoke stale authority.

Commands and events use strict JSON with schema `edi.assistant/1`; revisions are decimal strings. Provider calls bind connection, turn, request, project, revision and call ID. User approval has a separate trusted entry point. A call ID is idempotent only for the exact same complete invocation. Partial stream arguments never execute. Errors have `edi.assistant.*` codes; interrupted lifecycle events and malformed bound tool calls remain distinct. Batch edits validate the entire typed model domain and complete dependent relations on a copy before invoking the host edit door.

`OpenAiStream::feed` accepts fragmented SSE bytes; `finish` requires a completed terminal event. EOF, malformed UTF-8/JSON, duplicate fields, nonfinite numbers and bounded-size overflow refuse. The native adapter supplies request authority, never model-generated fields. A native response terminal is delivered only after the HTTP request finishes successfully, so tool follow-ups cannot collide with the previous request.

Independent probes include the real public header and link `edi::core`. The tests lane owns `assistant_contract_probe`; production provides no test JSON-lines executable. Build through the normal `app-build` environment, optionally selecting that target via `EDI_APP_TARGETS`. A locally supplied compatible `CRYSTA_SDK_DIR` is diagnostic only and does not replace release/CI SDK proof.

Current slice: parameter inspection, diagnostics, explicit plan approval, typed parameter/free edits, isolated single/joint real FitJob trials and checked result adoption. Scan artifact transactions, complete baseline-objective establishment, product skill resources, attachment transfer, native Claude, browser companion/hosted delivery and native project conversion remain owed. A missing recorded comparable baseline prevents automatic adoption rather than inventing an improvement.


Developer native helper input is provisioned with `pixi run -e app assistant-runtime` before a
native CMake configure. `python tools/deps/provision-assistant-runtime.py --offline` uses the same
canonical Pixi pin and retained verified archive when developing offline. CMake consumes the
published `build/deps/codex/provisioned/<target>/input.json`; missing or changed input fails closed.
The installed app does not depend on this developer Python/Pixi provisioning path.

Official assistant task threads are durable and reconnect by their original opaque thread ID only
under the same actual project/account/disclosure. `thread/resume` requests `excludeTurns=true`:
Edi keeps its own existing public rows and never synthesizes or replays uncertain scientific calls.
Ordinary work has no task idle/total timeout; individual protocol/startup/auth limits remain bounded.
Preferences AI offers the current-or-last bounded diagnostic JSON and Copy, independently of a
saved project. Project-local settled/final reports continue through the same native writer.
