# Offline feedback probes

`driver.cjs` evaluates the production QML JavaScript in an empty Node context. It has no HTTP
transport, filesystem API or real clock inside that context. Requests name the module, operation
and JSON arguments; replies contain a result or an exception string.

The file probe extends `Payload.buildPayload` after its existing nine arguments with a list of
files. A file carries `name`, decoded `size`, MIME `type` and base64 `data`. The resulting payload
carries attachments with the retained name and scrubbed base64 data. The existing contact and
subject arguments retain their meaning. Limit refusal raises an error naming the applicable limit.

The timing probe calls `app/feedback/Likes.js`'s `eligible(state, now)` with UTC epoch milliseconds.
State carries `sessions`, `firstSession`, nullable `lastPrompt`, `fitSucceeded`, `fitting`,
`tutorial`, and `disabled`. It returns a boolean and uses the supplied time. This is a probe adapter
boundary: if the app uses a different internal representation, adapt the driver with the tests
maintainer while preserving these inputs and observations.

The native bar probe uses the production window's `likes.bar` item and its actual `Likes`
settings. It seeds session history away from clock boundaries and emits the fit model's finished
signal through a controlled QObject. Clock-boundary checks stay in the pure policy probe with
its injected UTC time. The UI probe keeps the real tutorial binding, observes live fit activity,
and intercepts the bar's transport. An unsupported offline endpoint
prevents external requests even if transport interception fails. Negative answers use the
window's existing feedback form; sending the like answer does not submit a problem report.


The 2026-11-17 zip ruling keeps this client boundary as per-file transfer records.
All file types are accepted within the same limits. Opaque bytes (including images
and videos) are unchanged; text bytes are scrubbed while preserving the remaining
Unicode and line endings. Long scientific inputs stay complete in attachments and
are not expanded into message, log or Copy report text.

The service groups non-image/non-video files into attachments.zip after creating
the issue; media remain inline, and the full log is also archived. That service is
outside the declared edi mount. These probes exercise the production client and
never claim to execute the service's zip assembly, issue creation or upload route.


The survey clock probe calls the production `Likes.surveyEligible(state, now)` in
that same library. State contains `sessions`, `firstSession`, `disabled`, `stopped`,
nullable `lastShown`, `sessionsAtShown`, `usefulWork`, elapsed `idle` milliseconds,
`fitting`, `tutorial`, `likesDue`, `barShown` for either bar in this session, and
nullable `otherShown` for the other bar's last timestamp. First offer needs five
sessions over fourteen days and a minute idle after useful work. Both deferral
controls use thirty days plus two new sessions. A completed or permanently dismissed
invitation has `stopped` set; the preference independently supplies `disabled`.

`Likes.eligible` additionally consumes `barShown` and `otherShown`. Both predicates
refuse an already used session and less than seven days since the other bar. Survey
also gives way to `likesDue`. The driver accepts a list of calls in one unchanged VM
so activity and priority can be rechecked without cached eligibility. Expected
answers come from the written timing rules; the driver computes none of them.

The native likes case now clicks Yes once, observes its already sent anonymous
answer and the Share feedback form, then cancels that optional follow-up. There is
no inline Yes stage. Don't ask again and its restart check use the actual Feedback
preference, and the Interface Feedback rows retain their real On/Off popup input.

Saved contact fields are nonempty during the native answer checks; anonymity is
verified across the entire answer, including nested metadata.
