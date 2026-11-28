// SPDX-License-Identifier: BSD-3-Clause

// macOS and Windows: install the separately signed maintenance tool shipped in this component. Without this the
// installer writes the tool from its own binary, which breaks a real signature (edi ADR-0091). On macOS the
// installer moves the bundle to the installation root and removes this folder. On Linux the component carries only
// the tool's Qt runtime; the installer writes the tool itself.
function stagedTool() {
    if (systemInfo.kernelType === "darwin")
        return "@TargetDir@/maintenancetool/MaintenanceTool.app";
    if (systemInfo.kernelType === "winnt")
        return "@TargetDir@/maintenancetool/MaintenanceTool.exe";
    return "";
}

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
    if (systemInfo.kernelType === "winnt") {
        // A failed update's rollback leaves the staged tool it unpacked (measured on CI), so this operation's undo
        // removes it. A successful update has moved it into place already. cmd.exe needs backslashes here.
        var staged = installer.value("TargetDir").replace(/\//g, "\\") + "\\maintenancetool\\MaintenanceTool.exe";
        component.addOperation("Execute", "cmd.exe", "/c", "rem", "UNDOEXECUTE", "cmd.exe", "/c", "if", "exist", staged,
                               "del", "/f", "/q", staged);
    }
    if (installer.isUpdater() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
};

// After a successful update nothing of the swap is left: no backup and no staging folder, whichever tool drove the
// update (edi ADR-0109). After a rollback the undo has put the kept item back and nothing is removed. Windows keeps
// its staged tool here: in an update the framework writes the installed tool from it only after this signal, as it
// quits (IFW 4.11), so the app removes it once the installed tool has the same bytes.
Component.prototype.removeLeftovers = function () {
    if (!installer.isUpdater() || installer.status !== QInstaller.Success)
        return;
    var swap = swapped();
    var target = installer.value("TargetDir");
    if (swap === null || target === "")
        return;
    installer.execute("/bin/sh", ["-c", CLEANUP_SCRIPT, CLEANUP_SCRIPT, target, swap.item, swap.probe]);
};
