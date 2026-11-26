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
// tool. The framework replaces the tool at the end, on Windows once it has quit (edi ADR-0106).
Component.prototype.createOperations = function () {
    if (!installer.isInstaller() && !installer.isUpdater())
        return;
    component.createOperations();
    if (installer.isUpdater() && stagedTool() !== "")
        installer.setInstallerBaseBinary(stagedTool());
};
