# 0109. Replacing the Maintenance Tool's own files during an update

- **Status:** Proposed
- **Date:** 2026-11-27
- **Implementation:** ⬜ Not implemented
- **Priority:** High

## Context

Since [ADR-0106](0106-versions-and-checksum-updates.md) an update replaces the Maintenance Tool. On macOS an
operation of the tool's component swaps the signed bundle in with two renames and keeps the installed one as
`MaintenanceTool.app.old` until the update has succeeded, and the app puts a kept bundle back when it finds no tool in
place. The owner asked on 2026-11-27 for four things that design did not give:

1. **Coordinated recovery between the app and the update.** The app decided whether an update was still running from
   the process named in the backup's mark. A tool force-quit during the swap leaves its shell running, so the app saw
   a dead process, put the backup back, and the shell then moved the new bundle into the restored one. The mark's
   start time was local time, so an app in another time zone read it as a reused process number. Two app instances
   could both restore and leave neither a tool nor a backup.
2. **Rollback proven on every system.** The installer check proved it strictly on macOS only.
3. **The Linux tool's libraries.** The Linux tool loads its Qt libraries from `installer-runtime/`, which the app
   component carried. An update first undoes the operations the installed release saved for that component, which
   deletes the old runtime, then unpacks the new one; when it then fails, its rollback deletes that too, and the tool
   can no longer start (measured on CI: `libxkbcommon-x11.so.0` missing).
4. **Nothing left behind after a successful update, whichever tool drove it.** An update driven by a 2026.11 tool runs
   that release's control script, which does not remove the backup, and the swap removed the staging folder only when
   it was empty. The owner's Mac kept both after an update from 2026.11.27. On Windows the staged
   `maintenancetool\MaintenanceTool.exe` was never removed.

The macOS bundle and the Linux runtime are the same thing to an update: a folder the tool needs, which the tool's own
update replaces while the tool runs. So the runtime takes the bundle's design rather than a second one.

## Decision

1. **One lock for every writer of the tool's files.** The lock is `<target>/.MaintenanceTool.lock`, an empty file that
   stays between runs, since deleting a lock file that others may be locking races. Every writer holds an exclusive
   lock of the `flock` family on it:
   - The swap, undo and cleanup scripts wait for it up to 60 s, through `/usr/bin/lockf -k -t 60` on macOS and
     util-linux `flock -w 60` on Linux, whichever exists. Each script runs itself again under the lock when
     `EDI_MAINTENANCE_LOCKED` is unset, setting it for that run, and passes the tool's process number from before
     that step as `EDI_MAINTENANCE_TOOL_PID`. A lock not taken in time exits 1, so a swap fails and the Framework
     rolls the update back.
   - The app takes it without waiting (`open`, then `flock(LOCK_EX | LOCK_NB)`). A busy lock means a writer is at
     work: the app changes nothing, still counts the installation as managed, and the Maintenance and Update actions
     try again. macOS `lockf(1)` takes a flock-style lock, so the app and the scripts exclude each other there as on
     Linux.

   The kernel releases a lock when its holder ends and when the machine restarts, so neither a killed tool nor a
   stopped machine needs a guess about who is alive. The lock belongs to the script, not to the tool, so a tool quit
   in the middle of a swap leaves the swap to finish under its lock.

2. **The run mark is kept apart from the lock.** `<item>.old-token` holds `<token> <tool pid> <tool start time>`, the
   start time read with `ps -o lstart=` under `TZ=UTC0 LC_ALL=C` the same way in the swap and the undo. It answers one
   question: did this run keep the backup. The undo of the same run matches it and puts the backup back; a later
   update undoing the saved, committed operation never matches and changes nothing. The app never uses the mark to
   decide whether it may put a backup back; it reads it only before a cleanup (decision 5).

3. **One swap, undo and cleanup for two forms.** The scripts take the item and a probe, a path inside the item that
   exists only when the item is usable:

   - `maintenance_swap.sh <target> <token> <item> <probe>`
   - `maintenance_restore.sh <target> <token> <item> <probe>`
   - `maintenance_cleanup.sh <target> <item> <probe>`

   | System | `<item>` | `<probe>` | The tool's binary |
   |---|---|---|---|
   | macOS | `MaintenanceTool.app` | `Contents/MacOS/MaintenanceTool` | the item itself, signed on its own (ADR-0091) |
   | Linux | `installer-runtime` | `dependencies.json` | written by the Framework from its own binary |

   The tool's component unpacks the new item to `<target>/maintenance-update/<item>`, and its `Execute` operation runs
   the swap with the undo as `UNDOEXECUTE`. The staging folder's name differs from the tool's even on a case-insensitive
   disk: releases before used `maintenancetool`, which such a Linux disk cannot hold beside `MaintenanceTool`. Before
   the Framework unpacks anything (`beginInstallation`), the component's script has the swap, with `claim` as its last
   argument, write `claim <pid> <start>` for the running tool into `maintenance-update/.claim` under the lock; without
   it, or without the tool's start time, the update stops there. The swap likewise marks nothing without the start time,
   which alone tells the tool from a later process with the same number. Under the lock the swap moves `<item>` to
   `<item>.old` with the mark beside it, moves the staged item into place, and removes `<target>/maintenance-update`
   with whatever is left in it, such as a Finder `.DS_Store`. It can run again after any failure, and a failure puts the
   kept item back before it exits 1. A backup with another mark goes only while a usable item is in place; otherwise it
   is the only copy, left by an update stopped between the renames, and the swap keeps it as its own. On Linux the
   operation runs on a first installation too, where there is no item yet and the swap just moves the staged one in.

   On Linux the runtime leaves the app component. The tool's component (`org.easydiffraction.app.maintenancetool`)
   now exists there too and carries only `maintenance-update/installer-runtime/`, so every system's release carries the
   tool's component. Since the runtime is never unpacked in place, no undo deletes the runtime in use: a rollback puts
   back the runtime the same run kept.

   Windows has no shell and keeps ADR-0106's path: the component's script calls `installer.setInstallerBaseBinary` on
   the staged tool and the Framework replaces the installed tool once it quits. The Framework writes
   `MaintenanceTool.exe.new` from the staged tool as the update's tool quits, deletes it, and renames the new tool into
   place once the tool has exited (`writeMaintenanceTool` in Qt Installer Framework 4.11), but goes on when it cannot
   delete it. So the component's script unpacks its archive, one file `MaintenanceTool.update.exe`, into a folder of
   this run's own, `EasyDiffraction-MaintenanceTool-<time>-<random>`, in the user's temporary folder (`%TEMP%`, or
   `%LOCALAPPDATA%\Temp`; without either the update stops) and points the Framework there. Neither an installation nor
   an update puts it in the installation folder, a copy the Framework fails to delete stays in the temporary folder,
   and no tool an earlier run left can stand in for this run's. No operation of ours handles it, so none can be saved
   and replayed by a later update or a removal. The component's script settles it itself:
   - `beginInstallation`, before anything is unpacked, removes every `EasyDiffraction-MaintenanceTool-*` folder earlier
     runs left: emptied by the Framework, or left by a run that stopped.
   - After any run that did not succeed (`installer.installationFinished` with another status than success), it
     removes this run's folder, trying for ten seconds while something holds the file, and logs it if the folder stays.
     The unpack's own undo cannot: it leaves out the file the Framework is to write from (`ExtractArchiveOperation` in
     4.11), and a run can fail before any operation of this component was recorded.
   - After a successful update, if the file is missing because the unpack failed and the user ignored it, it unpacks
     the component's archives again, which the Framework keeps for the whole run, before the Framework reads the file;
     if that fails too, it tells the user the Maintenance Tool was not updated.

   Each command runs `cmd.exe` in the temporary folder and names only the run's folder, never a path.

4. **The app puts a kept item back.** On start, and before Maintenance or Update opens the tool, the app takes the
   lock; when it finds no usable `<item>` but a usable `<item>.old`, it moves the kept item back and removes its mark,
   leaving any staged item for a retried update. The lock alone decides; the mark plays no part. This holds for the
   bundle on macOS and for the runtime on Linux, whose tool cannot start without it.

5. **Cleanup after a successful update, in three layers.** `maintenance_cleanup.sh` removes `<item>.old`,
   `<item>.old-token` and `<target>/maintenance-update` under the lock when `<item>/<probe>` exists, and nothing
   otherwise; it also removes a `maintenancetool/` an older release staged into, when that is a folder and not the
   Linux tool itself on a case-insensitive disk. After a rolled back update it runs with `release` instead: it drops
   this run's claim and the staging folder if nothing else is in it.
   - The swap removes the staging folder as soon as the new item is in place.
   - The tool component's script runs the cleanup on `installer.installationFinished` when an update has succeeded,
     and the release when it has not.
     Component scripts come from the repository being installed, so the new script runs inside an older tool too.
     This is the only cleanup during an update: the control script no longer removes the backup itself. It has to wait
     for that signal, since the backup is the rollback's until the update has succeeded, and the Framework has dropped
     the rights it gained for a protected folder by then. So the script records in `beginInstallation` whether the
     update holds such rights, and takes them again for the cleanup: the Framework keeps its elevated helper running,
     so this asks nothing (`RemoteClient::setActive` in Qt Installer Framework 4.11). The app component's script does
     the same for the runtime copy (decision 8).
   - The app runs the same cleanup at start on macOS and Linux, under the lock and with two more guards, since an
     update unpacking holds no lock. It leaves `maintenance-update/` alone while the tool its claim names runs,
     whatever the folder holds yet; a folder without a claim, or whose tool has exited, is left over and goes. It
     removes `<item>.old` and its mark only when the tool the mark names is not running. For both it reads
     `<pid> <start>` and compares the start time with `ps -o lstart=` under `TZ=UTC0 LC_ALL=C`, as the scripts do, on
     Linux too. A wrong "running" only skips a cleanup that the next start tries again.

   During the one update that brings this decision an older tool still runs its own control script, which removes the
   backup without the lock once the update has succeeded. That removal and the new cleanup remove the same files and
   either may come first, so they overlap harmlessly.

   On Windows the update leaves no staged tool in the installation (decision 3), and the app component's script
   removes the `maintenancetool\` folder releases before staged into in `beginInstallation`, before anything else
   changes. The update holds the rights it gained for a protected folder such as Program Files there, and a folder that
   cannot go stops the update with nothing changed, where a failed operation would let the user ignore it. The app
   component is in every update, the tool's only when the tool changed. The app touches no Windows staging: it cannot
   tell whether an update in another session needs it, and without it the Framework would write an unsigned tool
   (ADR-0091). The command that removes the old folder runs `cmd.exe` in the installation folder and names only the
   folder, so no part of the folder's path, which may hold characters `cmd.exe` expands, reaches it.

6. **Purge.** On a successful uninstallation the control script removes `<item>.old`, `<item>.old-token`,
   `maintenance-update/` and `.MaintenanceTool.lock` (on macOS an older `maintenancetool/` too), and on Linux
   `installer-runtime/`, which no operation owns any more; the uninstalling tool has already loaded its libraries. On
   Windows it removes only a lock file, if one is there.

7. **Accepted window.**
   - *An app built before this decision, running during the one update that brings it.* It does not take the lock and
     still reads the mark, whose start time is now in UTC, so outside UTC it can read the mark as a reused process
     number and take the backup in the moment between the swap's two renames. The window lasts milliseconds, once.

8. **The first Linux update off a release whose app component carries the runtime.** Qt Installer Framework 4.11 runs
   that release's saved undo of the app component before any operation of the new release, which deletes
   `installer-runtime/`, and a rollback undoes only the new release's operations. The Framework calls each component
   script's `beginInstallation` before that undo, so the app component's script keeps the runtime there, and stops
   the update when the copy or the lock fails, before anything has changed:
   `maintenance_swap.sh … copy` puts a copy of a usable runtime (hard links where `cp -l` works, a plain copy
   otherwise) at `installer-runtime.old`, marked for this run as in decision 2. `maintenance_restore.sh … copy` then
   settles it: the copy goes back when no usable runtime is in place and is dropped otherwise. It runs as the app
   component's first operation and that operation's undo, and on `installer.installationFinished` after a success or
   a rollback, so a failure anywhere after the undo, an unpacking error included, leaves the original runtime. A swap
   of the tool's component in the same update finds no usable runtime, takes the copy as its own backup, and its undo
   puts it back. After a successful update no copy is left, and no undo owns the runtime any more.
   An update offers only components already installed, so on Linux the app component depends on the tool's
   component: the Framework adds a missing dependency of a component it updates, and the first update installs the
   tool's component with the new runtime.

## How CI proves it

- `tests/fixtures/installer/check_maintenance_swap.py` runs the real scripts in the macOS and Linux installer jobs, for
  both forms: the swap and the same run's undo; a later run's undo changes nothing; the swap removes a staging folder
  holding a planted `.DS_Store`; the cleanup removes the backup only with a usable item in place. The app's recovery,
  ported with `fcntl.flock`, declines while a swap or an undo is paused under the lock (an `mv` stand-in that waits on
  a FIFO between the renames, so nothing sleeps); with the tool process killed while the script is paused it still
  declines, and the script finishes with one correct item; with the whole process tree killed it puts the backup back;
  a swap and an undo run under different `TZ` still match; two recoveries started together leave one usable item.
- `tools/installer/protocol_check.py` drives the real Framework on each system:
  - macOS: an interrupted update rolls back through the same run's undo and leaves the old tool's checksum; after the
    update driven by the released control script and after the second update, no `.old`, `.old-token`,
    `maintenance-update/` or `maintenancetool/` is left, though the fixture planted a `.DS_Store` in both.
  - Windows: the failing operation runs in the update's own folder in the temporary folder and writes that folder's
    name, never its path, and the staged tool's hash there, which must be the 26.18 tool's; the check joins the name to
    the tool's own temporary folder and requires that folder gone after the rollback and no staged tool in the
    installation. Before the first update the check
    plants the empty `maintenancetool\` an earlier update left; after each successful update, once the tool has been
    replaced with the app never started, neither it nor the staged file is there. The app's test shows the app leaves
    both alone.
  - Linux: a failed update leaves `installer-runtime/` intact, its `dependencies.json` matching the libraries, the
    tool still answers an update check, and the purge removes the runtime and the lock file. The old exception that
    let a rolled-back Linux tool fail to start is gone.
- The app's recovery and cleanup are tested against a held lock in the app's Qt tests.

## Consequences

- Every installation carries `.MaintenanceTool.lock` until it is purged.
- The scripts depend on `/usr/bin/lockf` on macOS and util-linux `flock` on Linux, both part of the base system.
- The Linux tool's component is offered whenever the runtime's bytes change (ADR-0106, decision 4). That costs one
  swap and keeps the old runtime until the update succeeds.
- An old tool binary with a new runtime cannot follow a rollback, since the rollback puts the old runtime back.

## Alternatives considered

| Alternative | Verdict (why rejected / deferred) |
|---|---|
| Decide whether an update is running from the process named in the mark (ADR-0106) | Rejected: a force-quit tool, a time zone change or a second app each led it to take the backup at the wrong moment. |
| `QLockFile` in the app | Rejected: it is a process-number file, with the same stale-number problem the kernel lock removes. |
| A mark that older apps can read (process number only) with the run in a second file | Rejected: a second mark file kept forever for an exposure of milliseconds in one update. |
| Keep the Linux runtime in the app component and copy it aside before every update | Rejected: the runtime belongs to the tool, not the app; the copy covers only the one update that moves it (decision 8). |
| Remove the staging folder only when it is empty | Rejected: Finder writes files into it, and whatever is left once the staged item has moved out is debris. |
| Keep the staged Windows tool after an update | Rejected: the owner asked for no staging folder after a successful update, whichever tool drove it. |
