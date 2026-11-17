// SPDX-License-Identifier: BSD-3-Clause

// macOS: install the separately signed maintenance tool shipped in this component. Without this the installer
// writes the tool from its own binary, which breaks a real signature (edi ADR-0091). The installer moves the
// bundle to the installation root and removes this folder.
function Component() {
    if (installer.isInstaller() && systemInfo.kernelType === "darwin")
        installer.setInstallerBaseBinary("@TargetDir@/maintenancetool/MaintenanceTool.app");
}
