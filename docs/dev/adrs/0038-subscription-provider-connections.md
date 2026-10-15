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
