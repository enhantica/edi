// SPDX-License-Identifier: BSD-3-Clause

// macOS and Windows: install the separately signed maintenance tool shipped in this component. Without this the
// installer writes the tool from its own binary, which breaks a real signature (edi ADR-0091). On macOS the
// installer moves the bundle to the installation root and removes this folder.
function stagedTool() {
    if (systemInfo.kernelType === "darwin")
        return "@TargetDir@/maintenancetool/MaintenanceTool.app";
    if (systemInfo.kernelType === "winnt")
        return "@TargetDir@/maintenancetool/MaintenanceTool.exe";
    return "";
}

// The macOS swap and its undo (maintenance_swap.sh and maintenance_restore.sh), written in by package.py.
var SWAP_SCRIPT = "@EDI_SWAP_SCRIPT@";
var RESTORE_SCRIPT = "@EDI_RESTORE_SCRIPT@";

function Component() {
    if (installer.isInstaller() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
}

// The component carries the app version, so every update lists it. An update unpacks the new signed tool as well
// and asks for it here, where only a component being updated runs, so an update without it keeps the installed
// tool. On Windows the framework replaces the tool at the end, once it has quit. On macOS the framework moves the
// staged bundle into place on a first installation only (measured on CI), so the update swaps the bundles itself
// once the new one is unpacked: the swap can be run again after any failure, keeps the installed bundle until the
// update has succeeded, and its undo puts it back (edi ADR-0106). The running tool keeps its open files.
Component.prototype.createOperations = function () {
    if (!installer.isInstaller() && !installer.isUpdater())
        return;
    component.createOperations();
    if (!installer.isUpdater() || stagedTool() === "")
        return;
    if (systemInfo.kernelType === "darwin") {
        // One token for this operation: its undo puts back only the backup this operation kept, never one an earlier
        // update left behind.
        var token = String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e9));
        component.addOperation("Execute", "/bin/sh", "-c", SWAP_SCRIPT, "sh", "@TargetDir@", token,
                               "UNDOEXECUTE", "/bin/sh", "-c", RESTORE_SCRIPT, "sh", "@TargetDir@", token);
        return;
    }
    installer.setInstallerBaseBinary(stagedTool());
};
