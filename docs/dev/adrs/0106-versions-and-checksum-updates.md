# 0106. Versions YY.N and checksum updates

- **Status:** Accepted
- **Date:** 2026-11-26
- **Implementation:** 🟡 Partially implemented — the release tools, the app, the feed and the Maintenance Tool follow
  it; edi-download's site build is still to write both feeds, and one real update from an installed 2026.11.x on
  macOS or Windows is still to be done before a release uses it
- **Priority:** High
- **Supersedes:** the version scheme of [ADR-0072](0072-calendar-releases-and-application-updates.md) (its
  `YYYY.MM.SEQUENCE`); the rest of ADR-0072 stands.

## Context

ADR-0072 numbered releases `YYYY.MM.SEQUENCE`. Users read a name such as `Installer-2026.11.30` as a date, and the
month restarting the sequence made the numbers jump. The owner chose the two-digit year and a counter within the
year, one identity everywhere (2026-11-26). The first such number, 26.17, is smaller than the last old one,
2026.11.31, by plain numbers and by PEP 440, so neither the installer framework nor the app would see it as newer.

An update by the Maintenance Tool also kept the installed tool: the signed tool of ADR-0091 was unpacked only by a
first installation, so a tool once installed was never replaced.
Once the tool was replaced, it still showed the old release's pages, which the framework keeps beside the tool.

## Decision

1. **A release is `YY.N`**: the year's last two digits and a counter within the year, with no zero padding (26.17,
   26.18, then 27.1 in January). The app, installer, component repository, feed, GitHub release and the future
   Python package carry the same version; the tag is `v26.17`. 2026 had 16 releases before (v2026.11.0, .8 to .14,
   .20, .22, .24, .27 to .31), so its counter goes on from them and its first `YY.N` is 26.17. A rerun of a release
   keeps the version its draft or release already holds. Old `v2026.MM.N` tags stay.
2. **One order** wherever both forms meet: `YYYY.MM.N` is `(YYYY, 0, MM, N)` and `YY.N` is `(2000 + YY, 1, N, 0)`,
   so 2026.11.0 < 2026.11.31 < 26.17 < 26.18 < 27.1. The release tools take it from `tools/release/versions.py`
   (through `plan.py`), the installer, Pages and site tools import the same file, and the app has the same key in
   `release_version_key` (`desktop_updates.hpp`). What's new on a 26.N app lists its releases, then the 2026.11
   releases as older history.
3. **How a version is shown** (the owner, 2026-11-26): no "v" where users read it, and the date with a three-letter
   month. About: `Version 26.17 · 26 Nov 2026`. What's new: `26.17 · 26 Nov 2026`. Downloads:
   `EasyDiffraction-26.17-macOS-arm64.dmg`, and the same with `Windows-x64` and `Linux-x64`, and
   `EasyDiffraction-Offline-26.17-<platform>` for the offline kind. Old releases keep the file names they were
   published with, and the site shows them so. The GitHub release title, which keeps its tag's "v", is
   `v26.17 · 26 Nov 2026`, and `v2026.11.31 · 25 Nov 2026` for an old release, with ` preview` after a preview's
   (the owner, 2026-11-28). Every release was renamed to it; the publishing tools still accept a release's
   earlier title, `EasyDiffraction 26.17 (26 Nov 2026)` or `v2026.11.31 (25 Nov)`.
4. **The feed is built with `repogen --sha-update`** for every component. Qt Installer Framework 4.11 then offers a
   component whose content checksum differs from the installed one, not one with a higher version, and still checks
   release dates. So installed 2026.11.x copies update to 26.17. A component whose content is the same in two
   releases is not offered; one rebuilt with other bytes but the same content is offered again, so packaging stays
   as reproducible as it is; the feed's version fields are shown, never compared.
5. **An update replaces the Maintenance Tool** on macOS and Windows. The component that carries the signed tool
   unpacks it on an update too, from operations that run only for a component being updated. On Windows its script
   calls `installer.setInstallerBaseBinary` and the framework swaps the tool once it quits. On macOS the framework
   leaves the staged bundle in place on an update, so an operation of the component runs `maintenance_swap.sh`: it
   can run again after any failure, never leaves the tool's place empty except between two renames, keeps the
   installed bundle as `MaintenanceTool.app.old`, and puts it back if it fails; its undo (`maintenance_restore.sh`)
   puts it back after a rollback. Qt IFW saves the operation and, in the next update, runs its undo before it unpacks
   the component again, so the backup carries a mark: the operation's token and the process running the update with
   its start time. The undo restores only in the run that kept the backup and otherwise touches nothing, so undoing a
   committed operation is harmless even after an update run by the released 2026.11 control script, which leaves its
   backup behind. The next swap drops a backup with another mark only while a usable tool is in place; when an
   update stopped between the renames left the backup as the only tool, the swap keeps it as its own until the new
   tool is in place or it is put back. Such an update saves no operation, and the app opens the tool only at
   `MaintenanceTool.app`, so the app puts the backup back itself: on start, and before Maintenance or Update opens
   the tool, a missing tool with a kept one beside it is renamed back and its mark removed, leaving any
   `MaintenanceTool.app.new` for the retried update to finish the swap with. It does so only once the process the
   mark names has ended (its number and start time, read with `ps` in the C locale by the scripts and the app alike),
   so an app opened while an update runs never takes the backup from a swap or undo between its renames; that
   installation still counts as managed, and the launch actions put the tool back when the update has ended. The control script removes the kept
   bundle once the update has succeeded with the new tool in place. An update that leaves the component alone keeps the installed tool. Linux has no separate
   tool and is unchanged. The installer protocol check updates a 2026.11.31 install from a 26.17 repository and
   checks the tool's checksum afterwards.
6. **An update also replaces the Maintenance Tool's pages**, on every platform. The framework keeps the tool's
   configuration, control script, style sheet and the `-r` resources (the English text and the images) in
   `MaintenanceTool.dat`, which the running tool writes at the end of every update by copying the resources the old
   file holds, so a new tool showed the pages of the release first installed. Every online build therefore ships
   `MaintenanceTool.rcc` with the app component: the installer's default resource (`binarycreator -rcc`) with the
   `-r` files added, since a 2026.11 file has no `-r` resource to keep them (`maintenance_resource.py`). The app
   component's script names it as the framework's `DefaultResourceReplacement`, which the running tool reads while it
   writes the data file: the file becomes its first resource and is deleted. A first installation does the same, so
   no copy is left behind. The protocol check starts from a release whose pages differ, and checks after the update
   that the data file's first resource holds the new release's control script, style sheet, text and images.
7. **2026.11.x apps get a legacy feed** (the owner, 2026-11-27). Their update check reads `releases/stable.json`
   (`releases/testing.json` on the testing channel) and drops the whole document when one version is not
   `YYYY.MM.N` (`release_changes` in `app/src/desktop_updates.cpp` at `v2026.11.31`), so a feed holding 26.17 would
   show them nothing. Apps from 26.17 on read `releases/stable-v2.json` and `releases/testing-v2.json`, which hold the
   full history as the old files did, in both forms. The release tools still write `releases/stable.json` for the old
   apps: every published `YYYY.MM.N` release unchanged, and one alias for the newest `YY.N` release, numbered
   `2026.11.<31 + k>` where `k` counts the published `YY.N` releases up to and including it, so 26.17 is 2026.11.32
   and 26.18 is 2026.11.33. The alias has the release's date, commit and notes in the old schema (`edi.releases/1`,
   groups Added, Fixed and Changed, each title one line of at most 512 characters with a pull request number above
   zero), led by an Added entry "This update is EasyDiffraction 26.17: releases are now numbered by year (26.17,
   27.1, ...)" that carries the release's first pull request number. Earlier `YY.N` releases leave this feed, so it
   never holds a version the old parser refuses. `tools/release/legacy_feed.py` applies that parser's rules, and the
   tools publish no legacy feed it rejects. Both feed bases in `data/distribution.json` serve the site that
   enhantica/edi-download builds from the release's `release-history.json` asset, so that build writes the two feeds
   with `legacy_feed.write_feeds` at the release tag: a feed the check rejects fails the build, and the previous site
   stays up. The publish workflow writes the feeds from the same asset first and stops the release on a rejection.
   The `pages/` and `offsite/` copies of `distribution.py` carry both feeds too, but no app reads them. A `YY.N`
   release must come from a commit whose app reads the `-v2` feed, since an app reading the legacy feed would rank
   26.18's alias 2026.11.33 below its own 26.17; the publish workflow refuses one that does not. The testing channel
   has no feed at the feed bases, which serve the stable repositories only, so testing-channel apps of either form
   find no update there. The alias is only a name in the feed: the Maintenance Tool still updates by content checksum
   (point 4).

## Consequences

- Once edi-download writes both feeds, copies of 2026.11.x see the update in their own app: it finds 2026.11.32 in the
  legacy feed, whose first note says it is 26.17, and its Update button opens the Maintenance Tool, which installs
  26.17 by checksum. The updated app reads the `-v2` feed and shows 26.17. Until then the feed bases serve the full
  history as `stable.json` and no `stable-v2.json`, so once 26.17 is in it neither old nor new apps find an update.
- Before 26.17 is published: edi-download's `main`, which the publish workflow starts, builds its site with
  `legacy_feed.write_feeds`, and 26.17 is planned and built from a commit whose app reads the `-v2` feed.
- Before a release uses this: one real update from an installed 2026.11.x on macOS or Windows, against a local feed
  built with `--sha-update`, checking the version and date shown, What's new, the tool's checksum and icon, and that
  a second Update offers nothing.
- A version that is neither form is refused by every tool and by the app (`26.0`, `26.017`, `05.1`, `2026.17`).

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| `YYYY.N` (2026.32, then 2027.1) | Rejected by the owner for `YY.N`; it sorts above 2026.11.31 by plain numbers but reads long. |
| A shown `YY.N` with a hidden internal version for updates | Rejected: the owner preferred one identity to a pair kept in step forever. |
| Ask 2026.11.x users to reinstall once | Not needed: the Maintenance Tool applies the update, and the legacy feed shows it in their app (point 7). |
| One feed holding both forms | Rejected: a 2026.11.x app drops the whole feed at the first version it cannot read, so it would show no update at all. |
| Count the 2026 counter from every old tag and draft | Rejected: that would count previews and withdrawn reservations too; the count is of the 16 published releases. |
