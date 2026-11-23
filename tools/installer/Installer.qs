// SPDX-License-Identifier: BSD-3-Clause

// macOS refuses to start a downloaded program that still carries the quarantine flag from the
// browser, the bundled assistant runtime included, so it is cleared on everything installed.
function clearQuarantine() {
    if (systemInfo.kernelType !== "darwin")
        return;
    var target = installer.value("TargetDir");
    if (target !== "")
        installer.execute("/usr/bin/xattr", ["-r", "-d", "com.apple.quarantine", target]);
}

// Windows: a new installation goes to %LOCALAPPDATA%\Programs\EasyDiffraction, or to
// C:\Program Files\EasyDiffraction when the installer runs as administrator (edi ADR-0071). Set from the
// environment, as the Framework's own directory variables differ between its versions. An existing
// installation is updated by its maintenance tool where it is, so this never moves one.
function chooseWindowsTarget() {
    if (systemInfo.kernelType !== "winnt" || !installer.isInstaller())
        return;
    // Only the configured default is replaced, never a directory given with --root.
    function normal(path) { return path.replace(/\//g, "\\").toLowerCase(); }
    var configured = installer.value("ApplicationsDirUser") + "/EasyDiffraction";
    if (normal(installer.value("TargetDir")) !== normal(configured))
        return;
    var base = installer.hasAdminRights() ? installer.environmentVariable("ProgramFiles")
                                          : installer.environmentVariable("LOCALAPPDATA") + "\\Programs";
    if (base !== "" && base !== "\\Programs")
        installer.setValue("TargetDir", base + "\\EasyDiffraction");
}

// Whether the pages show dark, for the wordmark: Installer.qss takes its colours from the system's palette, which Qt
// makes dark only on macOS and on Windows 11 (build 22000 on) in dark mode; Windows 10 and Linux stay light.
// EDI_INSTALLER_THEME (light or dark) overrides it.
var theme = "";

function darkTheme() {
    if (theme !== "")
        return theme === "dark";
    var forced = installer.environmentVariable("EDI_INSTALLER_THEME");
    if (forced === "dark" || forced === "light") {
        theme = forced;
    } else if (systemInfo.kernelType === "darwin") {
        var appearance = installer.execute("/usr/bin/defaults", ["read", "-g", "AppleInterfaceStyle"]);
        theme = appearance[1] === 0 && appearance[0].trim() === "Dark" ? "dark" : "light";
    } else if (systemInfo.kernelType === "winnt" && Number(String(systemInfo.kernelVersion).split(".")[2]) >= 22000) {
        var key = "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize";
        var answer = installer.execute("reg", ["query", key, "/v", "AppsUseLightTheme"]);
        theme = answer[1] === 0 && /AppsUseLightTheme\s+REG_DWORD\s+0x0\b/.test(answer[0]) ? "dark" : "light";
    } else {
        theme = "light";
    }
    return theme === "dark";
}

// The page captures (EDI_INSTALLER_CAPTURE, a folder): each page is saved as <mode>-<page>-<theme>.png and the page
// moves on by itself, in the installer and in the maintenance tool alike.
var captureFolder = installer.environmentVariable("EDI_INSTALLER_CAPTURE");
// The maintenance tool's mode in capture mode (EDI_INSTALLER_MAINTENANCE_MODE): add (add or remove components),
// update, or remove (everything, the default).
var maintenanceMode = installer.environmentVariable("EDI_INSTALLER_MAINTENANCE_MODE") || "remove";

// Taken a moment later by a detached process, once the page has painted.
function capture(name) {
    if (captureFolder === "")
        return;
    var mode = installer.isInstaller() ? "installer" : "maintenance-" + maintenanceMode;
    var file = captureFolder + "/" + mode + "-" + name + "-" + (darkTheme() ? "dark" : "light") + ".png";
    if (systemInfo.kernelType === "winnt") {
        // A process started here cannot take a screenshot; capture_pages.py takes them on Windows.
    } else if (systemInfo.kernelType === "darwin") {
        installer.executeDetached("/bin/sh", ["-c", "sleep 1; /usr/sbin/screencapture -x '" + file + "'"]);
    } else {
        installer.executeDetached("/bin/sh", ["-c", "sleep 1; import -window root '" + file + "'"]);
    }
}

function advance(name, page) {
    if (captureFolder === "")
        return;
    if (name === "LicenseAgreement") {
        var accept = gui.findChild(page, "AcceptLicenseCheckBox") || gui.findChild(page, "AcceptLicenseRadioButton");
        if (accept)
            accept.checked = true;
    }
    // The maintenance tool takes the mode asked for; removing everything needs no repository.
    if (name === "Introduction" && !installer.isInstaller()) {
        var choice = {add: "PackageManagerRadioButton", update: "UpdaterRadioButton"}[maintenanceMode]
            || "UninstallerRadioButton";
        var radio = gui.findChild(page, choice);
        if (radio)
            radio.checked = true;
    }
    if (name === "PerformInstallation") {
        // The Framework moves on when it is done, unless its details are open; then this does.
        var next = function () { gui.clickButton(buttons.NextButton, 1500); };
        installer.installationFinished.connect(next);
        installer.uninstallationFinished.connect(next);
        return;
    }
    gui.clickButton(name === "Finished" ? buttons.FinishButton : buttons.NextButton, 2500);
}

function Controller() {
    // No component tree: macOS accessibility clients crash the Framework's Qt on it (edi #150); the one choice it
    // offered, the AI assistant, is a checkbox (assistantscript.qs).
    installer.setDefaultPageVisible(QInstaller.ComponentSelection, false);
    // No Settings button: the system proxy is used by default, and nobody needs to edit repositories here.
    gui.showSettingsButton(false);
    chooseWindowsTarget();
    installer.installationFinished.connect(clearQuarantine);
    installer.updateFinished.connect(clearQuarantine);
}

// edi's light and dark themes for the pages (Installer.qss, filled in by package.py). Scripts can reach the pages but
// not the window around them, which follows the system palette (InstallerChrome.qss).
var lightStylesheet = "@LIGHT_STYLESHEET@";
var darkStylesheet = "@DARK_STYLESHEET@";

function themePage(page) {
    if (page)
        page.styleSheet = darkTheme() ? darkStylesheet : lightStylesheet;
}

// The assistant's own page in the maintenance tool (assistantscript.qs).
Controller.prototype.DynamicAssistantFormCallback = function () {
    var page = gui.pageWidgetByObjectName("DynamicAssistantForm");
    themePage(page);
    // Adding components in capture mode adds the assistant, so the mode has something to do.
    var box = captureFolder !== "" ? gui.findChild(page, "AssistantCheckBox") : null;
    if (box)
        box.checked = true;
    capture("AssistantForm");
    advance("AssistantForm", page);
};

var wordmark = "";

function headerWordmark() {
    if (wordmark === "") {
        var image = darkTheme() ? "@DARK_WORDMARK@" : "@WORDMARK@";
        wordmark = '<img src="data:image/png;base64,' + image + '" width="140" height="44">';
    }
    return wordmark;
}

[
    "Introduction", "TargetDirectory", "ComponentSelection", "LicenseAgreement",
    "StartMenuDirectory", "ReadyForInstallation", "PerformInstallation", "Finished"
].forEach(function (name) {
    Controller.prototype[name + "PageCallback"] = function () {
        var page = gui.pageWidgetByObjectName(name + "Page");
        if (!page)
            return;
        themePage(page);

        // The maintenance tool asks plainly, at the top, and updates unless told otherwise: never a destructive
        // default.
        if (name === "Introduction" && !installer.isInstaller()) {
            var ask = gui.findChild(page, "MessageLabel");
            if (ask) {
                ask.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop
                ask.text = "What would you like to do?";
            }
            var update = gui.findChild(page, "UpdaterRadioButton");
            if (update && captureFolder === "")
                update.checked = true;
        }

        // The summary without the Framework's component trees: a tree view is what macOS accessibility clients
        // crashed (edi #150), so none may show. One plain sentence says what happens.
        if (name === "ReadyForInstallation") {
            ["InstallComponentsWidget", "UninstallComponentsWidget"].forEach(function (container) {
                var widget = gui.findChild(page, container);
                if (widget)
                    widget.visible = false;
            });
            var summary = gui.findChild(page, "RemoveAllMsgLabel");
            if (summary && !installer.isUninstaller()) {
                summary.text = installer.isInstaller() ? "EasyDiffraction is ready to install."
                    : installer.isUpdater() ? "EasyDiffraction is ready to update."
                    : "Your changes to EasyDiffraction are ready to apply.";
                summary.visible = true;
            }
        }

        if (name === "Introduction" && installer.isInstaller()) {
            var welcome = gui.findChild(page, "MessageLabel");
            welcome.openExternalLinks = true;
            // Top-aligned, level with the step list; a label centres its text in its minimum height.
            welcome.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop
            welcome.text = "<p>Welcome to the EasyDiffraction Installer.</p>"
                + "<p>EasyDiffraction calculates diffraction patterns from a structural model "
                + "and refines its parameters against experimental data.</p>"
                + '<p>Learn more at <a style="color: ' + (darkTheme() ? "#4ec1ef" : "#00a3e3")
                + '; text-decoration: none" href="https://easydiffraction.org">easydiffraction.org</a>.</p>';
        }

        // The licence is the GPL, which asks for no acceptance: the option starts accepted.
        if (name === "LicenseAgreement") {
            var accept = gui.findChild(page, "AcceptLicenseCheckBox") || gui.findChild(page, "AcceptLicenseRadioButton");
            if (accept)
                accept.checked = true;
        }

        if (name === "TargetDirectory") {
            var question = gui.findChild(page, "MessageLabel");
            if (question)
                question.text = "Choose where to install EasyDiffraction.";
        }

        if (name === "TargetDirectory" && systemInfo.kernelType === "darwin") {
            var directory = gui.findChild(page, "TargetDirectoryLineEdit");
            directory.styleSheet = "margin-top: 4px;";
        }

        var title = page.title;
        var subtitle = page.subTitle;
        function restoreHeading() {
            page.left.disconnect(restoreHeading);
            page.title = title;
            page.subTitle = subtitle;
        }

        // Preserve the step list's localized titles when navigating.
        page.left.connect(restoreHeading);
        page.title = headerWordmark();
        page.subTitle = " ";
        capture(name);
        advance(name, page);
    };
});
