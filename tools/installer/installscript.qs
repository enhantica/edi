// SPDX-License-Identifier: BSD-3-Clause

// Shortcuts to the installed program: the Start menu and the desktop on Windows, the applications menu and the
// desktop (when the home folder has one) on Linux. The installer undoes these operations when the app is removed.
function Component() {}

Component.prototype.createOperations = function () {
    component.createOperations();
    holdProgress();
    var target = installer.value("TargetDir");
    // The install page's "Add a desktop shortcut" box (Installer.qs); the command line keeps it.
    var desktopShortcut = installer.value("EdiDesktopShortcut") !== "false";
    if (systemInfo.kernelType === "winnt") {
        var program = target + "/bin/EasyDiffraction.exe";
        var folder = "workingDirectory=" + target, icon = "iconPath=" + program, about = "description=EasyDiffraction";
        component.addOperation("CreateShortcut", program, "@StartMenuDir@/EasyDiffraction.lnk", folder, icon, about);
        if (desktopShortcut)
            component.addOperation("CreateShortcut", program, "@DesktopDir@/EasyDiffraction.lnk", folder, icon, about);
    } else if (systemInfo.kernelType === "linux") {
        var entry = "Type=Application\nName=EasyDiffraction\nComment=Diffraction analysis\n"
            + "Exec=\"" + target + "/bin/EasyDiffraction\"\nIcon=" + target + "/share/icons/EasyDiffraction.png\n"
            + "Terminal=false\nCategories=Science;Education;\n";
        component.addOperation("CreateDesktopEntry", "EasyDiffraction.desktop", entry);
        var desktop = installer.value("HomeDir") + "/Desktop";
        if (desktopShortcut && installer.fileExists(desktop))
            component.addOperation("CreateDesktopEntry", desktop + "/EasyDiffraction.desktop", entry);
    }
};

// Captures (EDI_INSTALLER_CAPTURE) hold the progress page a few seconds when installing and when removing, so its
// picture and the accessibility check catch it: the marker installer is otherwise done at once and the Framework
// leaves the page by itself.
function holdProgress() {
    if (installer.environmentVariable("EDI_INSTALLER_CAPTURE") === "")
        return;
    var wait = systemInfo.kernelType === "winnt"
        ? ["powershell.exe", "-NoProfile", "-Command", "Start-Sleep -Seconds 4"] : ["/bin/sleep", "4"];
    component.addOperation("Execute", wait.concat(["UNDOEXECUTE"], wait));
}
