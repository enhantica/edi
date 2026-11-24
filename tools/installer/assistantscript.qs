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
    var form = component.userInterface("AssistantForm");
    if (!form)
        return;
    var box = form.AssistantCheckBox;
    if (installer.isInstaller()) {
        // Ticked from the start (owner's choice); the command line still installs it only when named.
        box.checked = true;
        installer.selectComponent(component.name);
    } else {
        // The choice page, the same when adding or removing and when updating: EasyDiffraction is always kept
        // (ticked, fixed), the AI assistant is ticked when installed. Updating, its box says whether it is updated;
        // an assistant that is not installed is not offered there.
        if (form.AppCheckBox)
            form.AppCheckBox.visible = true;
        box.text = "AI assistant";
        box.checked = component.installed;
        if (installer.isUpdater() && !component.installed)
            box.visible = false;
        // The licence, shortcut and space belong to installing, not to this choice.
        ["LicenseCheckBox", "LicenseLink", "ShortcutCheckBox", "NoticeLabel", "SpaceLabel"].forEach(function (name) {
            if (form[name])
                form[name].visible = false;
        });
    }
    box.toggled.connect(function (checked) {
        if (checked)
            installer.selectComponent(component.name);
        else
            installer.deselectComponent(component.name);
    });
}
