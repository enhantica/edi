// SPDX-License-Identifier: BSD-3-Clause

// Shortcuts to the installed program: the Start menu and the desktop on Windows, the applications menu and the
// desktop (when the home folder has one) on Linux. The installer undoes these operations when the app is removed.
function Component() {}

// What EasyDiffraction is, as the installer's pages say it (Installer.qs): the shortcut's and the menu entry's comment.
var DESCRIPTION = "Calculate diffraction patterns and fit a structural model to your data.";

Component.prototype.createOperations = function () {
    component.createOperations();
    holdProgress();
    var target = installer.value("TargetDir");
    // The install page's "Add a desktop shortcut" box (Installer.qs); the command line keeps it.
    var desktopShortcut = installer.value("EdiDesktopShortcut") !== "false";
    if (systemInfo.kernelType === "winnt") {
        var program = target + "/bin/EasyDiffraction.exe";
        var folder = "workingDirectory=" + target, icon = "iconPath=" + program;
        var about = "description=" + DESCRIPTION;
        component.addOperation("CreateShortcut", program, "@StartMenuDir@/EasyDiffraction.lnk", folder, icon, about);
        if (desktopShortcut)
            component.addOperation("CreateShortcut", program, "@DesktopDir@/EasyDiffraction.lnk", folder, icon, about);
    } else if (systemInfo.kernelType === "linux") {
        var entry = "Type=Application\nName=EasyDiffraction\nComment=" + DESCRIPTION + "\n"
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
        // ping waits without reading input; PowerShell and timeout stall or refuse when it is redirected.
        ? ["cmd.exe", "/c", "ping -n 5 127.0.0.1 > nul"] : ["/bin/sleep", "4"];
    component.addOperation("Execute", wait.concat(["UNDOEXECUTE"], wait));
}
