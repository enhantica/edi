# ADR-0072: Calendar releases and application updates

## Status

Accepted for implementation.

## Context

The application currently derives its display version from git. ADR-0067 supplies What's new from a
dated, handwritten website changelog and records the last day shown. ADR-0071 introduces native
installers and online component repositories. The Updates controls in Preferences are placeholders.
Diffraction-lib demonstrates deriving release notes from merged PR titles and grouping them by labels.
Scipp demonstrates calendar versioning accompanied by an explicit compatibility policy.

## Decision

Use `YYYY.MM.SEQUENCE`: a four-digit year, release month and zero-based release sequence within that
month. For example, `2026.11.0`, `2026.11.1`, then `2026.12.0`. Every release in a month advances the
sequence, regardless of its contents. Release automation chooses the next unused version from the
release calendar and existing releases; rerunning the same release must not create another version.
Use the same release identity in the app, installer, component repository and GitHub release.

Merged PR titles describe outcomes for users and become release-note entries. Scope labels group
notes into Added, Fixed and Changed; they do not select major, minor or patch increments. Internal
coordination identifiers and implementation-only titles do not belong in public release notes.

The same versioned release notes supply the application's What's new popup. An upgrade shows the
changes after the user's previously used release through the current release, including intermediate
releases when versions were skipped. Reuse the existing popup and its navigation rather than creating
a competing viewer. This supersedes ADR-0067's date cursor and handwritten source for release notes;
the transition must preserve its accessible presentation and manual access.

An installed desktop app checks release availability in the background independently of Preferences.
When a newer release is available, show an Update button with a red border/text and a light red
background in the light theme, with an appropriate dark-theme counterpart. Preferences control
optional notifications, rather than whether the button can learn about an available update. Updating
uses the installed maintenance tool and preserves the existing unsaved-work close flow. After the
updated application starts, show the relevant What's new entries.

GitHub Releases hosts the downloadable online installers. GitHub Pages hosts the separate per-platform
repositories (`Updates.xml` and component archives). Each installer embeds its platform repository URL.
The release page is not a replacement for that repository. Initial publication uses the testing channel;
production publication follows successful platform qualification. Offline installers remain test inputs.

Calendar versions imply no API or project-file compatibility promise. The project schema keeps its
own version. Release notes explicitly identify breaking changes and migrations; a newer date does not
substitute for testing.

## Validation

Check month/year transitions, multiple releases in a month, retry identity and version ordering.
Verify that notes use merged PR titles, labels only group entries, and skipped versions contribute
all relevant notes. Exercise update checks with notifications disabled, unavailable/malformed feeds,
installation/update failures and unsaved work. Use local recorded inputs in tests. Verify the button
and release popup in both themes. Publish a release only after the installer and its component
repository have passed the platform checks.

## Sources

- [Scipp versioning and deprecation policy](https://scipp.github.io/about/about.html)
- [Diffraction-lib release drafting](https://github.com/easyscience/diffraction-lib/blob/master/.github/workflows/release-notes.yml)
- [Qt Installer Framework package versions](https://doc.qt.io/qtinstallerframework/ifw-component-description.html)

## Deterministic release planning

`tools/release/plan.py` takes recorded merged PR metadata, an explicit included-commit set and the
published version history. A PR contributes only when its merged commit is included. Existing scope
labels group titles; automation does not silently invent a scope, edit a title or include an unmerged
PR. Reject empty releases, duplicate identities, ambiguous labels and backwards calendar movement.
A retry of an already published source commit reuses its original identity and notes, even in a later
month. Numeric ordering applies to release sequences, including sequences above nine.

The versioned history has schema `edi.releases/1`. Both GitHub Markdown notes and the application's
release-range selection consume these recorded entries. Release preparation and publication remain
separate: creating a plan does not tag, publish, merge or alter an online component repository.
