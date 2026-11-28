# 0111. Updates carry only the components that changed

- **Status:** Accepted
- **Date:** 2026-11-28
- **Implementation:** 🟡 Partially implemented — the build, promotion and release checks follow it and a local
  install and update through the download redirect proves it on Linux; a real release has not used it yet
- **Priority:** High
- **Amends:** decision 4 of [ADR-0106](0106-versions-and-checksum-updates.md) (an unchanged component is no
  longer rebuilt and offered again) and the component archives section of
  [ADR-0071](0071-desktop-installers.md)

## Context

Every release rebuilt every component at the release's version. The Maintenance Tool offers a component whose
content checksum differs from the installed one (`packageNeedsUpdate` in Qt Installer Framework 4.11,
`packagemanagercore_p.cpp`). `repogen --sha-update` takes that checksum from the archive's bytes
(`repositorygen.cpp`), and the bytes change on every build: 7z stores file times, and signing changes the
binaries. So each update offered and downloaded every component, the AI assistant runtimes and the Maintenance
Tool included, although most releases change only the app. Each release also uploaded all of them again.

The owner asked on 2026-11-28 that an update show only the components that really changed and that a release
upload only those.

## Decision

1. **A component's input identity** is a sha256 over what it is built from, never over the built bytes:
   - its metadata folder, with `Version` and `ReleaseDate` taken out of `package.xml`;
   - the files `COMPONENT_INPUTS` in `tools/installer/package.py` declares for it, by their content: for the
     AI assistants (ChatGPT, Claude, GitHub Copilot) each runtime's recipe, which pins its version and archive
     checksums, and ChatGPT's licences;
     for the Maintenance Tool the Installer Framework pin and the tool's pages and resources;
   - a build number from the same table, raised when a component's build changes in a way its files do not show.

   The app declares no files and its build number is the release version, so every release changes it. A
   component missing from the table is treated the same way, so a new component is shipped until its inputs are
   declared. The build writes the identities into `installer.json` (`component_identities`).
2. **Each stable release attaches `components.json`**: for every platform and component, the release that last
   changed it (`version`), its `identity` and its archive asset names (`archives`).
3. **Promotion compares** each component's identity with the record of the latest published release
   (`tools/release/promote.py`). An unchanged component takes that release's entry instead of its rebuilt one:
   its `Updates.xml` element, `meta.7z` and `.sha1` files from that release's repository index, and its archives
   from the release its version names. Its version in the repository is that earlier version. A changed component
   keeps this release's version and files. A latest release without a record (one published before this decision)
   makes every component changed. A record that is malformed, or that disagrees with its repository index, stops
   the promotion, and so does an archive whose bytes differ from its `.sha1`.
4. **The release attaches only the changed archives.** An archive of an earlier version is not attached again: the
   download site's redirect already sends it to the asset of the release its file name names (ADR-0071). The
   complete repository archive still holds every archive, so a rollback to it needs no redirect.
5. **The Maintenance Tool then offers only the changed components**: an unchanged one has the same version and the
   same content checksum as the installed copy, so the framework does not update it. A first installation fetches
   it from the earlier release.

## Consequences

- An update downloads the app and only the other components whose inputs changed; a release uploads only those.
- A release must stay published while a later release refers to its archives. Deleting one breaks every component
  it last changed until a release ships them again.
- The repository promotion publishes is not the one the qualification installed: its unchanged parts are the
  bytes an earlier release published, which were qualified then. A missing declared input would keep an old
  component: that is why identities are wide (whole folders) and a new component defaults to always changed.
- An offline installer still installs every component at its own release. The online repository then offers the
  unchanged ones once, because their content checksums differ from the offline ones.
- edi-download keeps the previous release's small files for updates in progress, but only those of the previous
  version; files of an older component that release reused are kept only by that release's own index.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Compare the built archives | Rejected: archive times and signing change the bytes of an unchanged component. |
| Reproducible archives (fixed times) | Rejected: signing and notarisation still change the binaries, and it would not stop the re-upload. |
| Keep each component's version but rebuild it | Rejected: the archive name carries the version, so a rebuilt archive with an old version would clash with the earlier release's asset. |
| Decide the components by hand at release time | Rejected: easy to forget, and nothing would check it. |
