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
// The installer on Linux shows its first page once more after Finish; that is not a page of the walk.
var installerWalked = false;
// The maintenance tool's mode in capture mode (EDI_INSTALLER_MAINTENANCE_MODE): add (add or remove components),
// update, or remove (everything, the default).
// Updating comes in three: update (as the page opens), updatekept (the assistant unticked) and updatewithout (the
// assistant not installed); their pages are named after them.
var maintenanceMode = installer.environmentVariable("EDI_INSTALLER_MAINTENANCE_MODE") || "remove";
var maintenanceAction = maintenanceMode.indexOf("update") === 0 ? "update" : maintenanceMode;

function pageId(name) {
    var mode = installer.isInstaller() ? "installer" : "maintenance-" + maintenanceMode;
    return mode + "-" + name + "-" + (darkTheme() ? "dark" : "light");
}

// Every page a captured walk shows, in order, one line each in pages.log: the checks compare it with the pages the
// walk must show, and the accessibility client reads its last line to know which page it is reading.
// Written before the page can be looked at: this waits for the write, without the event loop the Framework's own
// file operation runs (which let the whole installation go by on the progress page), so nothing sees the new page
// under the old page's name.
function notePage(name) {
    if (captureFolder === "")
        return;
    var line = pageId(name);
    if (systemInfo.kernelType === "winnt")
        installer.execute("cmd.exe", ["/c", "echo " + line + ">>" + captureFolder.replace(/\//g, "\\")
            + "\\pages.log"]);
    else
        installer.execute("/bin/sh", ["-c", 'printf "%s\\n" "$1" >> "$2"', "sh", line,
            captureFolder + "/pages.log"]);
}

// Moves a captured walk on from a page with `button` after `delay` ms. Each page stays long enough for its picture
// and for the accessibility client to read it; the progress page is held by the components (holdProgress in their
// scripts), as the Framework leaves it by itself.
function proceed(name, button, delay) {
    gui.clickButton(button, delay);
}

// Taken a moment later by a detached process, once the page has painted.
function capture(name) {
    if (captureFolder === "")
        return;
    notePage(name);
    // The progress page is gone within a second for the small marker installer; the first page needs the window up.
    var delay = name === "PerformInstallation" ? "0.2" : name === "Introduction" ? "2" : "1";
    var file = captureFolder + "/" + pageId(name) + ".png";
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
        var choice = maintenanceChoices(page)[maintenanceAction];
        if (choice)
            choice.checked = true;
    }
    // The summary page commits by itself (installPage below).
    if (name === "ReadyForInstallation" && installer.isInstaller())
        return;
    if (name === "PerformInstallation") {
        // The Framework moves on when it is done (its details are closed on this page, below); this is the backstop.
        var next = function () { proceed("PerformInstallation", buttons.NextButton, 1500); };
        installer.installationFinished.connect(next);
        installer.uninstallationFinished.connect(next);
        installer.updateFinished.connect(next);
        return;
    }
    // The maintenance tool's last page finishes with its relabelled Cancel button; its commit button restarts it.
    // Leaving it that way ends the tool with status 1 (the Framework counts the Cancel button as cancelled), after
    // the work was done; a11y-check.sh accepts that only once the Finished page was shown and the log says done.
    var finish = installer.isInstaller() || installer.isUninstaller() ? buttons.FinishButton : buttons.CancelButton;
    if (name === "Finished") {
        maintenanceWalked = true;
        installerWalked = true;
    }
    proceed(name, name === "Finished" ? finish : buttons.NextButton, 2500);
}

function Controller() {
    // No component tree: macOS accessibility clients crash the Framework's Qt on it (edi #150); the one choice it
    // offered, the AI assistant, is a checkbox (assistantscript.qs).
    installer.setDefaultPageVisible(QInstaller.ComponentSelection, false);
    // No page titles from the start: Qt decides whether a page has a header as it opens, before its callback runs.
    [QInstaller.Introduction, QInstaller.TargetDirectory, QInstaller.ReadyForInstallation,
     QInstaller.PerformInstallation, QInstaller.InstallationFinished].forEach(function (id) {
        var start = typeof gui.pageById === "function" ? gui.pageById(id) : null;
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
    // The progress page titles itself as the work goes (a header band); untitled again each time.
    installer.titleMessageChanged.connect(function () {
        var perform = gui.pageWidgetByObjectName("PerformInstallationPage");
        if (perform) {
            perform.title = "";
            perform.subTitle = "";
        }
    });
    installer.installationFinished.connect(clearQuarantine);
    installer.updateFinished.connect(clearQuarantine);
}

// edi's light and dark themes for the pages (Installer.qss, filled in by package.py). Scripts can reach the pages but
// not the window around them, which follows the system palette (InstallerChrome.qss).
var lightStylesheet = "@LIGHT_STYLESHEET@";
var darkStylesheet = "@DARK_STYLESHEET@";

function themePage(page) {
    if (!page)
        return;
    page.styleSheet = darkTheme() ? darkStylesheet : lightStylesheet;
    templatePage(page);
}

// The one layout every page follows: the logo first, one step (16) under it (logo()), then the heading, then the
// rows, each 8 under the one above and all on one left edge. The Framework's own layouts have no names (ours all
// have one), so a script finds them as the page's unnamed children; each that has a spacing gets the row gap.
var rowGap = 8;
//
// The page's own layout (its first unnamed layout; on the summary and progress pages the Framework names it
// BaseLayout) gets the window padding every page shares: the Framework's default, read from the last page's layout.
// Every other unnamed layout of the Framework's is nested and gets no margins: the maintenance choices sit in an
// inner widget whose layout took the style's margins (10 px in on macOS). Margins are copied from layouts that
// have them, as a script cannot make the value.
function isLayout(object) {
    return object && typeof object.spacing === "number" && object.sizeConstraint !== undefined;
}

// Our own layouts (the forms') are named so; every other layout is the Framework's.
var ownLayout = /^(AssistantLayout|DoneLayout|ProgressColumn|ProgressLayout|[A-Za-z]*Row)$/;

function layoutsOf(page) {
    var found = [];
    var all = page ? gui.findChildren(page, null) : [];
    for (var i = 0; i < all.length; ++i) {
        if (isLayout(all[i]) && !ownLayout.test(all[i].objectName))
            found.push(all[i]);
    }
    return found;
}

function firstLayout(page) {
    return layoutsOf(page)[0] || null;
}

function templatePage(page) {
    logLayout(page, "before");
    try {
        applyTemplate(page);
    } catch (error) {
        console.log("edi page template not applied: " + error);
    }
    logLayout(page, "after");
    if (captureFolder !== "")
        later(400, function () { logLayout(page, "shown"); });
}

// Captures log each page's layouts and widgets before and after the template, one line each: what the template's
// writes did (edi-layout lines in the log).
function logLayout(page, when) {
    if (captureFolder === "" || !page)
        return;
    var all = gui.findChildren(page, null);
    for (var i = 0; i < all.length; ++i) {
        var item = all[i];
        if (!item)
            continue;
        var line = "edi-layout " + page.objectName + " " + when + " " + String(item);
        if (i === 0)
            console.log("edi-layout " + page.objectName + " " + when + " title='" + page.title + "' subTitle='"
                + page.subTitle + "' page x=" + page.x + " y=" + page.y + " w=" + page.width + " h=" + page.height);
        if (isLayout(item))
            line += " spacing=" + item.spacing + " margins=" + String(item.contentsMargins);
        else if (typeof item.x === "number" && typeof item.width === "number")
            line += " x=" + item.x + " y=" + item.y + " w=" + item.width + " h=" + item.height
                + " visible=" + item.visible;
        else
            continue;
        console.log(line);
    }
}

function applyTemplate(page) {
    var padded = firstLayout(gui.pageWidgetByObjectName("FinishedPage"));
    var perform = gui.pageWidgetByObjectName("PerformInstallationPage");
    var flat = perform ? gui.findChild(perform, "TopLayout") : null;
    // The page's own layout comes first: the Framework makes it before what it holds.
    var layouts = layoutsOf(page);
    for (var i = 0; i < layouts.length; ++i) {
        var layout = layouts[i];
        if (layout.spacing !== rowGap)
            layout.spacing = rowGap;
        var source = i === 0 ? padded : flat;
        if (source && source !== layout)
            layout.contentsMargins = source.contentsMargins;
    }
    // The installer's page hides the form's own logo (the page's text has it), and the space under it.
    var logoRow = installer.isInstaller() ? gui.findChild(page, "LogoRow") : null;
    if (logoRow && flat)
        logoRow.contentsMargins = flat.contentsMargins;
    if (page.objectName === "IntroductionPage" && layouts.length > 1)
        [0, 150].forEach(function (delay) {
            later(delay, function () { settleChoices(page, layouts[0], layouts[1]); });
        });
}

// The choices in the order they read best, Update first. The Framework makes its three radio buttons in an order of its
// own (change, update, remove) and its layout cannot be reordered from a script, so the first two trade places by
// meaning: each one's words and the mode it sets are changed together, here, so that a button never says one thing
// and does another. The Framework sets its own mode when a button is chosen; ours is set right after it.
var choicesHooked = false;

function maintenanceChoices(page) {
    return {update: gui.findChild(page, "PackageManagerRadioButton"), add: gui.findChild(page, "UpdaterRadioButton"),
            remove: gui.findChild(page, "UninstallerRadioButton")};
}

function setChosenMode(page) {
    var choices = maintenanceChoices(page);
    if (choices.update && choices.update.checked)
        installer.setUpdater();
    else if (choices.add && choices.add.checked)
        installer.setPackageManager();
}

function orderChoices(page) {
    var choices = maintenanceChoices(page);
    if (!choices.update || !choices.add)
        return;
    if (!choicesHooked) {
        choices.update.text = "Update EasyDiffraction";
        choices.add.text = "Change components";
        [choices.update, choices.add].forEach(function (choice) {
            choice.toggled.connect(function () { setChosenMode(page); });
            choice.clicked.connect(function () { setChosenMode(page); });
        });
        choicesHooked = true;
    }
    choices.update.checked = true;
    // Shown checked already, it sends nothing: the mode is set here too.
    setChosenMode(page);
}

// The maintenance choices are the Framework's radio buttons straight in a column, which on macOS reach past their
// cells above and below, so their frames stand closer than the column's spacing. Once shown, each spacing is set so
// the frames are one row gap apart: under the question, and between the choices.
function bounded(value, most) {
    // A window too small for its rows squeezes them over one another; measuring that and adding the difference would
    // squeeze them further, each time more. A correction therefore never passes a small limit.
    return Math.max(0, Math.min(most, value));
}

// A layout's spacing by how far its drawn gap is off, once per laid-out gap: asked again before the page is laid out
// anew, the gap reads the same and nothing more is done.
var adjusted = {};
function adjustOnce(layout, gap) {
    var done = adjusted[String(layout)];
    if (done && done.gap === gap && done.spacing === layout.spacing)
        return;
    layout.spacing = bounded(layout.spacing + rowGap - gap, 2 * rowGap + 1);
    adjusted[String(layout)] = {gap: gap, spacing: layout.spacing};
}

function settleChoices(page, column, choices) {
    var question = gui.findChild(page, "MessageLabel");
    var radios = ["PackageManagerRadioButton", "UpdaterRadioButton", "UninstallerRadioButton"].map(function (name) {
        return gui.findChild(page, name);
    }).filter(function (radio) { return radio && radio.visible; });
    if (radios.length > 1)
        adjustOnce(choices, radios[1].y - (radios[0].y + radios[0].height));
    // The choices' widget: the page's one unnamed widget (the radios' places are inside it).
    var holder = gui.findChildren(page, "").filter(function (item) {
        return item && !isLayout(item) && typeof item.y === "number" && item.visible;
    })[0];
    if (question && holder && radios.length > 0)
        column.spacing = bounded(rowGap - radios[0].y, 2 * rowGap);
    later(100, function () { logLayout(page, "settled"); });
}

// The assistant's own page in the maintenance tool (assistantscript.qs).
Controller.prototype.DynamicAssistantFormCallback = function () {
    var page = gui.pageWidgetByObjectName("DynamicAssistantForm");
    themePage(page);
    // That is our form; the page around it, whose layout the Framework made without margins, takes the template.
    templatePage(gui.pageByObjectName("DynamicAssistantForm"));
    page.title = "";
    page.subTitle = "";
    var mark = gui.findChild(page, "FormLogo");
    if (mark) {
        mark.textFormat = 1;  // Qt.RichText
        mark.text = headerWordmark();
        mark.visible = true;
    }
    // Adding components in capture mode turns the assistant over (added if absent, removed if there), so the mode
    // always has work to do and its progress page shows.
    var box = captureFolder !== "" ? gui.findChild(page, "AssistantCheckBox") : null;
    if (box && maintenanceMode === "add")
        box.checked = !box.checked;
    if (box && maintenanceMode === "updatekept")
        box.checked = false;
    settleSoon(page);
    capture("AssistantForm");
    advance("AssistantForm", page);
};

// The assistant checkbox on the folder page decides the component, applied when that page is left and again before
// the summary counts what is installed: a selection made while the component scripts load does not last.
var assistantComponent = "org.easydiffraction.app.assistant";
var appComponent = "org.easydiffraction.app";
var assistantHooked = false;

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

// The Framework's size text ("36.26 MB", in steps of 1024) in bytes; 0 where there is none.
function frameworkBytes(figure) {
    var parts = /([\d.]+)\s*(bytes|KB|MB|GB|TB)/.exec(String(figure));
    return parts ? Math.round(Number(parts[1]) * Math.pow(1024, ["bytes", "KB", "MB", "GB", "TB"].indexOf(parts[2]))) : 0;
}

// `total`, where given, is what the whole change takes by the Framework's count, which includes parts the list does
// not name (the maintenance tool itself): EasyDiffraction's row carries them, so the rows add up to the line below.
function summaryRows(removing, total) {
    var named = total ? summaryBytes(removing) : 0;
    var rows = "";
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var c = all[i];
        if (c.value("Virtual") === "true")
            continue;
        var counted = removing ? c.uninstallationRequested() : c.installationRequested();
        if (!counted)
            continue;
        rows += '<tr><td style="padding: 2px 0 2px 4px">' + c.value("DisplayName") + '</td><td align="right">'
            + sizeText(Number(c.value("UncompressedSize") || 0)
                       + (c.name === appComponent ? Math.max(0, (total || 0) - named) : 0)) + '</td></tr>';
    }
    return rows;
}

// The bytes the components to be installed (or removed) take.
function summaryBytes(removing) {
    var bytes = 0;
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var c = all[i];
        if (c.value("Virtual") !== "true" && (removing ? c.uninstallationRequested() : c.installationRequested()))
            bytes += Number(c.value("UncompressedSize") || 0);
    }
    return bytes;
}

// A list under its heading, its items 4 px in from the heading's edge (each name's cell padding).
function summaryTable(rows) {
    return '<table width="100%" cellspacing="0" cellpadding="0">' + rows + "</table>";
}

// A path that may break at its separators instead of inside a name (a zero-width space after each).
function breakablePath(path) {
    return String(path).replace(/([\/\\])/g, "$1\u200b");
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
    var text = logo() + PARA + "<b>" + heading + "</b></p>";
    // "Space required: X" and "Space available: Y" from the Framework's space line, the only place that has them.
    var space = gui.findChild(page, "SpaceItem");
    var needed = "", available = "", warned = false;
    var labels = space ? gui.findChildren(space, "") : [];
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
    var neededBytes = installer.isUpdater() ? frameworkBytes(needed) : 0;
    var adding = summaryRows(false, neededBytes);
    var dropping = removing ? summaryRows(true) : (installer.isPackageManager() ? summaryRows(true) : "");
    if (adding !== "")
        text += summaryTable(adding);
    if (dropping !== "")
        text += (removing ? "" : PARA + "Removed:</p>") + summaryTable(dropping);
    if (removing) {
        text += '<p style="margin: 8px 0 0 0; color: ' + warning() + '">Everything in ' + breakablePath(target)
            + " will be removed.</p>";
    } else if (installer.isInstaller()) {
        text += PARA + "Install to " + breakablePath(target) + "</p>";
    }
    // Adding or removing components: what the change needs or frees, and nothing when it changes no files.
    if (installer.isPackageManager()) {
        var added = summaryBytes(false);
        var freed = summaryBytes(true);
        if (added > 0)
            text += PARA + sizeText(added) + " needed</p>";
        else if (freed > 0)
            text += PARA + sizeText(freed) + " freed</p>";
        if (space)
            space.visible = false;
    } else if (space && !removing) {
        // A change that needs no space (a figure of 0) says nothing about space.
        if (needed !== "" && parseFloat(needed) > 0)
            text += PARA + (neededBytes > 0 ? sizeText(neededBytes) : needed) + " needed · " + available
                + " available</p>";
        space.visible = warned;  // a shortage stays said as the Framework says it
    }
    summary.textFormat = 1;  // Qt.RichText
    summary.text = text;
    summary.visible = true;
}

// The install page: what EasyDiffraction is, where it goes, the choices, and the space it needs.
var licenseUrl = "https://www.gnu.org/licenses/gpl-3.0.html";

function warning() {
    return darkTheme() ? "@DARK_WARNING@" : "@LIGHT_WARNING@";
}

// The small check before a done sentence: a character of the text, in the app's success green.
function checkMark() {
    return '<span style="color: ' + success() + '">\u2713</span>';
}

function success() {
    return darkTheme() ? "@DARK_SUCCESS@" : "@LIGHT_SUCCESS@";
}

var openHooked = false;

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
        // PowerShell by its system path (an installer's PATH may lack it); the first number it prints, as its output
        // can carry a byte-order mark or a carriage return.
        var shell = installer.value("RootDir", "C:").replace(/[\\/]$/, "")
            + "\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe";
        if (!installer.fileExists(shell))
            shell = "powershell.exe";
        var free = installer.execute(shell, ["-NoProfile", "-NonInteractive", "-Command",
            "[System.IO.DriveInfo]::new('" + path.substring(0, 1) + ":\\').AvailableFreeSpace"]);
        var digits = String(free[0]).match(/\d+/);
        if (Number(free[1]) !== 0 || !digits) {
            console.log("edi free space unknown: " + shell + " gave " + free[1] + ": " + String(free[0]).trim());
            return NaN;
        }
        return Number(digits[0]);
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
    var folder = folderField();
    if (!label || !folder)
        return;
    var free = freeSpace(String(folder.text));
    label.text = sizeText(neededSpace()) + " needed" + (isNaN(free) ? "" : " · " + sizeText(free) + " available");
}

function setupInstallPage(page) {
    var intro = gui.findChild(page, "MessageLabel");
    if (intro) {
        intro.textFormat = 1;  // Qt.RichText
        intro.text = logo() + PARA + "EasyDiffraction calculates diffraction patterns from a structural model and "
            + "fits its parameters to experimental data.</p>" + PARA + "Install to</p>";
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
    // Our folder field and Browse stand in for the Framework's, which stay hidden and remain what the installation
    // reads and checks: ours writes it on every change, Browse is its own, and ours reads it back on entering.
    var theirs = gui.findChild(page, "TargetDirectoryLineEdit");
    var browse = gui.findChild(page, "FolderBrowseButton");
    var theirBrowse = gui.findChild(page, "BrowseDirectoryButton");
    var folder = gui.findChild(page, "FolderLineEdit");
    var ownField = folder && theirs && browse && theirBrowse;
    if (!folder)
        folder = theirs;
    if (ownField) {
        theirs.visible = false;
        theirBrowse.visible = false;
        if (String(folder.text) !== String(theirs.text))
            folder.text = theirs.text;
    }
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
        // The folder is probed (its disk, an installation in it) when its editing is done, never per keystroke,
        // and when Browse sets it (a change while the field has no focus, which ends no editing).
        if (folder) {
            folder.editingFinished.connect(refreshInstallPage);
            folder.textChanged.connect(function () {
                if (!folder.focus)
                    refreshInstallPage();
            });
        }
        if (ownField) {
            folder.textChanged.connect(function () {
                if (String(theirs.text) !== String(folder.text))
                    theirs.text = folder.text;
                // The Framework judges the folder 200 ms after a change; its refusal is shown under ours then.
                later(300, showNotice);
            });
            // The Framework's own Browse (its dialog and its rules), and the folder it chose read back.
            browse.clicked.connect(function () {
                theirBrowse.click();
                if (String(folder.text) !== String(theirs.text))
                    folder.text = theirs.text;
                // The field can keep the keyboard focus through Browse, and then refreshes nothing by itself.
                refreshInstallPage();
            });
        }
        installPageReady = true;
    }
    refreshInstallPage();
}

// What the chosen folder says: an installation already in it is updated by its maintenance tool, not installed
// twice. A licence refusal stays said until Install is pressed again.
var licenseRefused = false;

// The form's rows stand one row gap apart (the logo one step above them), measured once the page shows: each gap
// widget above a row (AssistantForm.ui) takes what the drawn frames need. A row with nothing shown has no gap.
var formRows = [["LogoRow", ["FormLogo"]], ["FolderRow", ["FolderLineEdit", "FolderBrowseButton"]],
                ["AppRow", ["AppCheckBox"]], ["AssistantRow", ["AssistantCheckBox"]],
                ["LicenseRow", ["LicenseCheckBox", "LicenseLink"]], ["ShortcutRow", ["ShortcutCheckBox"]],
                ["NoticeRow", ["NoticeLabel"]], ["SpaceRow", ["SpaceLabel"]]];

// As soon as the page is laid out, so nobody sees it move, and once more when the styles have reached every widget.
function settleSoon(page) {
    later(0, function () { settleForm(page); });
    later(150, function () { settleForm(page); });
}

function settleForm(page) {
    // Only a page on screen has frames to measure.
    if (!page || !page.visible)
        return;
    var previous = null;
    formRows.forEach(function (row) {
        var shown = row[1].map(function (name) { return gui.findChild(page, name); })
            .filter(function (widget) { return widget && widget.visible; });
        var gap = gui.findChild(page, row[0] + "Gap");
        if (gap)
            gap.visible = shown.length > 0 && previous !== null;
        if (shown.length > 0)
            previous = row[0];
    });
    // The licence and its link: one row gap between the box's frame and the link.
    var license = gui.findChild(page, "LicenseCheckBox");
    var link = gui.findChild(page, "LicenseLink");
    var licenseRow = gui.findChild(page, "LicenseRow");
    later(0, function () {
        if (license && link && licenseRow && license.visible && link.visible)
            adjustOnce(licenseRow, link.x - (license.x + license.width));
        var above = null;
        formRows.forEach(function (row) {
            var shown = row[1].map(function (name) { return gui.findChild(page, name); })
                .filter(function (widget) { return widget && widget.visible; });
            if (shown.length === 0)
                return;
            var top = Math.min.apply(null, shown.map(function (widget) { return widget.y; }));
            var bottom = Math.max.apply(null, shown.map(function (widget) { return widget.y + widget.height; }));
            var gap = gui.findChild(page, row[0] + "Gap");
            if (above && gap) {
                var wanted = above.name === "LogoRow" ? 2 * rowGap : rowGap;
                // What lies between the rows besides the gap widget, all read from the page as it is laid out. Taking
                // the difference from the height last set instead would correct twice when asked again before the
                // page is laid out anew.
                var besides = (gap.y - above.bottom) + (top - (gap.y + gap.height));
                var height = bounded(wanted - besides, wanted);
                gap.minimumHeight = height;
                gap.maximumHeight = height;
            }
            above = {name: row[0], bottom: bottom};
        });
        // On the installer's page the form's first row (our folder) stands one row gap under the page's text: the
        // page's spacing, that page's only gap, takes up where the row's frame sits.
        var install = gui.pageWidgetByObjectName("TargetDirectoryPage");
        var form = install ? gui.findChild(install, "AssistantForm") : null;
        var text = install ? gui.findChild(install, "MessageLabel") : null;
        var field = gui.findChild(page, "FolderLineEdit");
        var column = install ? firstLayout(install) : null;
        if (form && text && field && field.visible && column && page.objectName === "TargetDirectoryPage")
            column.spacing = bounded(rowGap - field.y, 2 * rowGap);
        if (captureFolder !== "")
            later(100, function () { logLayout(page, "settled"); });
    });
}

// The removal's progress, in the Framework's own label: the logo, one line and the bar with its percentage, as the other
// progress page has them. The Framework's bar comes before its label and cannot be put after it, so the bar is drawn in
// the text and the real one hidden. The Framework writes the label for every step; ours is put back on each sign of
// that, so its words can show for a moment.
var removalHooked = false;

function showRemoval(page, bar, label) {
    function put() {
        var share = bar.maximum > bar.minimum
            ? Math.max(0, Math.min(100, Math.round(100 * (bar.value - bar.minimum) / (bar.maximum - bar.minimum)))) : 0;
        var cell = function (width, colour) {
            // A cell is as high as its text (Qt takes no height for it): this size gives the 8 px of the other bar.
            return width > 0 ? '<td width="' + width + '%" bgcolor="' + colour
                + '" style="font-size: 6px">&nbsp;</td>' : "";
        };
        var text = logo() + PARA + "Removing EasyDiffraction… " + share + "%</p>"
            + '<table width="100%" cellspacing="0" cellpadding="0" style="margin-top: 8px"><tr>'
            // The track: the accent at 17 % on the window (ACCENT_TRACK), as a plain colour.
            + cell(share, accent()) + cell(100 - share, darkTheme() ? "#2e424a" : "#c4e0ea") + "</tr></table>";
        if (String(label.text) !== text)
            label.text = text;
    }
    bar.visible = false;
    label.textFormat = 1;  // Qt.RichText
    label.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
    label.wordWrap = true;
    label.visible = true;
    put();
    if (removalHooked)
        return;
    removalHooked = true;
    bar.valueChanged.connect(put);
    var details = gui.findChild(page, "DetailsBrowser");
    if (details)
        details.textChanged.connect(function () { put(); Qt.callLater(put); });
    installer.uninstallationFinished.connect(function () { put(); later(100, put); });
}

// The done page's box one row gap under its sentence: on macOS a box's frame sits below where its row starts, so the
// page's spacing (that page's only gap) takes up the difference once shown.
function settleDone(page) {
    var text = gui.findChild(page, "MessageLabel");
    var form = gui.findChild(page, "DoneForm");
    var open = gui.findChild(page, "OpenCheckBox");
    var column = firstLayout(page);
    if (!page.visible || !text || !form || !open || !open.visible || !column)
        return;
    column.spacing = bounded(rowGap - open.y, 2 * rowGap);
    if (captureFolder !== "")
        later(100, function () { logLayout(page, "settled"); });
}

// The notice line: the licence refusal, the Framework's refusal of the folder (its warning line, which decides
// whether Install is allowed) and an installation already there. Composed whole each time, so nothing stale stays.
var installedHere = false;

function showNotice() {
    var notice = installPageField("NoticeLabel");
    if (!notice)
        return;
    var refusal = installPageField("WarningLabel");
    var lines = [];
    if (licenseRefused)
        lines.push("Accept the license to install EasyDiffraction.");
    if (refusal && String(refusal.text) !== "")
        lines.push(String(refusal.text));
    if (installedHere)
        lines.push("EasyDiffraction is already installed here. To update it, open its Maintenance Tool and choose "
            + "Update.");
    notice.text = lines.join(" ");
    notice.visible = notice.text !== "";
    settleSoon(gui.pageWidgetByObjectName("TargetDirectoryPage"));
}

// Our folder field, or the Framework's where our form is missing.
function folderField() {
    return installPageField("FolderLineEdit") || installPageField("TargetDirectoryLineEdit");
}

function refreshInstallPage() {
    var folder = folderField();
    var target = folder ? String(folder.text) : installer.value("TargetDir");
    var tool = target + (systemInfo.kernelType === "darwin" ? "/MaintenanceTool.app"
                         : systemInfo.kernelType === "winnt" ? "/MaintenanceTool.exe" : "/MaintenanceTool");
    installedHere = target !== "" && installer.fileExists(tool);
    showNotice();
    updateSpace();
}



var wordmark = "";

// No title and no subtitle, so Qt draws no header. The Framework sets some again as a page opens (the maintenance
// tool's first page, an inserted page), so they are cleared again once the page says it was entered.
var untitledPages = [];
// A script's one timer: the progress page's details button, clicked while another page shows (that page resets it
// as it opens), runs `then` after `delay` ms.
// Each click runs the waiting call that is due first.
var laterCalls = [];
// Set while the progress page closes its own details, a click that is not a timer's.
var closingDetails = false;
var laterHooked = false;
function later(delay, then) {
    var perform = gui.pageWidgetByObjectName("PerformInstallationPage");
    var details = perform ? gui.findChild(perform, "DetailsButton") : null;
    if (!details)
        return;
    if (!laterHooked) {
        details.clicked.connect(function () {
            if (closingDetails)
                return;
            // On the progress page itself the click opened its details: closed again, and the images area that
            // closing shows hidden again.
            if (perform.visible) {
                closingDetails = true;
                details.click();
                closingDetails = false;
                var images = gui.findChild(perform, "ProductImagesScrollArea");
                if (images)
                    images.visible = false;
            }
            laterCalls.sort(function (a, b) { return a.due - b.due; });
            var call = laterCalls.shift();
            if (call)
                call.then();
        });
        laterHooked = true;
    }
    laterCalls.push({due: Date.now() + delay, then: then});
    gui.clickButton("DetailsButton", delay);
}

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
    }
}

// The logo heading each page's own content (the pages have no titles, so Qt shows no header).
// A paragraph of a page's text: one row gap above it and none below, so the label ends where its last line does
// (Qt's own paragraph margins would leave space the frame counts but nobody sees as a gap). Under the logo the logo's
// step wins: Qt takes the larger of two touching margins.
var PARA = '<p style="margin: 8px 0 0 0">';

// The logo heading a page's text, one step (16) above what follows it (templatePage).
function logo() {
    return '<p style="margin-bottom: 16px">' + headerWordmark() + "</p>";
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
        // No title, so no header: the logo heads the page's own content. Cleared first, as some pages leave early.
        keepUntitled(page);
        // The first page is shown after its callback, and showing the window gives every page without a subtitle a
        // one-space one (a header band): cleared again once the window is up.
        if (name === "Introduction") {
            try {
                later(0, function () { keepUntitled(page); });
            } catch (error) {
                console.log("edi first page header kept: " + error);
            }
        }

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
                ask.text = logo() + PARA + "What would you like to do?</p>";
            }
            orderChoices(page);
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
            // A captured walk stays a moment, so the accessibility client reads this page too.
            notePage(name);
            if (!licenseRefused && captureFolder !== "") {
                proceed(name, buttons.CommitButton, 1500);
            } else if (!licenseRefused) {
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
            if (captureFolder === "")
                gui.clickButton(buttons.NextButton, 50);
            else if (installerWalked)
                gui.clickButton(buttons.NextButton, 50);
            else {
                notePage(name);
                proceed(name, buttons.NextButton, 3000);
            }
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
            // The Framework's warning line stays hidden: what it says shows in our notice line (showNotice).
            var warning = gui.findChild(page, "WarningLabel");
            if (warning)
                warning.visible = !gui.findChild(page, "FolderLineEdit") && warning.text !== "";
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
            var closeDetails = function () {
                if (detailsBrowser && detailsBrowser.visible && detailsButton) {
                    closingDetails = true;
                    detailsButton.click();
                    closingDetails = false;
                }
            };
            closeDetails();
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
            // Removing loads no component, so there is no form of ours to show.
            if (bar && label && !ours)
                showRemoval(page, bar, label);
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
            // On Linux the desktop shortcut is made only where the home folder has a Desktop (installscript.qs).
            if (systemInfo.kernelType === "linux" && !installer.fileExists(installer.value("HomeDir") + "/Desktop"))
                shortcut = false;
            // macOS adds nothing outside the chosen folder, so a folder elsewhere is said to be that folder.
            // Captures install into a throwaway folder but show what the default installation says.
            var applications = captureFolder !== ""
                || /^(\/Applications|.*\/Users\/[^\/]+\/Applications)(\/|$)/.test(target);
            var where = systemInfo.kernelType === "winnt" ? (shortcut ? "in the Start menu and on your desktop"
                                                                      : "in the Start menu")
                : systemInfo.kernelType === "darwin" ? (applications ? "in your Applications folder" : "in the folder you chose")
                    : (shortcut ? "in your applications menu and on your desktop" : "in your applications menu");
            if (done && installer.isInstaller() && installer.status === QInstaller.Success) {
                // A check mark in the app's success green, a character of the text so it has the text's height.
                done.textFormat = 1;  // Qt.RichText
                done.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
                done.text = logo() + PARA + checkMark() + " EasyDiffraction is installed. You'll find it " + where
                    + ".</p>";
            }
            // The maintenance tool says what it did the same way, in one line; a failure keeps the Framework's words.
            if (done && !installer.isInstaller() && String(done.text).indexOf("<img") < 0) {
                done.textFormat = 1;  // Qt.RichText
                done.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop
                var said = installer.isUninstaller() ? "EasyDiffraction is removed."
                    : installer.isUpdater() ? "EasyDiffraction is updated." : "Your changes are made.";
                done.text = logo() + PARA + (installer.status === QInstaller.Success ? checkMark() + " " + said
                    : done.text) + "</p>";
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
            // Our own box in a row of its own (DoneForm.ui) stands in for the Framework's, which stays hidden and
            // follows it; shown only where the Framework would show its box.
            var open = gui.findChild(page, "OpenCheckBox");
            later(0, function () { settleDone(page); });
            later(150, function () { settleDone(page); });
            if (run && open) {
                open.visible = run.visible;
                open.checked = run.checked;
                run.visible = false;
                if (!openHooked) {
                    open.toggled.connect(function (on) { run.checked = on; });
                    openHooked = true;
                }
            }
            if (captureFolder !== "")
                installer.setValue("RunProgram", "");
        }

        // No title, so no header: the logo heads the page's own content.
        keepUntitled(page);
        capture(name);
        advance(name, page);
    };
});
