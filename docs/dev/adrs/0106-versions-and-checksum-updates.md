# 0106. Versions YY.N and checksum updates

- **Status:** Accepted
- **Date:** 2026-11-26
- **Implementation:** 🟡 Partially implemented — the release tools, the app, the feed and the Maintenance Tool follow
  it; one real update from an installed 2026.11.x on macOS or Windows is still to be done before a release uses it
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
   month. About: `Version 26.17 · 26 Nov 2026`. The GitHub release title: `EasyDiffraction 26.17 (26 Nov 2026)`.
   What's new: `26.17 · 26 Nov 2026`. Downloads: `EasyDiffraction-26.17-macOS-arm64.dmg`, and the same with
   `Windows-x64` and `Linux-x64`, and `EasyDiffraction-Offline-26.17-<platform>` for the offline kind. Old releases
   keep the titles and file names they were published with, and the site shows them so.
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
   puts it back after a rollback, and only a bundle that same operation kept (its token beside it): a backup an
   earlier update left, as one run by an older control script does, is dropped by the next swap and never restored.
   The control script removes the kept bundle once the update has succeeded with the new tool in place. An update that leaves the component alone keeps the installed tool. Linux has no separate tool and is unchanged. The
   installer protocol check updates a 2026.11.31 install from a 26.17 repository and checks the tool's checksum
   afterwards.

## Consequences

- Copies of 2026.11.x take 26.17 through the Maintenance Tool by checksum, but their own update check cannot read a
  `YY.N` feed, so the app does not show them the Update button; the Maintenance Tool's Update and a new download
  both work.
- Before a release uses this: one real update from an installed 2026.11.x on macOS or Windows, against a local feed
  built with `--sha-update`, checking the version and date shown, What's new, the tool's checksum and icon, and that
  a second Update offers nothing.
- A version that is neither form is refused by every tool and by the app (`26.0`, `26.017`, `05.1`, `2026.17`).

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| `YYYY.N` (2026.32, then 2027.1) | Rejected by the owner for `YY.N`; it sorts above 2026.11.31 by plain numbers but reads long. |
| A shown `YY.N` with a hidden internal version for updates | Rejected: the owner preferred one identity to a pair kept in step forever. |
| Ask 2026.11.x users to reinstall once | Not needed for the update itself, which the Maintenance Tool applies; a notice may still be wanted, since their app cannot read the new feed. |
| Count the 2026 counter from every old tag and draft | Rejected: that would count previews and withdrawn reservations too; the count is of the 16 published releases. |
