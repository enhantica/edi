# External public-context retirement characterization

This is a separately selected technical characterization, outside the ordinary tests/unit/app input directory. It is NOT an expected-crash pass, a skip, a UI warning or a change to Qt’s public lifetime contract. The original retirement sequence and assertions remain in the existing test-owned proof method, selected only by the explicit true argument plus EDI_E11_CONTEXT_RETIREMENT_CHARACTERIZATION=selected. No production API is added.

Default actualContextLookups(ApplicationInfo) uses its false default, requires that environment variable absent, and strictly executes the full live context-property/context-object alias, replacement/notification, receiver/constructor, reentry, explicit precedence and scope-method matrix. It now checks live warnings before teardown and ordinary live teardown. The fixture chooses to keep its context until its Panel lease has been destroyed. That is the boundary of this live control, NOT a general requirement that objects must be destroyed before their creation context. The original ordinary owner QML remains byte-exact.

The public context-first survival/disabled-binding obligations remain in the explicitly selected characterization. It preserves real context death while the actual Panel survives, the same public input/notification, inactive-binding assertion and strict warning check. No unconditional return/expectFail/exception swallow/version check can convert the known crash into a pass. Current FAILED/UNQUALIFIED status remains distinct from any live-owner result. A future actual pass is a new observation requiring independent qualification, never an automatic acceptance from this selection.

An independent Qt-only reproduction, using only public QtCore and QtQml API, fails the same way when the surviving input changes, before the retired context is deleted or any later case runs. It loaded the same QtCore and QtQml binaries as the failing app runs. That supports this narrow reading only: no upstream patch or all-version Qt defect is claimed, and unexpected setup, import or live warnings stay red rather than being charged to this boundary by name.

In edi's production code, app-owned context properties live on the engine's root context, Main owns the Panel directly, and no production factory installs these builtin overrides into a disposable external Panel context. Ordinary Qt Loader and delegate contexts are still reachable and are not waived. The native known-slot, list lifetime, conversion and GC checks remain ordinary mandatory tests. A new external creation or retirement path, or a changed Qt, reopens this boundary.

## Explicit separate invocation

Run the same freshly built edi_app_tests binary and window setup as the live owner, in its own child process. Reuse the existing normal invocation/log/XML/phase/source-root wrapper, changing only the explicit input directory to this folder and setting:

    EDI_E11_USAGE_ACCOUNT_PHASE=<actual-native-or-original-phase>
    EDI_E11_USAGE_ACCOUNT_SOURCE_ROOT=<matching-genuine-source-root>
    EDI_E11_CONTEXT_RETIREMENT_CHARACTERIZATION=selected
    <matching-fresh-edi_app_tests> -input <matching-source>/tests/characterization/e11_t5_external_context_retirement <unchanged-normal-output/platform-options>

Record this actual QML input SHA separately; do not relabel the unchanged ordinary b065 owner as the invoked input. The CPP pre-engine log records selected mode/phase before the live factory; retirement-begin is recorded before the original sequence. Preserve raw exit/signal/XML/log and the last actually reached trace. A crash is FAILED/UNQUALIFIED, not an expected pass. Ordinary live runs MUST leave the selection variable unset and keep the original unit input directory.

Also confirm that the selection is refused without the flag, and that a selected characterization cannot be recorded as the ordinary live mode.
