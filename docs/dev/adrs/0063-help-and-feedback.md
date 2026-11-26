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
- The feedback service's address is the `develop/feedbackAddress` setting, kept in the settings file (Preferences
  stopped showing it on 2026-11-10). By default it is
  `https://edi-feedback.savanna-animas-0g.workers.dev/feedback`, so Send works out of the box. A user may change it or
  clear it; while it is empty, Send is off and the form says why. Earlier builds kept an empty address under
  `develop/feedbackEndpoint`, which is no longer read. The service answers 201 with the new message's number, 400 for a
  message it refuses and 429 when too many arrive from one place (five in ten minutes); the form thanks the user, says
  to try again later, or says sending failed. The transport is a function the form takes; tests pass their own and never
  use the network.
- The website's Get in touch form sends to the same service. The site build copies the default address from
  `Preferences.qml`, so the address has one source. The form's reason becomes the kind, its name, e-mail and affiliation
  the contact, its subject and message the subject and text, and `app` says only that it came from the website and from
  which page. The page shows the service's answer in the app's words.
- The website's Survey page (About → Survey, 2026-11-10) sends to the same service at `/survey` in place of
  `/feedback`: `event` (a name from `website/surfaces/docs/assets/survey/events.json`, `general` always, any other
  only between its `start` and `end` dates), `answers` (an object of the answered questions only), optional
  `contact` (`name` and `affiliation` when filled in, `email` only with the consent box ticked; the fields look like
  the Get in touch form's, the owner, 2026-11-10) and `app` as the Get in touch form sends it. The service labels the
  issue `survey` and `event:<name>` and refuses an event the file does not list or whose dates have passed; the page
  lists only the events open that day.
- **Attachments.** The form takes up to 5 files of any type, 5 MB each and 10 MB in total, by Attach files (a short
  link beside the log box, the detail in its tooltip) or by dropping them on the form; it lists each with its size and
  a way to remove it, keeps them with an unsent draft as it keeps the text, and past a limit says which one and keeps
  Send off. A picked or dropped file over 5 MB is refused by name and never read. A text file's content has the home
  folder and user name replaced, as the log does, and a byte sequence that is not UTF-8 becomes U+FFFD; its name is
  kept. An error popup's unreadable file comes in the same way, its first 5 MB when larger and marked as cut; the file
  is the one the load was reading when it failed, recorded where it was read. Each load attempt (an Open, an example's
  download, a Load data, a located data file) holds its own failed file (`LoadAttempt`), and its failure hands on only
  that one: a refusal that read no file, an earlier attempt or one still pending never lends its file to another. The
  web app's Attach files uses the browser's file chooser (`WebFiles.openFiles`). The message
  carries them as `attachments`, each `name`, `type`, `size` and base64 `data` (`Payload.buildPayload`). After the issue
  exists, the service uploads screenshots and videos one by one through GitHub's upload route and shows them. Every
  other file, with the full log as `log.txt`, goes into one zip uploaded as `<issue>-attachments.zip` to the feedback
  repository's `attachments` release through GitHub's release-asset API and linked (owner, 2026-11-17); entries keep
  their names, a repeated name (ignoring case) gets " (2)". The body keeps the log cut well under GitHub's limit; when
  the app's preview of the log is cut it sends the whole log beside it as `fullLog` (up to 5 MB). If the release asset
  is refused, text files go into the body and only those held whole count as attached. Tests never call GitHub. Its
  201 answer names the files it `attached` and says `logAttached: false` when the whole log did not arrive; the form
  names what did not arrive, never a plain success.
- **Attach AI work report** (owner, 2026-11-19), a link left of Attach files when the app has the assistant, attaches
  the assistant's work report as `work-report.json` in one click, with nothing to choose. It replaces an earlier copy
  of that file, follows the same limits, and says when there is no report yet. The form is 48 units wide (was 40).
- **The website's Get in touch form** takes the same attachments in the same way (owner, 2026-11-17): Attach files
  with the app's paperclip and tooltip under the message at the left, the file list with Remove below it, a drop on
  the form, the same limits and payload, and the same results (the service's reason, the files not attached).
  `website/build.py` writes the app form's wording and `app/feedback/Payload.js` itself into the page, so the limits
  and the attached-file check are one implementation; `website/checks/contact_form.py` drives it in a browser with the
  service stubbed. Its answer window has only Close, with no Copy report: a browser user can copy the message from the
  form, which keeps it after a failed send. After a message is sent, only the subject, the text and the files are
  cleared. Name, e-mail and affiliation stay, and the window says so, so the next message can go straight away (owner,
  2026-11-19).
- **Copy report.** After a send that fails (any answer but 201, no answer included) the form says why, with the
  service's or the network's own reason when one came, and shows a **Copy report** link beside it: the message as
  plain text (type, subject, message, contact if filled in, the app's details and the log when that box is ticked),
  attached files listed by name, so it can be sent another way (owner, 2026-11-17). The link is hidden before a send
  and after a successful one.
- **The likes prompt** (`LikesBar.qml`, rule in `app/feedback/Likes.js`). A slim bar above the status bar asks
  "Enjoying EasyDiffraction?" after a fit ends with its result, only once the app has started at least 3 times over
  at least 7 days, at most every 3 months (the same day three months later), and never during a fit or a tutorial;
  `Likes.eligible(state, now)` takes the clock as an argument, so tests pass their own. Yes, Not really and Not sure
  are neutral buttons with icons tinted green, red and amber; Don't ask again and a close cross sit a little apart on
  the right. Every answer is sent at once as `{"kind": "likes", "answer": "yes" | "no" | "unsure"}`, which the service
  labels `likes`, then opens this form: Yes as Share feedback, Not really as a problem, Not sure as a question; closing
  the form keeps the answer sent (owner, 2026-11-17). Controls are 32 px high with one 14 px text size. The counts live
  in the settings file's `Likes` group.
- **The survey invitation** (`SurveyBar.qml`, rule `Likes.surveyEligible`; owner, 2026-11-17), a bar of the same
  style: "Help shape EasyDiffraction: a 10–15 min anonymous survey on how you work and what you need." with Take the
  survey (external-link icon), Not now, Don't ask again and a close cross. First after at least 5 sessions over 14
  days, after useful work in the session (a project loaded or a fit finished) once the app has been idle about 60
  seconds, never at start-up; Not now or the cross asks again after 30 days and at least 2 more sessions; Take the
  survey or Don't ask again stops it. The two bars never show in one session and keep at least 7 days apart; the
  likes bar goes first when both qualify; both are checked again just before showing and never show during a fit or
  a tutorial. Preferences → Interface → Feedback turns each on or off.
- **Home's links** (owner, 2026-11-17), under Start in two columns of four: using the app (Tutorials, Documentation,
  What's new, How to cite) and talking to the developers (Help and feedback; Enjoying EasyDiffraction?, with the heart
  icon, which shows the likes bar at once whatever its timing rule; Take the user survey, with the external-link icon
  and the tooltip "About 10–15 minutes"; About EasyDiffraction). The form itself has no survey link: the survey is on
  Home and in the survey invitation.

**One kind of message (the owner, 2026-11-23, edi-feedback #102).** The app's form and the website's Get in touch form
have no type list and no subject: the message is the one text field, and its hint asks what the type list and the
subject asked before ("Feedback, a question, a problem or an idea: tell us what it is about. For a problem, what did you
do, what happened, and what did you expect?"), the same words in both forms, a sentence a line in the app's
(the site reads them from the app's dialog). Both send `kind` `feedback` and no `subject`; the service accepts a message without a kind, so it no longer
needs one. The type icons of the earlier list go with it. An error popup and the likes popup still open the form, with
their own text. The service labels every issue it files `⚠️ scope needed` and `⚠️ priority needed`
([ADR-0101](0101-issue-labels.md)) instead of the kind; issues filed before keep their kind label.

## Consequences
- A log leaves the user's computer only when they press Send with the box ticked.
- Turning sending on is one setting once the feedback service is deployed; the app changes nothing else.
