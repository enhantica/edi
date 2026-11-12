// SPDX-License-Identifier: BSD-3-Clause

// Shortcuts to the installed program: the Start menu and the desktop on Windows, the applications menu and the
// desktop (when the home folder has one) on Linux. The installer undoes these operations when the app is removed.
function Component() {}

Component.prototype.createOperations = function () {
    component.createOperations();
    var target = installer.value("TargetDir");
    if (systemInfo.kernelType === "winnt") {
        var program = target + "/bin/EasyDiffraction.exe";
        var folder = "workingDirectory=" + target, icon = "iconPath=" + program, about = "description=EasyDiffraction";
        component.addOperation("CreateShortcut", program, "@StartMenuDir@/EasyDiffraction.lnk", folder, icon, about);
        component.addOperation("CreateShortcut", program, "@DesktopDir@/EasyDiffraction.lnk", folder, icon, about);
    } else if (systemInfo.kernelType === "linux") {
        var entry = "Type=Application\nName=EasyDiffraction\nComment=Diffraction analysis\n"
            + "Exec=\"" + target + "/bin/EasyDiffraction\"\nIcon=" + target + "/share/icons/EasyDiffraction.png\n"
            + "Terminal=false\nCategories=Science;Education;\n";
        component.addOperation("CreateDesktopEntry", "EasyDiffraction.desktop", entry);
        var desktop = installer.value("HomeDir") + "/Desktop";
        if (installer.fileExists(desktop))
            component.addOperation("CreateDesktopEntry", desktop + "/EasyDiffraction.desktop", entry);
    }
};
