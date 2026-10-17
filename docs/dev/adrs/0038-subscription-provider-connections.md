# Subscription provider connections

Status: Accepted
Date: 2026-10-15
Implementation: Partial; desktop ChatGPT candidate, live account proof pending
Priority: High

The first desktop connection implements OpenAI's [open-source local SIWC flow](https://developers.openai.com/siwc/token-sharing-open-source). It uses the user's ChatGPT subscription, dynamic registration, a stable host identifier, a system browser and a loopback callback. It never substitutes an API key or imports another application's credentials. The provider's issued client identifier is retained per verified account. A fresh connection identifier fences every sign-in and reconnect.

`assistant/native/chatgpt_connection.*` owns Qt networking and credential storage; the Qt-free controller (ADR-0037) owns project authority. PKCE, unpredictable state and nonce bind the callback to the current attempt. The callback requires the exact loopback Host, path and unique query fields. Token acceptance verifies the OpenID issuer, audience, nonce, expiry, subject and RS256 signature against the issuer's keys through upstream jwt-cpp. Required direct-use scopes and a bounded positive access-token lifetime are checked. Redirects are refused. Cancellation or sign-out invalidates pending network completions.

On POSIX, edi's own app-local connection directory and records are owner-only. Credentials are separate from projects, conversation history and exports. Sign-out invalidates active operations, attempts provider revocation and erases only the selected credential record. Nonsecret issued-registration and host mappings remain for provider-prescribed reuse; unconfirmed revocation or failed erasure is visible. Windows subscription sign-in refuses until an OS credential-store adapter exists; permissions must not be claimed there. Additional saved-registration selection UI remains pending.

The connection lists provider-visible models rather than inventing entitlement. Inference calls `/v1/responses` with `stream: true` and `store: false`; tools use the `edi` namespace. Model listing is not proof that inference succeeds for an account. Public text and complete function calls pass through `OpenAiStream`; successful terminal delivery waits for successful transport completion. The native connection stamps the captured request's project, revision and connection authority onto normalized events. Provider content cannot approve a plan.

This extends the existing native Qt network and worker boundaries; it does not replace the worker, editor or fitting engine. jwt-cpp v0.7.2 is vendored unmodified with its MIT licence, bundled picojson BSD licence and archive provenance. OpenSSL is already an application dependency.

The broader provider contract remains active: native Claude uses its own supported sign-in/runtime, not extracted subscription tokens. Browser delivery must investigate both a local companion and provider-approved hosted sign-in. This desktop candidate has neither implementation. Attachments, refresh recovery under all failures, account switching and platform secure stores need independent gates before full acceptance. An owner sign-in trial and a verified streamed read/approved mutation are required before reporting live readiness. No readiness follow-up timer starts on a prototype.

The native boundary now accepts the exact NativeDependencies bundle for HTTP operations, browser launch, protected
own-record operations and wall/monotonic clocks. Every required function is validated before external I/O. Production
construction supplies the fixed Qt networking, browser and protected POSIX record adapters in connection_services;
injection changes dependencies, never provider endpoints, JWT verification, callback binding or token visibility.
Each transport operation is cancellable, settles once, and is fenced by owner lifetime and native generation.
Incremental headers/body limits and owner-thread polling enforce the declared deadlines before unbounded buffering.

The normalized account catalog trusts only documented slug/display_name/visibility fields. Unknown visible models
remain visible but unavailable until the shipped, cited capability map supports them; upstream effort-shaped fields
are not trusted. Responses input retains original output items and complete function arguments across tool and user
continuations, and skips pending local acknowledgements until their actual terminal arrives. Rotation keeps an
exclusive own-record lease across read/renew/write in the production adapter. Revocation uses the fixed issuer's
validated discovery endpoint, bounded retries and local erasure independently of remote confirmation.

Both production archives compile against the locally qualified integrated SDK at this checkpoint. This does not
prove offline fixture behavior, actual authentication, secure stores on other operating systems, CI SDK qualification
or readiness. The real app-owner composition and public history/disclosure/UI integration are separate pending work.

The common receive boundary checks inclusive operation, inference idle and owning sign-in/revocation deadlines
before admitting headers, data or finish, including a backwards-clock refusal. Data cannot renew an already
expired idle allowance. Sign-in remains one attempt through catalog settlement. An unsuccessful inference HTTP
status never reaches SSE semantics. Complete function calls are retained until both the semantic response and
actual transport finish succeed; text may stream earlier. A transport failure discards those unexecuted calls and
settles the captured request as interrupted. The production Qt adapter preserves real network/protocol failures
after headers; only Qt's explicit HTTP rejection categories with a corresponding error status remain HTTP replies.

Native request fields and required nested objects/arrays/identities are validated before Qt conversions, replay
changes or I/O. Empty own-host associations and an absent record carrying bytes refuse. Each loaded own record
is charged while held, alongside current registration/credential/revocation objects; ownership transfer to the
current slot avoids retaining an uncharged duplicate. Per-record/aggregate excess has the declared resource code
and a bounded generated explanation. This scoped repair does not close pending request/rotation/socket/accounting
or real-UI retention matrices, nor establish live provider access or CI qualification.

Stateless continuation distinguishes retained evidence from replay eligibility. Original completed output
items from failed, incomplete or refused responses remain charged to the bounded local replay role, but
their provisional unexecuted calls are excluded from outgoing continuation. The same visible conversation
can Retry from its last completed response; a generated bounded failure explains that no tools ran.
Completed responses retain their exact original items. Before physical dispatch, every included original
function call must have exactly one correlated settled output. Later calls in a successful edit batch
receive the controller's original-bound stale-revision refusals. Inconsistent executed history instead
gets an explicit recovery refusal, without weakening the project/revision fence or inventing outcomes.
Account or explicit conversation replacement retires this replay scope.

The production protected-record adapter reports known per-record byte and registration-count exhaustion
through the existing internal typed resource refusal, as does the common injected-list count check.
Absent records, ordinary I/O and security-policy failures retain their distinct existing behavior; quota
refusal neither erases grants nor starts browser/provider work. This narrow category correction does not
establish pre-growth admission for directory materialization, racing file growth, outgoing buffers or
rotation aggregates. Actual live-provider and complete retaining-role verification remain owed.

Replay belongs to the current authenticated connection as well as its conversation. Full operation teardown,
disconnected/expired publication and an explicit new conversation retire originals, replay groups, marker and
blocked-recovery state together. Saved-account selection and same-account renewal both replace connection
scope, consistently with the core's normalized-history retirement. Omitting or retaining an optional host
conversation marker cannot carry an old account's public or opaque items into the new connection. Ordinary
unchanged-connection continuation and failed-response Retry retain their current replay scope.

The same per-record resource category applies to writes. Complete mapping and credential byte encodings
are both prepared/admitted before either record changes; HTTP token-body admission alone cannot establish
that the metadata-bearing persisted grant fits. The common save path and actual protected write reject known
size excess through the existing typed resource refusal before I/O. Ordinary write/permission/lock failures
retain their separate failure category, and sign-out still reports unconfirmed erasure truthfully. This does
not establish full pre-growth or rotation-recovery atomicity beyond the reviewed known-size boundary.

The partial app foundation now composes the default native connection through production main's
`configure_engine(engine)` → Session → AssistantViewModel chain. The ordinary ChatGptConnection constructor
supplies production Qt HTTP/browser/protected-record/clock services; the offline dependency constructor is
native-only and is not the preview launch. The production CMake executable target is `edi_app`, not the Python
extension or an independent test host. Its current local build prerequisite is the diagnostic integrated SDK;
the committed SDK pin and official CI qualification remain unresolved. Building this draft branch alone is
not a promise of a verified preview: real VM terminal-retention/failure-card behavior, current production smoke and live
subscription verification remain unfinished under ADR0041.

Decoder failure status and cause are distinct. Native feed and finish preserve the decoder's bounded
message/code; they describe an edi decoding failure rather than claiming a provider refusal. The VM
snapshots existing native last_error_code at the matching terminal emission before queued delivery can
replace it, then retains that category in the existing failure payload. The normalized core turn_finished
envelope stays unchanged. Known event/stage and required-field diagnostics are app-owned labels; arbitrary
exception strings, unknown event names and duplicate JSON member names are withheld. No raw SSE, headers,
body, credentials or hidden reasoning is logged. This diagnostic checkpoint does not resolve the unknown
live failure, HTTP admission metadata/recovery or partial-item semantics.

Returning OAuth callbacks may omit `client_id`: use the exact issued ID already bound to the pending
request, as required by [SIWC registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
Presence is distinct from absence: a supplied empty or different ID is refused. First dynamic registration
still requires the callback's nonempty issued ID and refuses `dynamic_agent_client`; the placeholder is
never used for token exchange. Existing state/code/PKCE/nonce, loopback, signature/audience and selected
account identity guards remain unchanged. No callback URL or credential is logged, and no saved store
is deleted to retry. This fixes a documented returning-callback compatibility defect; the owner's exact
callback and the separate live chat failure remain unobserved.

A terminal-array omission keeps its existing invalid_argument refusal and execution policy. Its bounded
reason reports only retained/terminal/missing/wire-unfinished counts and the first omitted item's fixed
known kind/status/wire-done classification; unknown or wrong-typed values receive app-owned labels.
First means map iteration, not stream order, and wire-done does not assert semantic completion. No IDs,
arbitrary strings, arguments, text or reasoning are exposed. All output shape/size, identity/position and
membership guards remain. This diagnoses the owner-reached finalization failure; it does not authorize
unioning omitted outputs, establish a missing reasoning item or claim that live chat succeeds.

The stream decoder retains its first complete bounded public feed failure. Repeated feed calls and
finish after that failure return the same code and encoded safe message before reading more wire or
emitting events. Both typed refusals and sanitized decoder exceptions use this path; their existing
categories, redaction and error-byte cap remain unchanged. An incomplete finish without a prior feed
failure retains its existing interrupted result. Constructing or copying the failure can still allocate;
this is first-cause preservation, not an allocation-failure delivery guarantee or live-chat compatibility fix.

Known-field decoder diagnostics cover direct and helper-mediated accessors, including item/part
containers and delta payloads for public text, refusal, reasoning and function arguments. Only exact
missing-member or expected-type errors for fixed app-owned field names are retained; arbitrary keys,
values and exception strings still receive a generic sanitized reason. The first-cause cache preserves
that same bounded reason through later feed/finish. Acceptance, execution and resource categories do
not change, and this does not identify the live omitted item or complete the broader diagnostic work.

Decoder rejection is latched without allocation before either catch handler prepares its diagnostic.
If preparation throws, later feed/finish remain rejected even when a terminal flag was already set;
they use a fixed bounded fallback rather than an unavailable cache. The fallback retains current
app-owned refusal categories through fixed labels; unclassified exceptions retain invalid_argument.
A fully prepared first safe reply is published separately and survives later reply-copy failures.
Fallback/reply construction can still throw under exhaustion, but cannot reopen the decoder, consume
more wire or publish a successful terminal. No permanent-memory delivery guarantee, resource-category
redesign or output/tool-policy change follows from this rejection fence.

### Completed nonexecuting originals and final call authority

Review50/owner prototype staging permits the existing active decoder to keep genuine finalized message/reasoning originals across an explicit compact or empty successful final output array. Known IDs retain their original positions/order; a compact offset cannot rebind them, and unseen terminal snapshots cannot steal positions. Message status remains required; the actual reasoning/function output-union status is optional, so absence stays absent only with genuine finalization/full call arguments and successful call membership. Explicit incomplete/in-progress/failed, null or wrong-type status never authorizes a completed known item. Partial or unknown originals cannot qualify for omission.

Both item.done and arguments.done now prepare call arguments without publishing normalized tool calls. All successful terminal originals/membership/status checks must pass first, then calls publish in original output order. Omitted executable calls still refuse; failed/incomplete/refused groups publish no calls. Native continues to hold them until the physical successful HTTP finish, preserving trailing-data/status/error/cancel fences. Complete terminal-only snapshots remain supported; no SDK accumulator projection, new provider backend or live-cure claim follows. Existing caps, immutable duplicates, first safe failure and replay/retention policy remain.

Finalized known nonexecuting originals require their published minimum shape before retention or replay eligibility: assistant role and content array for messages, required summary text entries and typed optional encrypted/content members for reasoning, and the required text/refusal/annotations containers of recognized content parts. The same checks apply before direct done, live-to-done and terminal-only item snapshots, and completed content-part events. Empty arrays/text and optional absent status remain valid where published; opaque metadata and encrypted bytes are retained unchanged. This is bounded known-shape admission, not a universal schema engine or an interpretation of annotations/reasoning. Whole-group validation still precedes all normalized call publication.


### Finalized streamed call authority

The owner observed a genuine completed item.done function original omitted from an explicit empty successful final summary after Hello works. Packet d5dec42b4/plan review54 selects item.done plus separate whole-response/physical success as the authority for this narrow omission class, supported by official streamed function-call guidance; this is not a universal final-summary guarantee. The existing omittable predicate runs before terminal snapshots install: a known function_call must already be finalized by genuine output_item.done with complete valid arguments and consistent item/call/name/namespace/position declarations. Added/arguments.done/partial/unknown items cannot gain this authority. Type-specific optional status stays literal; bad status refuses. Core closed tools/scientific approval remain independent.

All final originals still map by their own identity and known original order/positions; contradiction, duplicate/slot stealing and malformed companions refuse before normalized calls. Required output remains an actual array; genuine successful response, whole group/retention budgets, native HTTP/physical stream.finish, request/currentness and exact-once real outcome pairing are unchanged. Failed/incomplete/refused/late malformed/transport/cancel/stale groups do not execute or automatically retry. This changes the existing sole adapter, with no helper/backend, synthetic arguments or partial clean replay. Independent changed-class gates and actual owner post-change trial remain required; this source note is not runtime/CI acceptance.

FC1 enforces bounded typed consistency for response_id actually supplied on supported events and response.id actually supplied on response declarations/terminal envelopes; genuine absence remains legal. The retained identity is admitted before copying and private diagnostics never print it. FC2 keeps the actual first argument-bearing item declaration in the existing held original until item.done; repeated added declarations compare that immutable source, never the mutable/canonically respelled argument buffer. Initial argument strings seed genuine accumulation; wrong types/changed declarations refuse. A complete declaration must agree canonically; a progressive prefix is checked against actual accumulated bytes before arguments.done, allowing equivalent final spelling. Empty and legitimate progressive/duplicate controls remain valid. A brand-new declaration after argument completion cannot overwrite prior state. No extra retained declaration string, parser or API is added. All checks precede group/native/currentness/approval publication.
