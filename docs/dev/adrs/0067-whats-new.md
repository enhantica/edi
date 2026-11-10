# 0067. What's new from one dated changelog

- **Status:** Accepted
- **Date:** 2026-11-02
- **Implementation:** ✅ Implemented
- **Priority:** Medium

## Context

Home's What's new opened the docs site's What's new page. Users who do not follow the site never learn what changed
after an update, and the app had nothing of its own to show. edi has no numbered releases yet.

## Decision

- `website/surfaces/docs/changelog.md` is the one place changes are written. The docs site publishes it as its What's
  new page, and the app bundles the same file. A `## YYYY-MM-DD` heading starts a day's changes, newest first; a section
  without a date is not shown in the app.
- What's new on Home opens a window listing the days after the last one the user saw, or the newest day when nothing is
  new, with a Show all changes button in the footer beside Close, always visible, for every day, and a link to the
  site's page at the end of the list, which alone scrolls. Closing it marks the newest day as seen.
- The last day seen is kept in the settings (`WhatsNew/seen`). At start, when the changelog's newest day is later than
  it, the window opens once by itself. A first start with nothing stored takes the newest day as seen and opens nothing,
  so a new install, a test or a capture never starts with it open.
- A link in an entry opens only when it is a web address.
- A test run gives its own changelog through `EDI_CHANGELOG_JSON` (JSON text or a file: entries with a `date` and a
  `text` or a list of `changes`), in place of the bundled one.

## Consequences

- An entry added to the changelog shows on the site and, after the next update, in the app.
- When numbered releases start, the headings become versions and "since the last update" compares them instead of dates.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| A separate changelog for the app | Rejected: two lists drift apart; the owner asked for one file feeding both. |
| Opening the site's page only | Rejected: it shows nothing until the user goes looking. |

## Versioned release follow-up

[ADR-0072](0072-calendar-releases-and-application-updates.md) replaces the handwritten date-based
release source and date cursor with calendar release identities and notes from merged user-facing PR
titles. Its implementation reuses this popup, manual access and accessible presentation. The existing
dated implementation remains the prior art during that transition.
