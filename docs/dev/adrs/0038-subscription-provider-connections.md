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
