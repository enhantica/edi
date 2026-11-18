// SPDX-License-Identifier: BSD-3-Clause

// macOS and Windows: install the separately signed maintenance tool shipped in this component. Without this the
// installer writes the tool from its own binary, which breaks a real signature (edi ADR-0091). On macOS the
// installer moves the bundle to the installation root and removes this folder.
function Component() {
    if (!installer.isInstaller())
        return;
    if (systemInfo.kernelType === "darwin")
        installer.setInstallerBaseBinary("@TargetDir@/maintenancetool/MaintenanceTool.app");
    else if (systemInfo.kernelType === "winnt")
        installer.setInstallerBaseBinary("@TargetDir@/maintenancetool/MaintenanceTool.exe");
}

// The component carries the app version, so every update lists it. An update keeps the installed tool and
// unpacks nothing, so no copy is left behind; only a first installation unpacks the bundle.
Component.prototype.createOperations = function () {
    if (installer.isInstaller())
        component.createOperations();
};
