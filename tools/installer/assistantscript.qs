// SPDX-License-Identifier: BSD-3-Clause

// The assistants are the installer's one choice, so they are checkboxes instead of the Framework's component tree: on
// the installation folder page of the installer, and on a page of its own when the maintenance tool adds or removes
// components. The tree page is hidden (Installer.qs) because macOS accessibility clients crashed the Framework's
// Qt on it (edi #150). This is ChatGPT's component; its form has a row for each assistant component (edi ADR-0108).

// Each assistant component, its row and its label; ChatGPT starts ticked when installing, the others do not. A
// component the installer does not carry (Claude or GitHub Copilot, until its distribution is public) has no row.
var CHOICES = [{row: "Assistant", name: "org.easydiffraction.app.assistant", label: "ChatGPT", ticked: true},
               {row: "Claude", name: "org.easydiffraction.app.claude", label: "Claude", ticked: false},
               {row: "Copilot", name: "org.easydiffraction.app.copilot", label: "GitHub Copilot", ticked: false}];

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
    // Changing components asks about the assistants on a page of its own; updating takes everything installed and
    // goes straight to its summary (owner, 2026-11-26).
    else if (installer.isPackageManager())
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
    // The form's parts are in row widgets, so they are looked for by name at any depth.
    function part(name) { return gui.findChild(form, name); }
    // EasyDiffraction is always installed (ticked, fixed), each row with its size (Installer.qs).
    part("AppBox").visible = true;
    if (installer.isInstaller()) {
        // The folder field of our own (Installer.qs keeps the Framework's in step with it).
        part("FolderBox").visible = true;
    } else {
        // The licence and shortcut belong to installing, not to this choice; the space line stays (Installer.qs).
        ["LicenseBox", "ShortcutBox", "NoticeBox"].forEach(function (name) {
            part(name).visible = false;
        });
    }
    CHOICES.forEach(function (choice) {
        var box = part(choice.row + "CheckBox");
        var carried = choice.name === component.name ? component : installer.componentByName(choice.name);
        part(choice.row + "Box").visible = !!carried;
        if (!carried || !box)
            return;
        box.text = choice.label;
        if (installer.isInstaller()) {
            // The owner's choice of what starts ticked; the command line still installs only what it names.
            box.checked = choice.ticked;
            if (choice.ticked)
                installer.selectComponent(choice.name);
        } else {
            // Adding or removing components: each is ticked when installed.
            box.checked = carried.installed;
        }
        box.toggled.connect(function (checked) {
            if (checked)
                installer.selectComponent(choice.name);
            else
                installer.deselectComponent(choice.name);
        });
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
