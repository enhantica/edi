# 0063. One Help and feedback form

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

Users had a bug button opening GitHub issues, which needs a GitHub account and gives no way to attach what the app was
doing. Feedback, questions and ideas had no place at all. The service that receives messages is a small Cloudflare
Worker holding the only token; it can create issues in a private repository and nothing else. Its README declares the
message: `POST /feedback` with `kind` (`feedback`, `question`, `problem` or `idea`), `text`, and optionally `subject`,
`contact`, `app` and `log`; it answers 201, 400 or 429.

## Decision

- One form, Help and feedback, opened from Home and from the
  crash popup (ADR-0062). About 560 pt wide, so the note on what is sent takes two lines (narrower in a narrower app
  window), it opens scrolled to the top with the cursor in the message. In order: a one-line invitation, then the kind,
  a box of Share feedback (praise, complaint or both; the first entry and the default), Ask a question, Report a problem
  and Suggest an idea (values `feedback`, `question`, `problem`, `idea`), the crash popup opening on Report a problem;
  three optional fields on one row, Name, E-mail and Affiliation, kept in the settings for the next message; an optional
  subject, its hint following the kind; the message, five lines tall and scrolling beyond, its hint following the kind;
  "Include app version, system and log", ticked by default, its box in line with the fields; a short note on what is
  sent, the contact fields included; "Show what will be sent", which shows the message in the same field style, six
  lines in a monospaced font; Cancel and Send. The window never grows past the app's, and it shows at most one scroll
  bar, the app's: normally only the preview scrolls; when the app window is too short for the form, the form scrolls and
  the preview shows all its lines. A scroll bar is shown once the window has opened, when its content is taller than its
  room, and while scrolling. Send is off until the message has text and while it is sending. A sent message replaces the
  form with one confirmation, "Your message was sent. Thank you!", and the window closes by itself after about two
  seconds (Close closes it at once); reopened, the form is fresh, the contact fields kept. A failed one keeps its text
  and says why.
- The subject is sent as `subject`, trimmed, and left out when empty; it is redacted as the text is. The contact is sent
  as `contact`, holding only the fields filled in, trimmed; with none filled in it is left out. It is sent as written,
  since the user typed it to be sent.
- `app/feedback/Payload.js` builds the message (`buildPayload`) and sends it (`submit`). The form shows exactly the
  object it sends. `app` holds the version, commit, crysta build, Qt, OS and graphics backend from the run log's header;
  `log` is this run's log, or the crashed run's when the crash popup opened the form, cut to its header and its last
  40,000 characters.
- Before anything is shown or sent, the user's home folder and user name become `~` in the text, the app's details and
  the log, however they are written. Each is matched character by character, every character in any of its forms: as
  written in any case, as a JSON `\u` escape, URL-encoded once or twice (a file URL, a query, a form's `+` for a space,
  a support link), and for the home folder's separators either slash, a doubled backslash or JSON's escaped slash. So a
  value is found however its characters are mixed, as when a JSON writer escapes only the non-ASCII ones. A file URL
  keeps its own root slash. The user name is replaced only as a whole word, and an escape next to it counts as the
  character it stands for (the `F` of `%2F` is a slash, not a letter). The kind is one of the four fixed values and is
  never rewritten.
- Home opens the feedback form directly inside the app. Only web (http or https) addresses open outside the app.
- The feedback service's address is the `develop/feedbackAddress` setting, shown in Preferences. By default it is
  `https://edi-feedback.savanna-animas-0g.workers.dev/feedback`, so Send works out of the box. A user may change it or
  clear it; while it is empty, Send is off and the form says why. Earlier builds kept an empty address under
  `develop/feedbackEndpoint`, which is no longer read. The service answers 201 with the new message's number, 400 for a
  message it refuses and 429 when too many arrive from one place (five in ten minutes); the form thanks the user, says
  to try again later, or says sending failed. The transport is a function the form takes; tests pass their own and never
  use the network.  ## Consequences
- A log leaves the user's computer only when they press Send with the box ticked.
- Turning sending on is one setting once the feedback service is deployed; the app changes nothing else.
