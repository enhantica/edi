// SPDX-License-Identifier: BSD-3-Clause

// The AI assistant is the installer's one choice, so it is a checkbox instead of the Framework's component tree: on
// the installation folder page of the installer, and on a page of its own when the maintenance tool adds or removes
// components. The tree page is hidden (Installer.qs) because macOS accessibility clients crashed the Framework's
// Qt on it (edi #150).
function Component() {
    // The command line (install and remove by name, the protocol check) has no pages.
    if (installer.isCommandLineInstance())
        return;
    if (installer.isInstaller())
        installer.addWizardPageItem(component, "AssistantForm", QInstaller.TargetDirectory);
    else if (installer.isPackageManager())
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
        box.text = "Install the AI assistant";
        box.checked = component.installed;
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
