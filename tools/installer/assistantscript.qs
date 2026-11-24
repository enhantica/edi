// SPDX-License-Identifier: BSD-3-Clause

// The AI assistant is the installer's one choice, so it is a checkbox instead of the Framework's component tree: on
// the installation folder page of the installer, and on a page of its own when the maintenance tool adds or removes
// components. The tree page is hidden (Installer.qs) because macOS accessibility clients crashed the Framework's
// Qt on it (edi #150).
function Component() {
    // The command line (install and remove by name, the protocol check) has no pages.
    if (installer.isCommandLineInstance())
        return;
    // The installing page's bar with its percentage beside it (Installer.qs feeds it), in every mode.
    installer.addWizardPageItem(component, "ProgressForm", QInstaller.PerformInstallation);
    // The last page's box to open the program, in a row of its own (DoneForm.ui, Installer.qs).
    installer.addWizardPageItem(component, "DoneForm", QInstaller.InstallationFinished);
    if (installer.isInstaller())
        installer.addWizardPageItem(component, "AssistantForm", QInstaller.TargetDirectory);
    else if (installer.isPackageManager() || installer.isUpdater())
        installer.addWizardPage(component, "AssistantForm", QInstaller.ReadyForInstallation);
    else
        return;
    // The Framework gives its added page a one-space subtitle, which draws a header band: cleared before it shows.
    var added = installer.isInstaller() ? null : gui.pageByObjectName("DynamicAssistantForm");
    if (added) {
        added.title = "";
        added.subTitle = "";
    }
    var form = component.userInterface("AssistantForm");
    if (!form)
        return;
    var box = form.AssistantCheckBox;
    if (installer.isInstaller()) {
        // Ticked from the start (owner's choice); the command line still installs it only when named.
        box.checked = true;
        // The folder field of our own (Installer.qs keeps the Framework's in step with it).
        ["FolderLineEdit", "FolderBrowseButton"].forEach(function (name) {
            if (form[name])
                form[name].visible = true;
        });
        installer.selectComponent(component.name);
    } else {
        // The choice page, the same when adding or removing and when updating: EasyDiffraction is always kept
        // (ticked, fixed), the AI assistant is ticked when installed. Updating, its box says whether it is updated;
        // an assistant that is not installed cannot be, and a note says where to add it.
        if (form.AppCheckBox)
            form.AppCheckBox.visible = true;
        box.text = "AI assistant";
        box.checked = component.installed;
        // The licence, shortcut and space belong to installing, not to this choice.
        ["LicenseCheckBox", "LicenseLink", "ShortcutCheckBox", "NoticeLabel", "SpaceLabel"].forEach(function (name) {
            if (form[name])
                form[name].visible = false;
        });
        if (installer.isUpdater() && !component.installed) {
            box.enabled = false;
            if (form.NoticeLabel) {
                form.NoticeLabel.text = "The AI assistant is not installed. Choose Change components to add it.";
                form.NoticeLabel.visible = true;
            }
        }
    }
    box.toggled.connect(function (checked) {
        if (checked)
            installer.selectComponent(component.name);
        else
            installer.deselectComponent(component.name);
    });
}

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

Component.prototype.createOperations = function () {
    component.createOperations();
    holdProgress();
};
