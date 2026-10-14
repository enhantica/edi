# Subscription provider connections

Status: Accepted
Date: 2026-10-15
Implementation: Partial; desktop ChatGPT candidate, live account proof pending
Priority: High

The first desktop connection implements OpenAI's [open-source local SIWC flow](https://developers.openai.com/siwc/token-sharing-open-source). It uses the user's ChatGPT subscription, dynamic registration, a stable host identifier, a system browser and a loopback callback. It never substitutes an API key or imports another application's credentials. The provider's issued client identifier is retained per verified account. A fresh connection identifier fences every sign-in and reconnect.

`assistant/native/chatgpt_connection.*` owns Qt networking and credential storage; the Qt-free controller (ADR-0037) owns project authority. PKCE, unpredictable state and nonce bind the callback to the current attempt. The callback requires the exact loopback Host, path and unique query fields. Token acceptance verifies the OpenID issuer, audience, nonce, expiry, subject and RS256 signature against the issuer's keys through upstream jwt-cpp. Required direct-use scopes and a bounded positive access-token lifetime are checked. Redirects are refused. Cancellation or sign-out invalidates pending network completions.

On POSIX, edi's own app-local connection directory and records are owner-only. Credentials are separate from projects, conversation history and exports. Sign-out invalidates active operations and removes the selected registration. Windows subscription sign-in refuses until an OS credential-store adapter exists; permissions must not be claimed there. Additional saved-registration selection UI remains pending.

The connection lists provider-visible models rather than inventing entitlement. Inference calls `/v1/responses` with `stream: true` and `store: false`; tools use the `edi` namespace. Model listing is not proof that inference succeeds for an account. Public text and complete function calls pass through `OpenAiStream`; successful terminal delivery waits for successful transport completion. The native connection stamps the captured request's project, revision and connection authority onto normalized events. Provider content cannot approve a plan.

This extends the existing native Qt network and worker boundaries; it does not replace the worker, editor or fitting engine. jwt-cpp v0.7.2 is vendored unmodified with its MIT licence, bundled picojson BSD licence and archive provenance. OpenSSL is already an application dependency.

The broader provider contract remains active: native Claude uses its own supported sign-in/runtime, not extracted subscription tokens. Browser delivery must investigate both a local companion and provider-approved hosted sign-in. This desktop candidate has neither implementation. Attachments, refresh recovery under all failures, account switching and platform secure stores need independent gates before full acceptance. An owner sign-in trial and a verified streamed read/approved mutation are required before reporting live readiness. No readiness follow-up timer starts on a prototype.
