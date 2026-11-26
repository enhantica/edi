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

function Component() {
    if (installer.isInstaller() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
}

// The component carries the app version, so every update lists it. An update unpacks the new signed tool as well
// and asks for it here, where only a component being updated runs, so an update without it keeps the installed
// tool. On Windows the framework replaces the tool at the end, once it has quit; on macOS the update swaps the bundle
// itself (below; edi ADR-0106).
Component.prototype.createOperations = function () {
    if (!installer.isInstaller() && !installer.isUpdater())
        return;
    component.createOperations();
    if (!installer.isUpdater() || stagedTool() === "")
        return;
    // On macOS the framework moves the staged bundle into place on a first installation only: an update leaves it in
    // the staging folder and keeps the old tool (measured on CI). So the update swaps the bundles itself, once the new
    // one is unpacked; the running tool keeps its open files until it quits.
    if (systemInfo.kernelType === "darwin") {
        component.addOperation("Execute", "/bin/sh", "-c",
            'staged="$1/maintenancetool/MaintenanceTool.app"; [ -d "$staged" ] || exit 1;'
            + ' rm -rf "$1/MaintenanceTool.app.old" && mv "$1/MaintenanceTool.app" "$1/MaintenanceTool.app.old"'
            + ' && mv "$staged" "$1/MaintenanceTool.app" && rm -rf "$1/MaintenanceTool.app.old" "$1/maintenancetool"',
            "sh", "@TargetDir@");
        return;
    }
    installer.setInstallerBaseBinary(stagedTool());
};
