# 0100. Naming and first saving of untitled work as one operation

- **Status:** Proposed
- **Date:** 2026-11-23
- **Implementation:** 🟡 Partial: manual Create, Save, guard Save and the assistant's Create on untitled work; desktop
  fresh and Replace writes; the browser's claimed first save
- **Priority:** High

## Context

Untitled work (ADR-0017 "Work before Create") is named by the Create dialog, which then saves it. Before this the
request had no identity. The browser publication cleared `untitled` and recorded the place before the write had
settled; a desktop Replace moved the old folder aside around a save whose Boolean result did not say where it stopped;
a Save on untitled work opened Create and dropped what was waiting for it; and answers from a dialog or a question
could reach a later request or another project.

## Decision

1. **One operation per request.** `UntitledOperation` (`app/src/untitled_operation.{hpp,cpp}`) holds an `id`, unique
   within the session; its owner (the untitled project and its replacement generation); its origin (manual Create,
   Save, guard Save for Close, Quit, Replace or Open, or the assistant's Create); the dialog's form; its destination;
   and its state. `Session` holds at most one. Every callback, signal and QML call carries the `id`; a dialog can only
   answer its own. No session-wide naming flag carries this state.
2. **States.** `asking` (the Create dialog is open for it), `replanning` (the save asks about linked data, or plans
   again), `writing`, then exactly one of `saved`, `refused`, `rejected` (Cancel) or `superseded`. A settled operation
   never changes again and `untitledSettled(id, state)` is emitted once.
3. **Supersession.** A newer request of another origin, action or owner, a replaced project or the session's end
   settles the open operation `superseded` and writes nothing to the session. The newer operation is the current one
   before the older one settles, so a request a listener of that settlement makes supersedes the newer one in turn and
   no operation is ever dropped unsettled. The same request again while its dialog asks is the same operation; a guard
   Save is the same request only for the same unsaved-changes question. Every resumed callback checks that the session
   and the operation still exist, the id is its own, the operation is open and still the session's current one, and
   its project is still the open one; otherwise it settles `superseded`. Ids stay below 2^53, so QML holds them
   exactly.
4. **Only `saved` names the project.** The dialog's name, title, authors and description go into the save's snapshot,
   not the open project. `untitled` is cleared, the location published, "project saved" logged and the waiting action
   run only once the write is done, in that order. The waiting action runs only for the same session and project; on
   any other end it is abandoned.
5. **The data question belongs to the operation.** Its Cancel settles `rejected`; an answer for an operation that gave
   way changes nothing, not even the session's message. An answer given while the question is being asked moves the
   same operation to `writing`. An answer that cannot go on (the project changed, it cannot be held, the linked data
   is unavailable) and a replan that is refused settle it `refused`: every refusal is terminal, so nothing waits on
   it. On the desktop the Create form must name a folder; without one it is refused, and nothing is named.
6. **Desktop.** A fresh destination stays fresh across the question and any replan. A Replace records the identity
   (device and inode; on Windows the volume and file index) of the folder and of its `project.edi` when the user
   confirms it (`approveUntitledReplace`, for that operation's id). The Create dialog's OK carries the id and the
   confirmation to the deferred Create, which answers that operation only. A Replace is refused when the folder is
   gone, changed or cannot be read. The publish moves the old folder into a new private folder beside it, checks it
   there, moves it back if it is not the approved one, and removes it only while it still is, after the new folder
   is in place.
7. **Browser.** The first save writes into a stage of its own, `stage-<id>-<uuid>`, never the untitled place's key.
   Each stage has one claim record, `claim:<stage>`, naming the untitled place, the operation and the stage; no other
   stage ever writes it. It is taken once, live, before the stage is written; a revoke that came first left it
   revoked, and then it is never taken. After the stage is written, one IndexedDB transaction checks the claim and,
   only while it is still this operation's and live and the untitled place was not published from another stage
   (`claim:source:<untitled key>`), records the named place (the stage's key), removes the untitled place, records the
   source and marks the claim published. Supersession revokes the claim in a transaction on the same record, so
   whichever commits first decides; a published or revoked claim never changes again. A lost publish removes its own
   stage; a published one removes the untitled place's recovery copy. So two tabs recovering the same untitled place,
   even with the same operation id, never act on each other's stage and publish it once. A tab holds the Web Lock
   `edi-stage:<stage>` while it claims, writes and publishes. Listing the places removes a stage only under that lock,
   reading it again there in one transaction: no named place, and its claim revoked, absent, or live with no writer
   (then revoked first). Without Web Locks only a stage whose claim is revoked is removed. Ordinary named saves keep
   their single write.

   The publishing transaction also asks the app, inside it, whether the operation is still open and current and the
   staged snapshot still the project's (same revision, nothing refusing a save). If not, nothing is published and
   the claim is revoked: a changed snapshot settles `refused`, the untitled place and its recovery copy as they were.
   What that transaction committed is the result the session gets; removing files after it can fail without
   changing it. A project edited between that commit and the session's turn is named and saved where it was
   published, its newer edits kept unsaved, and nothing that waited for the save runs on them.

8. **Fenced handoffs.** Publications that can reenter go on only while the session and the project they belong to are
   still the open ones, checked before each: `Session::restoreProjectSetAside` after `replaceProject` and after each
   state write and signal (a refused restore leaves the project set aside); Save As into an existing folder after
   `takeStaged` and each location signal; Save As to a .zip after `publishArchive` and each location signal; and the
   untitled operation's own write, `saved` steps, error messages and place changes, which also need the operation to
   be still open and current.

## Consequences

- Save and guard Save on untitled work finish what they started once the project is named.
- A named place in the browser exists only from the commit that also removes the untitled one.
- Claim records live in the places store and are not listed as places.

## Alternatives considered

| Alternative | Verdict |
| --- | --- |
| Session-wide naming flags | Rejected: a flag cannot say which request an answer belongs to. |
| Check ownership in the browser callback after the write | Rejected: the named place is already durable by then. |
| Replace by path, checked at dispatch | Rejected: a folder made after the confirmation would be replaced. |
