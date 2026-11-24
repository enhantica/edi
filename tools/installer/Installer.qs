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
var installPageReady = false;
var progressHooked = false;
// A maintenance tool that updated its own component restarts at its first page; a captured walk then ends there.
var maintenanceWalked = false;
// The maintenance tool's mode in capture mode (EDI_INSTALLER_MAINTENANCE_MODE): add (add or remove components),
// update, or remove (everything, the default).
var maintenanceMode = installer.environmentVariable("EDI_INSTALLER_MAINTENANCE_MODE") || "remove";

// Taken a moment later by a detached process, once the page has painted.
function capture(name) {
    if (captureFolder === "")
        return;
    // The progress page is gone within a second for the small marker installer; the first page needs the window up.
    var delay = name === "PerformInstallation" ? "0.2" : name === "Introduction" ? "2" : "1";
    var mode = installer.isInstaller() ? "installer" : "maintenance-" + maintenanceMode;
    var file = captureFolder + "/" + mode + "-" + name + "-" + (darkTheme() ? "dark" : "light") + ".png";
    if (systemInfo.kernelType === "winnt") {
        // A process started here cannot take a screenshot; capture_pages.py takes them on Windows.
    } else if (systemInfo.kernelType === "darwin") {
        installer.executeDetached("/bin/sh", ["-c", "sleep " + delay + "; /usr/sbin/screencapture -x '" + file + "'"]);
    } else {
        installer.executeDetached("/bin/sh", ["-c", "sleep " + delay + "; import -window root '" + file + "'"]);
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
    // The summary page commits by itself (installPage below).
    if (name === "ReadyForInstallation" && installer.isInstaller())
        return;
    if (name === "PerformInstallation") {
        // The Framework moves on when it is done (its details are closed on this page, below); this is the backstop.
        var next = function () { gui.clickButton(buttons.NextButton, 1500); };
        installer.installationFinished.connect(next);
        installer.uninstallationFinished.connect(next);
        return;
    }
    // The maintenance tool's last page finishes with its relabelled Cancel button; its commit button restarts it.
    var finish = installer.isInstaller() || installer.isUninstaller() ? buttons.FinishButton : buttons.CancelButton;
    if (name === "Finished")
        maintenanceWalked = true;
    gui.clickButton(name === "Finished" ? finish : buttons.NextButton, 2500);
}

function Controller() {
    // No component tree: macOS accessibility clients crash the Framework's Qt on it (edi #150); the one choice it
    // offered, the AI assistant, is a checkbox (assistantscript.qs).
    installer.setDefaultPageVisible(QInstaller.ComponentSelection, false);
    // No page titles from the start: Qt decides whether a page has a header as it opens, before its callback runs.
    [QInstaller.Introduction, QInstaller.TargetDirectory, QInstaller.ReadyForInstallation,
     QInstaller.PerformInstallation, QInstaller.InstallationFinished].forEach(function (id) {
        var start = gui.pageById(id);
        if (start) {
            start.title = "";
            start.subTitle = "";
        }
    });
    // No Settings button: the system proxy is used by default, and nobody needs to edit repositories here.
    gui.showSettingsButton(false);
    // The licence was accepted when installing; the maintenance tool does not ask again.
    if (!installer.isInstaller())
        installer.setDefaultPageVisible(QInstaller.LicenseCheck, false);
    // The capture checks prove our resources are in the built installer: the text and the check box's tick.
    if (captureFolder !== "") {
        [":/metadata/translations/ifw_en.qm", ":/metadata/edi/CheckMark.png"].forEach(function (path) {
            if (!installer.fileExists(path))
                console.log("edi resource missing: " + path);
        });
    }
    if (installer.isInstaller()) {
        // Three pages: Install (the folder and the choices), Installing, Done. The welcome and summary pages pass by
        // themselves; the Start menu entry is "EasyDiffraction" without asking.
        installer.setDefaultPageVisible(QInstaller.StartMenuSelection, false);
        gui.setWizardPageButtonText(QInstaller.TargetDirectory, buttons.NextButton, "Install");
    }
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
    keepUntitled(page);
    var mark = gui.findChild(page, "FormLogo");
    if (mark) {
        mark.textFormat = 1;  // Qt.RichText
        mark.text = headerWordmark();
        mark.visible = true;
    }
    // Adding components in capture mode adds the assistant, so the mode has something to do.
    var box = captureFolder !== "" ? gui.findChild(page, "AssistantCheckBox") : null;
    if (box)
        box.checked = true;
    capture("AssistantForm");
    advance("AssistantForm", page);
};

// The assistant checkbox on the folder page decides the component, applied when that page is left and again before
// the summary counts what is installed: a selection made while the component scripts load does not last.
var assistantComponent = "org.easydiffraction.app.assistant";
var assistantHooked = false;
var warningHooked = false;

function assistantChosen() {
    var page = gui.pageWidgetByObjectName("TargetDirectoryPage");
    var box = page ? gui.findChild(page, "AssistantCheckBox") : null;
    return box ? box.checked : false;
}

function applyAssistantChoice() {
    if (!installer.isInstaller())
        return;
    if (assistantChosen())
        installer.selectComponent(assistantComponent);
    else
        installer.deselectComponent(assistantComponent);
}

// Removing everything calls its summary step "Ready to remove" (the Framework's "Installation Summary"); the step list
// takes page titles as the next page opens, so it is set when the first page is left.
var introductionHooked = false;
var summaryTitle = "";

function nameSummaryStep() {
    var intro = gui.pageWidgetByObjectName("IntroductionPage");
    var remove = intro ? gui.findChild(intro, "UninstallerRadioButton") : null;
    var summary = gui.pageWidgetByObjectName("ReadyForInstallationPage");
    if (!summary)
        return;
    if (summaryTitle === "")
        summaryTitle = summary.title;
    summary.title = remove && remove.checked ? "Ready to remove" : summaryTitle;
}

// The summary page in plain text, as the other pages: a heading, one line per component with its size, where it goes
// and the space it needs. The Framework's framed tables (tree views, which macOS accessibility clients crashed, edi
// #150) and its space line are hidden; the space figures are read from that line, the only place that has them.
function sizeText(bytes) {
    var units = ["B", "KB", "MB", "GB"];
    var value = Number(bytes);
    var unit = 0;
    while (value >= 1000 && unit < units.length - 1) {
        value /= 1000;
        unit += 1;
    }
    return (unit === 0 ? value : value.toFixed(2)) + " " + units[unit];
}

function summaryRows(removing) {
    var rows = "";
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var c = all[i];
        if (c.value("Virtual") === "true")
            continue;
        var counted = removing ? c.uninstallationRequested() : c.installationRequested();
        if (!counted)
            continue;
        rows += '<tr><td>' + c.value("DisplayName") + '</td><td align="right">'
            + sizeText(c.value("UncompressedSize") || 0) + '</td></tr>';
    }
    return rows;
}

function writeSummary(page) {
    ["InstallComponentsWidget", "UninstallComponentsWidget"].forEach(function (container) {
        var widget = gui.findChild(page, container);
        if (widget)
            widget.visible = false;
    });
    var summary = gui.findChild(page, "RemoveAllMsgLabel");
    if (!summary)
        return;
    var removing = installer.isUninstaller();
    var heading = installer.isInstaller() ? "Ready to install" : installer.isUpdater() ? "Ready to update"
        : removing ? "Ready to remove" : "Ready to apply your changes";
    var target = installer.value("TargetDir");
    var text = logo() + "<p><b>" + heading + "</b></p>";
    var adding = summaryRows(false);
    var dropping = removing ? summaryRows(true) : (installer.isPackageManager() ? summaryRows(true) : "");
    if (adding !== "")
        text += '<table width="100%" cellpadding="2">' + adding + "</table>";
    if (dropping !== "")
        text += (removing ? "" : "<p>Removed:</p>") + '<table width="100%" cellpadding="2">' + dropping + "</table>";
    if (removing) {
        text += '<p style="color: ' + (darkTheme() ? "#FFAB91" : "#FF5722") + '">Everything in ' + target
            + " will be removed.</p>";
    } else if (installer.isInstaller()) {
        text += "<p>Install to " + target + "</p>";
    }
    // The space line: "Space required: X" and "Space available: Y", read and said once, plainly.
    var space = gui.findChild(page, "SpaceItem");
    if (space && !removing) {
        var needed = "", available = "", warned = false;
        var labels = gui.findChildren(space, "");
        for (var j = 0; j < labels.length; ++j) {
            var line = String(labels[j].text || "");
            var figure = line.replace(/^[^:]*:\s*/, "");
            if (/required/i.test(line))
                needed = figure;
            else if (/available/i.test(line) && /\d/.test(figure))
                available = figure;
            if (/^Space(Warning|Recommendation)$/.test(labels[j].objectName) && labels[j].visible)
                warned = true;
        }
        if (needed !== "")
            text += "<p>Space: " + needed + " needed · " + available + " available</p>";
        space.visible = warned;  // a shortage stays said as the Framework says it
    }
    summary.textFormat = 1;  // Qt.RichText
    summary.text = text;
    summary.visible = true;
}

// The install page: what EasyDiffraction is, where it goes, the choices, and the space it needs.
var licenseUrl = "https://www.gnu.org/licenses/gpl-3.0.html";

function accent() {
    return darkTheme() ? "#4ec1ef" : "#00a3e3";
}

function installPageField(name) {
    var page = gui.pageWidgetByObjectName("TargetDirectoryPage");
    return page ? gui.findChild(page, name) : null;
}

function licenseAccepted() {
    var box = installPageField("LicenseCheckBox");
    return box ? box.checked : false;  // no readable choice is no acceptance
}

function freeSpace(folder) {
    // The nearest existing folder's volume: df on macOS and Linux, PowerShell's drive on Windows. Only for a whole
    // absolute path; the walk up stops when a step no longer shortens it.
    var absolute = systemInfo.kernelType === "winnt" ? /^[A-Za-z]:[\\/]/.test(folder) : folder.charAt(0) === "/";
    if (!absolute)
        return NaN;
    var path = folder;
    while (!installer.fileExists(path)) {
        var shorter = path.replace(/[\\/][^\\/]*[\\/]?$/, "");
        if (shorter === path || shorter.length < (systemInfo.kernelType === "winnt" ? 2 : 1))
            return NaN;
        path = shorter;
    }
    if (systemInfo.kernelType === "winnt") {
        var drive = path.substring(0, 1);
        var free = installer.execute("powershell", ["-NoProfile", "-Command", "(Get-PSDrive " + drive + ").Free"]);
        return free[1] === 0 ? Number(String(free[0]).trim()) : NaN;
    }
    var df = installer.execute("/bin/df", ["-k", path]);
    if (df[1] !== 0)
        return NaN;
    var fields = String(df[0]).trim().split("\n").pop().trim().split(/\s+/);
    return Number(fields[3]) * 1024;
}

function neededSpace() {
    var bytes = 0;
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var name = all[i].name;
        if (name === assistantComponent && !assistantChosen())
            continue;
        bytes += Number(all[i].value("UncompressedSize") || 0);
    }
    return bytes;
}

function updateSpace() {
    var label = installPageField("SpaceLabel");
    var folder = installPageField("TargetDirectoryLineEdit");
    if (!label || !folder)
        return;
    var free = freeSpace(String(folder.text));
    label.text = sizeText(neededSpace()) + " needed" + (isNaN(free) ? "" : " · " + sizeText(free) + " available");
}

function setupInstallPage(page) {
    var intro = gui.findChild(page, "MessageLabel");
    if (intro) {
        intro.textFormat = 1;  // Qt.RichText
        intro.text = logo() + "<p>EasyDiffraction calculates diffraction patterns from a structural model and fits its "
            + "parameters to experimental data.</p><p>Install to</p>";
    }
    var link = gui.findChild(page, "LicenseLink");
    if (link) {
        link.textFormat = 1;
        link.text = '<a style="color: ' + accent() + '; text-decoration: none" href="' + licenseUrl
            + '">read online <img src=":/metadata/edi/' + (darkTheme() ? "external-dark" : "external")
            + '.png" width="12" height="12"></a>';
    }
    var license = gui.findChild(page, "LicenseCheckBox");
    var shortcut = gui.findChild(page, "ShortcutCheckBox");
    var assistantBox = gui.findChild(page, "AssistantCheckBox");
    var folder = gui.findChild(page, "TargetDirectoryLineEdit");
    if (!installPageReady) {
        if (license)
            license.checked = true;
        if (shortcut) {
            shortcut.visible = systemInfo.kernelType !== "darwin";
            shortcut.checked = true;
            shortcut.toggled.connect(function (on) { installer.setValue("EdiDesktopShortcut", on ? "true" : "false"); });
        }
        if (assistantBox)
            assistantBox.toggled.connect(updateSpace);
        // The folder is probed (its disk, an installation in it) when its editing is done, never per keystroke.
        if (folder)
            folder.editingFinished.connect(refreshInstallPage);
        installPageReady = true;
    }
    refreshInstallPage();
}

// What the chosen folder says: an installation already in it is updated by its maintenance tool, not installed
// twice. A licence refusal stays said until Install is pressed again.
var licenseRefused = false;

function refreshInstallPage() {
    var notice = installPageField("NoticeLabel");
    var folder = installPageField("TargetDirectoryLineEdit");
    var target = folder ? String(folder.text) : installer.value("TargetDir");
    var tool = target + (systemInfo.kernelType === "darwin" ? "/MaintenanceTool.app"
                         : systemInfo.kernelType === "winnt" ? "/MaintenanceTool.exe" : "/MaintenanceTool");
    if (notice) {
        var lines = [];
        if (licenseRefused)
            lines.push("Accept the license to install EasyDiffraction.");
        if (target !== "" && installer.fileExists(tool))
            lines.push("EasyDiffraction is already installed here. To update it, open its Maintenance Tool and choose "
                + "Update.");
        notice.text = lines.join(" ");
        notice.visible = notice.text !== "";
    }
    updateSpace();
}



var wordmark = "";

// No title and no subtitle, so Qt draws no header. The Framework sets some again as a page opens (the maintenance
// tool's first page, an inserted page), so they are cleared whenever the page says it was entered or changed.
var untitledPages = [];
function keepUntitled(page) {
    function clear() {
        if (page.title !== "")
            page.title = "";
        if (page.subTitle !== "")
            page.subTitle = "";
    }
    clear();
    if (untitledPages.indexOf(page) < 0) {
        untitledPages.push(page);
        page.entered.connect(clear);
        page.completeChanged.connect(clear);
    }
}

// The logo heading each page's own content (the pages have no titles, so Qt shows no header).
function logo() {
    return "<p>" + headerWordmark() + "</p>";
}

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
        if (name === "Introduction" && !installer.isInstaller() && captureFolder !== "" && maintenanceWalked) {
            // Closed as a person would, answering its "quit?" question with Yes.
            installer.setMessageBoxAutomaticAnswer("cancelInstallation", QMessageBox.Yes);
            gui.clickButton(buttons.CancelButton, 50);
            return;
        }
        if (name === "Introduction" && !installer.isInstaller()) {
            var ask = gui.findChild(page, "MessageLabel");
            if (ask) {
                ask.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop
                ask.textFormat = 1;  // Qt.RichText
                ask.text = logo() + "<p>What would you like to do?</p>";
            }
            var update = gui.findChild(page, "UpdaterRadioButton");
            if (update && captureFolder === "")
                update.checked = true;
            if (!introductionHooked) {
                page.left.connect(nameSummaryStep);
                introductionHooked = true;
            }
        }

        // The summary without the Framework's component trees: a tree view is what macOS accessibility clients
        // crashed (edi #150), so none may show. One plain sentence says what happens.
        if (name === "ReadyForInstallation")
            writeSummary(page);
        // The installer has no summary page of its own: Install on the first page commits, unless the licence box
        // was cleared, which brings the first page back saying why.
        if (name === "ReadyForInstallation" && installer.isInstaller()) {
            applyAssistantChoice();
            // Clicked a moment later, outside the Framework's own page change, which a nested click leaves half done.
            licenseRefused = !licenseAccepted();
            if (!licenseRefused) {
                gui.clickButton(buttons.CommitButton, 50);
            } else {
                refreshInstallPage();
                gui.clickButton(buttons.BackButton, 50);
            }
            return;
        }

        // The welcome page passes by itself (online, it fetches the component list meanwhile).
        // The welcome page passes by itself, in captures too: the design has no welcome page.
        if (name === "Introduction" && installer.isInstaller()) {
            gui.clickButton(buttons.NextButton, 50);
            return;
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
            setupInstallPage(page);
            // The warning line takes a line's height even when empty: shown only while it says something.
            var warning = gui.findChild(page, "WarningLabel");
            var folder = gui.findChild(page, "TargetDirectoryLineEdit");
            var showWarning = function () {
                if (warning)
                    warning.visible = warning.text !== "";
            };
            showWarning();
            if (folder && !warningHooked) {
                folder.textChanged.connect(showWarning);
                warningHooked = true;
            }
            var assistantBox = gui.findChild(page, "AssistantCheckBox");
            // Capture mode can clear it, to check both states (EDI_INSTALLER_ASSISTANT=off).
            if (assistantBox && captureFolder !== "" && installer.environmentVariable("EDI_INSTALLER_ASSISTANT") === "off")
                assistantBox.checked = false;
            if (!assistantHooked) {
                page.left.connect(applyAssistantChoice);
                assistantHooked = true;
            }
        }
        if (name === "LicenseAgreement" || name === "ReadyForInstallation")
            applyAssistantChoice();

        // Installing: the bar and one status line, no details.
        if (name === "PerformInstallation") {
            // --verbose opens the details, which stops the Framework moving on by itself when done: they are closed
            // with their own button, which turns that back on, and the button and download count are hidden.
            var detailsBrowser = gui.findChild(page, "DetailsBrowser");
            var detailsButton = gui.findChild(page, "DetailsButton");
            if (detailsBrowser && detailsBrowser.visible && detailsButton)
                detailsButton.click();
            // The product-images area is invisible but takes the page's height, which left our bar far below.
            ["DetailsButton", "DownloadStatus", "ProductImagesScrollArea", "ProductImagesLabel"].forEach(function (hidden) {
                var widget = gui.findChild(page, hidden);
                if (widget)
                    widget.visible = false;
            });
            // Our bar with its percentage beside it (ProgressForm.ui), fed from the Framework's bar, which is
            // hidden; where our form is missing (no assistant component loaded), the Framework's bar stays.
            var bar = gui.findChild(page, "ProgressBar");
            var label = gui.findChild(page, "ProgressLabel");
            var ours = gui.findChild(page, "EdiProgressBar");
            var percent = gui.findChild(page, "EdiProgressPercent");
            var status = gui.findChild(page, "EdiProgressStatus");
            var mark = gui.findChild(page, "EdiProgressLogo");
            if (bar && label && ours && percent && status && !progressHooked) {
                bar.visible = false;
                label.visible = false;
                if (mark) {
                    mark.textFormat = 1;  // Qt.RichText
                    mark.text = headerWordmark();
                }
                // One plain status line of our own: the Framework's changes per step and says little.
                status.text = installer.isInstaller() ? "Installing EasyDiffraction…"
                    : installer.isUninstaller() ? "Removing EasyDiffraction…" : "Updating EasyDiffraction…";
                bar.valueChanged.connect(function (value) {
                    var share = bar.maximum > bar.minimum
                        ? Math.round(100 * (value - bar.minimum) / (bar.maximum - bar.minimum)) : 0;
                    ours.value = share;
                    percent.text = share + "%";
                });
                progressHooked = true;
            }
        }

        // Done: where to find it, and the program opened directly if wanted. No folder path.
        if (name === "Finished") {
            var done = gui.findChild(page, "MessageLabel");
            // Where it really is: the shortcuts made, and the folder when it is not the usual one.
            var shortcut = installer.value("EdiDesktopShortcut") !== "false";
            var target = String(installer.value("TargetDir"));
            var where = systemInfo.kernelType === "winnt" ? (shortcut ? "in the Start menu and on your desktop"
                                                                      : "in the Start menu")
                : systemInfo.kernelType === "darwin" ? "in your Applications folder"
                    : (shortcut ? "in your applications menu and on your desktop" : "in your applications menu");
            if (done && installer.isInstaller() && installer.status === QInstaller.Success) {
                // A large check in the accent above the sentence (the app's circle-check icon).
                done.textFormat = 1;  // Qt.RichText
                done.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
                done.text = logo() + '<p><img src=":/metadata/edi/' + (darkTheme() ? "done-dark" : "done")
                    + '.png" width="64" height="64"></p><p>EasyDiffraction is installed.</p><p>You\'ll find it ' + where
                    + ".</p>";
            }
            // The maintenance tool keeps the Framework's own sentence (updated, removed), under the logo.
            if (done && !installer.isInstaller() && String(done.text).indexOf("<img") < 0) {
                done.textFormat = 1;  // Qt.RichText
                done.text = logo() + "<p>" + done.text + "</p>";
            }
            ["LocationLabel", "FinishText"].forEach(function (hidden) {
                var widget = gui.findChild(page, hidden);
                if (widget)
                    widget.visible = false;
            });
            // Ticked; captures keep it ticked and clear what it would open, as the marker installer has no program.
            var run = gui.findChild(page, "RunItCheckBox");
            if (run)
                run.checked = true;
            if (captureFolder !== "")
                installer.setValue("RunProgram", "");
        }

        if (name === "TargetDirectory" && systemInfo.kernelType === "darwin") {
            var directory = gui.findChild(page, "TargetDirectoryLineEdit");
            directory.styleSheet = "margin-top: 4px;";
        }

        // No title, so no header: the logo heads the page's own content.
        keepUntitled(page);
        capture(name);
        advance(name, page);
    };
});
