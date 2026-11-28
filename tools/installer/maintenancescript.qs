// SPDX-License-Identifier: BSD-3-Clause

// macOS and Windows: install the separately signed maintenance tool shipped in this component. Without this the
// installer writes the tool from its own binary, which breaks a real signature (edi ADR-0091). On macOS the
// installer moves the bundle to the installation root and removes this folder. On Windows the component unpacks the
// tool into a folder of this run's own in the user's temporary folder, never the installation folder
// (createOperationsForArchive below). On Linux
// the component carries only the tool's Qt runtime; the installer writes the tool itself. The staging folder's name
// differs from the tool's even on a case-insensitive disk.
function stagedTool() {
    if (systemInfo.kernelType === "darwin")
        return "@TargetDir@/maintenance-update/MaintenanceTool.app";
    if (systemInfo.kernelType === "winnt" && windowsStaging() !== "")
        return windowsStaging() + "\\" + handoffFolder() + "\\MaintenanceTool.update.exe";
    return "";
}

// Windows: this run's folder in the temporary folder, so a tool an earlier run left there can never stand in for this
// update's: a missing one makes the Framework keep the installed tool (IFW 4.11).
var handoffName = "";

function handoffFolder() {
    if (handoffName === "")
        handoffName = "EasyDiffraction-MaintenanceTool-" + String(Date.now()) + "-"
            + String(Math.floor(Math.random() * 1e9));
    return handoffName;
}

// Windows: the user's temporary folder, where the staged tool is unpacked (edi ADR-0109).
function windowsStaging() {
    var temp = installer.environmentVariable("TEMP");
    if (temp === "" && installer.environmentVariable("LOCALAPPDATA") !== "")
        temp = installer.environmentVariable("LOCALAPPDATA") + "\\Temp";
    return temp;
}

// Windows: the Framework writes the installed tool from the staged one only as it quits, after every script, and then
// deletes it but goes on if it cannot (IFW 4.11). Unpacked into this run's folder in the temporary folder, the staged
// tool is never in the installation folder, so no operation has to move or remove it there.
Component.prototype.createOperationsForArchive = function (archive) {
    if (systemInfo.kernelType !== "winnt")
        return undefined;
    if (windowsStaging() === "")
        throw new Error("The update found no temporary folder for the Maintenance Tool.");
    component.addOperation("Extract", archive, windowsStaging() + "\\" + handoffFolder());
    return true;
};

// The folder the swap puts in place, and the file inside it that shows it is usable (edi ADR-0109).
function swapped() {
    if (systemInfo.kernelType === "darwin")
        return { item: "MaintenanceTool.app", probe: "Contents/MacOS/MaintenanceTool" };
    if (systemInfo.kernelType === "linux")
        return { item: "installer-runtime", probe: "dependencies.json" };
    return null;
}

// maintenance_swap.sh, maintenance_restore.sh and maintenance_cleanup.sh, written in by package.py. Each runs as
// sh -c with its own text as its name, so it can run itself again under the lock.
var SWAP_SCRIPT = "@EDI_SWAP_SCRIPT@";
var RESTORE_SCRIPT = "@EDI_RESTORE_SCRIPT@";
var CLEANUP_SCRIPT = "@EDI_CLEANUP_SCRIPT@";

function Component() {
    if (installer.isInstaller() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
    // Component scripts come from the repository being installed, so this runs even in an update driven by an older
    // maintenance tool.
    installer.installationFinished.connect(this, Component.prototype.removeLeftovers);
}

// Whether this update holds rights it gained for a protected installation folder, as IFW 4.11 does before it calls
// beginInstallation. It drops them before installationFinished but keeps its helper running, so taking them again
// there asks nothing (RemoteClient::setActive); the cleanup needs them to remove what the swap kept.
var updateRights = false;

function withUpdateRights(run) {
    var again = updateRights && !installer.hasAdminRights();
    if (again)
        installer.gainAdminRights();
    try {
        run();
    } finally {
        if (again)
            installer.dropAdminRights();
    }
}

// IFW 4.11 calls this before it unpacks any component. The claim tells the app that this run's tool owns the staging
// folder, so a start of the app during the unpacking leaves it alone (edi ADR-0109). Without the claim the update
// stops here, before anything has changed.
Component.prototype.beginInstallation = function () {
    updateRights = installer.hasAdminRights();
    var swap = swapped();
    if (swap === null || !installer.isUpdater() || installer.value("TargetDir") === "")
        return;
    var result = installer.execute("/bin/sh", ["-c", SWAP_SCRIPT, SWAP_SCRIPT, installer.value("TargetDir"), "claim",
                                               swap.item, swap.probe, "claim"]);
    if (result.length !== 2 || result[1] !== 0)
        throw new Error("The update could not prepare the Maintenance Tool's files.");
};

// The component carries the app version, so every update lists it. An update unpacks the new signed tool as well
// and asks for it here, where only a component being updated runs, so an update without it keeps the installed
// tool. On Windows the framework replaces the tool at the end, once it has quit. On macOS the framework moves the
// staged bundle into place on a first installation only (measured on CI), so the update swaps the bundles itself
// once the new one is unpacked. On Linux the runtime the tool loads its Qt libraries from is swapped the same way,
// on a first installation too, so that no undo ever deletes the runtime in place. The swap can be run again after
// any failure, keeps the installed item until the update has succeeded, and its undo puts it back (edi ADR-0109).
// The running tool keeps its open files.
Component.prototype.createOperations = function () {
    if (!installer.isInstaller() && !installer.isUpdater())
        return;
    component.createOperations();
    var swap = swapped();
    if (swap !== null && (installer.isUpdater() || systemInfo.kernelType === "linux")) {
        // One token for this operation. The scripts mark the backup with it and with the running tool's process, so
        // the undo puts back only a backup this operation kept in this run: a later update that undoes the saved,
        // committed operation leaves the tools alone.
        var token = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e9));
        component.addOperation("Execute", "/bin/sh", "-c", SWAP_SCRIPT, SWAP_SCRIPT, "@TargetDir@", token,
                               swap.item, swap.probe,
                               "UNDOEXECUTE", "/bin/sh", "-c", RESTORE_SCRIPT, RESTORE_SCRIPT, "@TargetDir@", token,
                               swap.item, swap.probe);
        return;
    }
    if (systemInfo.kernelType === "winnt" && windowsStaging() !== "") {
        // The unpack leaves the tool the Framework is to write from out of what its undo removes (IFW 4.11
        // ExtractArchiveOperation), so this operation's undo removes this run's folder on a rollback. cmd.exe runs in
        // the temporary folder and names only the folder, so it never reads a path; a later update's or a removal's
        // undo finds the folder empty or gone, and the exit code stays 0 so it never asks.
        var folder = "workingdirectory=" + windowsStaging();
        component.addOperation("Execute", "cmd.exe", "/c", "rem", folder, "UNDOEXECUTE", "cmd.exe", "/c", "rmdir", "/s",
                               "/q", handoffFolder(), "2>nul", "&", "exit", "0", folder);
    }
    if (installer.isUpdater() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
};

// After a successful update nothing of the swap is left: no backup and no staging folder, whichever tool drove the
// update (edi ADR-0109). After a rollback the undo has put the kept item back, and only this run's claim on the
// staging folder goes. Windows has nothing to remove here: the staged tool was unpacked into the temporary folder.
Component.prototype.removeLeftovers = function () {
    var swap = swapped();
    var target = installer.value("TargetDir");
    if (!installer.isUpdater() || swap === null || target === "")
        return;
    var command = ["-c", CLEANUP_SCRIPT, CLEANUP_SCRIPT, target, swap.item, swap.probe];
    if (installer.status !== QInstaller.Success)
        command.push("release");
    withUpdateRights(function () { installer.execute("/bin/sh", command); });
};
