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

Release builds supply `EDI_RELEASE_VERSION` to the existing C++ version generator; ordinary developer
builds keep their git-derived identity. The installer source-build driver accepts the same version.
Validate the calendar syntax before generating C++ and fail configuration on invalid input. Release
preparation must pass its single selected identity to both the app build and component packaging;
a GitHub tag alone does not override a reused build directory's explicit version selection.

## Desktop update interaction and history transition

A managed numbered native release discovers its installed maintenance tool relative to the application.
It checks the small release-history feed after startup and every six hours, independently of notification
preferences. Requests have a timeout and a one-MiB limit; malformed metadata tries the configured mirror.
The feed cannot supply an executable path or command. Developer and browser builds do not launch a
native updater. Test mode suppresses automatic checks.

Preferences controls optional notifications and offers Check now with a visible result. The red toolbar
button remains available with notifications disabled and has explicit light/dark palettes. Updating
first runs the existing project/text/tutorial save-or-discard guard. Cancellation leaves the app open;
a maintenance-tool launch failure also leaves it open with an explanation. Only a successful launch
allows the existing application shutdown and assistant lifetime guard to finish.

Release preparation supplies the bundled version history through `EDI_RELEASE_HISTORY`. The existing
What's new viewer uses a numeric release cursor for that history, retains its dated cursor for legacy
builds, and includes skipped releases through the running version. The first numbered upgrade from a
legacy dated installation shows numbered history; a fresh install records its current release without
an automatic popup. Manual access and Show all changes remain available. Release titles are escaped
before Markdown display.

The read-only Prepare calendar release workflow collects the latest published history asset and only
merged PR metadata whose merge commit is in the candidate's ancestry range. The first calendar history
starts at the existing main commit recorded in `data/releases.json`; older dated notes remain available
in legacy builds. Authentication/server errors do not become an empty first-release history. Prepared
artifacts contain the chosen release, complete history and Markdown notes; no tag or release is created.
Installer jobs run these offline release-policy fixtures and the engine's small native portability
fixtures before the full source build.

Prepared release metadata must agree on source commit, calendar identity and complete history before
compilation. Application and installer packaging share these inputs; packaging refuses mismatched
staged metadata. Installed application qualification records the actual compiled version and SHA-256
of its bundled history, which must match the prepared inputs. This checks what was installed rather
than relying only on filenames or workflow environment variables.

Native qualification can consume the successful preparation run only when its workflow identity and
source commit match the current build. Download the immutable artifact ID after checking attempt,
expiry, size and exact bounded regular members. Version/history inputs are then shared by the app,
offline qualification and final online component repository. A prepared candidate uses stable URLs
but is not automatically published. Ordinary development jobs use testing URLs and unique test versions.

Artifacts include the workflow attempt in their names, so retries retain previous evidence. Testing
publication requires all platform repositories from the same attempt; rerunning only failed jobs
cannot silently combine different qualified sets. After all native jobs pass, a separate job retains
the exact prepared inputs for later promotion. Production publication remains a separate operation.

## Promotion and publication

Publish qualified calendar release is a separate, manual, main-only workflow. It promotes immutable
artifact IDs from a successful main qualification attempt, without rebuilding. Every native platform
and retained plan must have succeeded in that same attempt. Check ZIP hashes, platform/stable URLs,
source/version/history identity and actual installed application receipts; all platforms must build
the same complete crysta commit. Validate Qt component identities and original archive checksums.

Publication first creates or reuses a matching GitHub draft and uploads only missing, byte-identical
assets, without clobbering. Existing tags, differing notes/source/asset digests and stale histories
refuse publication. The tested repositories and matching release-history feed deploy together under
the shared Pages publication lock, preserving docs, web app and existing archives. Only then is the
verified release made public. An interruption leaves a retryable draft rather than regenerated
component archives. Documentation publication preserves the release feed as well as all other reserved
roots. No production release is dispatched from an unmerged feature branch.

References: [GitHub artifact downloads](https://docs.github.com/en/rest/actions/artifacts#download-an-artifact),
[release creation](https://cli.github.com/manual/gh_release_create),
[asset upload without clobber](https://cli.github.com/manual/gh_release_upload).

Both the ordinary developer app builder and the installer builder explicitly declare their selected
version and history on every configure, including the empty developer version. These values join the
ordinary build identity. Reusing a cache after a failed or manually numbered build cannot silently
retain a previous release version or a different bundled history.

The ordinary incremental web builder also declares its empty developer version and default history
on every configure, matching the ordinary native builder. It cannot inherit a manually selected
numbered release or another history file from an earlier CMake cache.


## Notifications and preview updates

An installed app checks at startup and hourly while open. The notification preference controls
automatic prompts. The red Update control at the bottom left remains available whenever the
app knows about a newer release. It opens the same release-notes dialog as a manual check or
an automatic prompt. The existing unsaved-work guard still owns the transition to Maintenance Tool.

Calendar previews install a testing channel marker. They read a separate release feed published
atomically with the tested component repositories. Their notes describe the candidate, and their
bundled copy supplies What's New after installation. Stable releases continue to use the
source-bound history generated from merged pull requests and the stable feed.

## Testing release drafts

A calendar preview builds the online installers for Linux, macOS and Windows.
After qualification, CI creates a GitHub draft marked as a prerelease, reserves
the calendar tag and attaches the verified installers. The draft uses the
release notes embedded in the installers. A maintainer publishes the draft after
review. GitHub generates the source archive links from the tag upon publication.

Testing components are published separately to the public Pages repository
under `/edi/repository/testing/<platform>/`. The application update feed is at
`/edi/releases/testing.json`. Publish the matching component repositories
before making the corresponding installer draft public.

## Public release notes

The public documentation renders published GitHub release descriptions at
build time, newest first, with a prerelease label when applicable. Publishing
a GitHub release requests a docs-only deployment from the default branch.
Draft descriptions are excluded.

A note can declare one or more affected interfaces with a hidden Markdown
comment before the note text, for example
`- <!-- interfaces: desktop,web --> Improve plot zoom.`. Use `desktop`,
`web`, `python`, `cli-python` and `cli-standalone`. Omit the marker for
general notes. The site renders these identifiers as labelled icons and
GitHub renders the note text. Scripts and notebooks share the Python API.

Managed desktop installations offer **Open Maintenance Tool** under
Preferences → Updates. Launching it uses the same unsaved-project flow as
starting an update. The missing-assistant dialog links to that tab so users
can add the component from the Maintenance Tool.
