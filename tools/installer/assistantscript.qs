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
    var line = "The runtime for the ChatGPT assistant in EasyDiffraction";
    var size = Number(component.value("CompressedSize"));
    if (size > 0)
        line += ", a " + Math.max(1, Math.round(size / 1e6)) + " MB download";
    if (installer.isInstaller()) {
        box.checked = false;
        form.AssistantDescription.text = line + ".";
    } else {
        box.text = "Install the AI assistant";
        box.checked = component.installed;
        form.AssistantDescription.text = line + (component.installed ? ". Clear the box to remove it." : ".");
    }
    box.toggled.connect(function (checked) {
        if (checked)
            installer.selectComponent(component.name);
        else
            installer.deselectComponent(component.name);
    });
}
