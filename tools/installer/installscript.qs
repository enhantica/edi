// SPDX-License-Identifier: BSD-3-Clause

// Shortcuts to the installed program: the Start menu and the desktop on Windows, the applications menu and the
// desktop (when the home folder has one) on Linux. The installer undoes these operations when the app is removed.
// On Linux an update also keeps the maintenance tool's runtime (keepsRuntime below); on Windows it removes the tool's
// old staging folder (removeOldStaging).
function Component() {
    installer.installationFinished.connect(this, Component.prototype.settleRuntime);
}

// What EasyDiffraction is, as the installer's pages say it (Installer.qs): the shortcut's and the menu entry's comment.
var DESCRIPTION = "Calculate diffraction patterns and fit a structural model to your data.";

// The maintenance tool's pages, which an online build ships with this component (package.py names the file here). The
// running tool keeps its pages in MaintenanceTool.dat and copies them over at the end of every update, so without this
// a newer tool shows the pages of the release first installed. Named as the replacement, the file goes into that data
// file instead and the Framework deletes it (edi ADR-0106).
var MAINTENANCE_RESOURCE = "";

// The first Linux update off a release whose app component carried the tool's runtime (installer-runtime/, edi
// ADR-0109). The Framework undoes that release's operations of this component, which deletes the runtime, before
// any operation of this update runs, and a rollback never brings it back. So the update keeps a copy first and
// settles it at the end: back in place when no usable runtime is there, dropped otherwise. maintenance_swap.sh and
// maintenance_restore.sh, written in by package.py, do it with copy as their last argument, under the lock and with
// a mark naming this run.
var SWAP_SCRIPT = "@EDI_SWAP_SCRIPT@";
var RESTORE_SCRIPT = "@EDI_RESTORE_SCRIPT@";
var RUNTIME_TOKEN = "runtime-" + String(Date.now()) + "-" + String(Math.floor(Math.random() * 1e9));

function keepsRuntime() {
    return systemInfo.kernelType === "linux" && installer.isUpdater();
}

function runtimeCommand(script) {
    return ["-c", script, script, installer.value("TargetDir"), RUNTIME_TOKEN, "installer-runtime",
            "dependencies.json", "copy"];
}

// IFW 4.11 calls this for each component it is about to install, before it undoes the installed release's
// operations. Without the copy that undo could delete the only runtime, so the update stops here instead, before
// anything has changed.
Component.prototype.beginInstallation = function () {
    if (!keepsRuntime() || installer.value("TargetDir") === "")
        return;
    var result = installer.execute("/bin/sh", runtimeCommand(SWAP_SCRIPT));
    if (result.length !== 2 || result[1] !== 0)
        throw new Error("The update could not keep a copy of the Maintenance Tool's files.");
};

// After a success or a rollback.
Component.prototype.settleRuntime = function () {
    if (keepsRuntime() && installer.value("TargetDir") !== "")
        installer.execute("/bin/sh", runtimeCommand(RESTORE_SCRIPT));
    removeOldStaging();
};

// Windows: after a successful update, the folder releases before staged the Maintenance Tool into, which nothing uses
// any more (edi ADR-0109). This component is in every update, the tool's component only when the tool changed.
// cmd.exe runs in the installation folder and names only that folder, so it never reads the installation's path.
function removeOldStaging() {
    var target = installer.value("TargetDir");
    if (systemInfo.kernelType !== "winnt" || !installer.isUpdater() || installer.status !== QInstaller.Success
            || target === "" || !installer.fileExists(target + "/maintenancetool"))
        return;
    installer.performOperation("Execute", ["cmd.exe", "/c", "rmdir", "/s", "/q", "maintenancetool",
                                           "workingdirectory=" + target]);
}

Component.prototype.createOperations = function () {
    // First, so that any later failure of this component undoes it: the copy goes back when the runtime is gone.
    if (keepsRuntime()) {
        var settle = ["/bin/sh"].concat(runtimeCommand(RESTORE_SCRIPT));
        component.addOperation("Execute", settle.concat(["UNDOEXECUTE"], settle));
    }
    component.createOperations();
    holdProgress();
    var target = installer.value("TargetDir");
    if (MAINTENANCE_RESOURCE !== "")
        installer.setValue("DefaultResourceReplacement", target + "/" + MAINTENANCE_RESOURCE);
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
