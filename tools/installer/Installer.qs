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

// macOS: the maintenance tool an update replaced is kept (maintenance_swap.sh) until the update has succeeded with the
// new tool in place; then it goes. The Framework signals the end of an update, a successful one or one rolled back,
// as installationFinished, so the status and the tool are checked first: after a rollback the kept tool was put
// back by the swap's undo and nothing is removed.
function dropOldTool() {
    if (systemInfo.kernelType !== "darwin" || !installer.isUpdater() || installer.status !== QInstaller.Success)
        return;
    var target = installer.value("TargetDir");
    if (target === "" || !installer.fileExists(target + "/MaintenanceTool.app/Contents/MacOS/MaintenanceTool"))
        return;
    installer.execute("/bin/rm", ["-rf", target + "/MaintenanceTool.app.old"]);
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
// Updating comes in two: update (everything installed) and updatewithout (the assistant not installed); their pages
// are named after them.
var maintenanceMode = installer.environmentVariable("EDI_INSTALLER_MAINTENANCE_MODE") || "remove";
var maintenanceAction = maintenanceMode.indexOf("update") === 0 ? "update" : maintenanceMode;

// The installer's other captured states (EDI_INSTALLER_CAPTURE_STATE), each a walk of its own that stops on its
// state: installed (run again over an installation, Install pressed, the page stays), quit (Cancel pressed) and
// locked (started while another installer holds the lock). capture_pages.py ends those walks once their picture is
// taken.
var captureState = installer.environmentVariable("EDI_INSTALLER_CAPTURE_STATE");

function pageId(name) {
    var mode = installer.isInstaller() ? "installer" + (captureState ? "-" + captureState : "")
        : "maintenance-" + maintenanceMode;
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
    if (systemInfo.kernelType === "winnt" && name === "Introduction" && !installer.isInstaller()) {
        waitForPicture(name, button, delay, 0);
        return;
    }
    // macOS and Linux: the page stays until its settled picture is written (or found unsettled), so a later page is
    // never grabbed under its name. The progress page is kept as grabbed and needs no wait.
    if (grabbing[pageId(name)] && systemInfo.kernelType !== "winnt" && name !== "PerformInstallation") {
        waitForGrab(name, button, delay, 0);
        return;
    }
    gui.clickButton(button, delay);
}

// The pages a grab was started for (capture), by picture name: only those wait for their picture.
var grabbing = {};

// A grab that writes nothing within 10 s fails the walk rather than moving on, which could leave the next page's frames
// to be saved under this page's name: a .timeout marker names the page and the installer quits.
function waitForGrab(name, button, delay, tries) {
    var stem = captureFolder + "/" + pageId(name);
    if (installer.fileExists(stem + ".png") || installer.fileExists(stem + ".unsettled.png")) {
        delete grabbing[pageId(name)];
        gui.clickButton(button, delay);
        return;
    }
    if (tries >= 40) {
        installer.execute("/bin/sh", ["-c", 'echo "no settled picture within 10 s" > "$1"', "sh", stem + ".timeout"]);
        gui.rejectWithoutPrompt();
        return;
    }
    later(250, function () { waitForGrab(name, button, delay, tries + 1); });
}

// Windows: capture_pages.py takes the pictures, and Next on the maintenance tool's first page starts loading, which
// greys the choices and shows a progress bar. So Next waits until the picture of the page is there, and a marker
// file tells capture_pages.py to keep no later frame of it.
function waitForPicture(name, button, delay, tries) {
    var picture = captureFolder + "/" + pageId(name) + ".png";
    if (!installer.fileExists(picture) && tries < 40) {
        later(500, function () { waitForPicture(name, button, delay, tries + 1); });
        return;
    }
    installer.execute("cmd.exe", ["/c", "echo loading>" + captureFolder.replace(/\//g, "\\") + "\\" + pageId(name)
        + ".loading"]);
    gui.clickButton(button, delay);
}

// Taken a moment later by a detached process, once the page has painted.
function capture(name) {
    if (captureFolder === "")
        return;
    notePage(name);
    // The progress page is gone within a second for the small marker installer; the first page needs the window up.
    // A hovered button waits for the pointer capture_pages.py moves onto it; the install page waits for its rows to be
    // spaced, which takes up to a second and a half on a software-drawn display.
    var delay = name === "PerformInstallation" ? "0.2"
        : name === "Introduction" || name === "CancelHover" || name === "TargetDirectory" ? "2" : "1";
    var file = captureFolder + "/" + pageId(name) + ".png";
    if (systemInfo.kernelType !== "winnt")
        grabbing[pageId(name)] = true;
    if (systemInfo.kernelType === "winnt") {
        // A process started here cannot take a screenshot; capture_pages.py takes them on Windows.
    } else if (systemInfo.kernelType === "darwin") {
        // This process's front window (the page, or a pop-up over it), without its shadow; the whole screen if none.
        var grab = 'id=$(/usr/bin/osascript -l JavaScript -e "$js");'
            + ' if [ -n "$id" ]; then /usr/sbin/screencapture -x -o -l"$id" "$out";'
            + ' else /usr/sbin/screencapture -x "$out"; fi';
        // Pixels alone (a BMP copy, no timestamps) say whether two grabs are the same.
        var same = '/usr/bin/sips -s format bmp "$a" --out "$a.bmp" >/dev/null 2>&1 &&'
            + ' /usr/bin/sips -s format bmp "$b" --out "$b.bmp" >/dev/null 2>&1 && cmp -s "$a.bmp" "$b.bmp"';
        installer.executeDetached("/bin/sh", ["-c", settledGrab(grab, same, delay, name), "sh",
                                              frontWindowScript(), file]);
    } else {
        // The screen around the window is black: trimmed away, leaving the window (and a pop-up over it).
        var root = 'import -window root -trim +repage "$out"';
        var equal = 'test "$(compare -metric AE "$a" "$b" null: 2>&1)" = 0';
        installer.executeDetached("/bin/sh", ["-c", settledGrab(root, equal, delay, name), "sh", "", file]);
    }
}

// A picture is kept only once the page holds still: two grabs 150 ms apart with the same pixels. A page still moving
// after three seconds is saved as <name>.unsettled.png, which the walk's check reports as a missing page, so a frame
// between two layouts is never shown as the page. The progress page moves by design and is kept as grabbed.
// `grab` writes "$out" ("$js" is the script's first argument); `same` compares "$a" and "$b". The file is "$2".
function settledGrab(grab, same, delay, name) {
    var head = 'js="$1"; f="$2"; shot() { out="$1"; ' + grab + '; }; sleep ' + delay + "; ";
    if (name === "PerformInstallation")
        return head + 'shot "$f"';
    return head + 't="${f%.png}"; a="$t.a.png"; b="$t.b.png"; shot "$a"; i=0;'
        + ' while :; do sleep 0.15; shot "$b";'
        + ' if ' + same + '; then mv "$b" "$f"; rm -f "$a" "$a.bmp" "$b.bmp"; exit 0; fi;'
        + ' mv "$b" "$a"; i=$((i+1));'
        + ' if [ $i -ge 20 ]; then mv "$a" "$t.unsettled.png"; rm -f "$a.bmp" "$b.bmp"; exit 1; fi; done';
}

// macOS: the window number of this process's front window, for screencapture -l. The front-most window of a process
// is listed first; layer 0 leaves out its menu bar.
var ownPid = "";

function frontWindowScript() {
    if (ownPid === "")
        ownPid = String(installer.execute("/bin/sh", ["-c", "echo $PPID"])[0]).trim();
    return "ObjC.import('CoreGraphics');"
        + " var w = ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(1, 0))).filter(function (x) {"
        + " return x.kCGWindowOwnerPID == " + ownPid + " && x.kCGWindowLayer == 0; });"
        + " w.length ? String(w[0].kCGWindowNumber) : ''";
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
    // The pop-ups: noted and grabbed as they open, then left open. Install over an installation opens none: its
    // picture shows the page staying.
    var popup = {installed: ["InstallPressed", buttons.NextButton], quit: ["Quit", buttons.CancelButton]}[captureState];
    if (name === "TargetDirectory" && popup) {
        // Where the capture can move the pointer (EDI_INSTALLER_CAPTURE_HOVER), Cancel is first shown hovered: the
        // page is noted, capture_pages.py puts the pointer on Cancel, and the picture follows.
        var hover = captureState === "quit" && installer.environmentVariable("EDI_INSTALLER_CAPTURE_HOVER") !== "";
        if (hover)
            later(1500, function () { capture("CancelHover"); });
        later(hover ? 4000 : 2500, function () {
            capture(popup[0]);
            gui.clickButton(popup[1], 100);
        });
        return;
    }
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

// One window height on every page: the height of the first page shown, held, so a page without a button row (macOS
// hides Cancel while installing) or with a status line does not grow the window.
var windowHeight = 0;

function fixWindowHeight() {
    if (windowHeight === 0) {
        if (!(gui.height > 0))
            return;
        windowHeight = gui.height;
    }
    gui.minimumHeight = windowHeight;
    gui.maximumHeight = windowHeight;
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
    // Install over an installation already in the folder is refused by the Framework with a pop-up of its own. The
    // page already says so above "Install to" (INSTALLED_HERE), so the refusal is answered silently and Install leaves
    // the page as it is. A script cannot disable the button there: tried with an emptied folder field, the page's
    // completeness and the Framework's refusal line, the Framework keeps Install enabled.
    installer.setMessageBoxAutomaticAnswer("TargetDirectoryInUse", QMessageBox.Ok);
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
    installer.installationFinished.connect(dropOldTool);
    // When the work is done the Framework moves on to the last page by itself; should it stay on the progress page,
    // Next is pressed for it, so the tool always ends by saying what it did.
    if (captureFolder === "") {
        var finished = function () {
            var perform = gui.pageWidgetByObjectName("PerformInstallationPage");
            if (perform && perform.visible)
                gui.clickButton(buttons.NextButton, 0);
        };
        [installer.installationFinished, installer.updateFinished, installer.uninstallationFinished].forEach(
            function (done) { done.connect(function () { later(1500, finished); }); });
    }
    // Finish opens the program when its box is ticked: the installer's Finish button, and the maintenance tool's,
    // which is its relabelled Cancel button and so ends it as cancelled once the work is done.
    if (installer.finishButtonClicked)
        installer.finishButtonClicked.connect(openProgram);
    installer.statusChanged.connect(function (status) {
        if (status === QInstaller.Canceled)
            openProgram();
    });
}

// "Open EasyDiffraction now" (DoneForm.ui), offered on a successful last page. The program is started from here, not
// through the Framework's RunProgram: that ran from its own hidden box and did not open the app on macOS (edi
// #188). Asked only once the last page was shown, and once. The window is closing by then, so the box's own
// visibility says nothing; whether it was offered is kept.
var openOffered = false;
var openStarted = false;

function openProgram() {
    if (!openOffered || openStarted || captureFolder !== "")
        return;
    var page = gui.pageWidgetByObjectName("FinishedPage");
    var open = page ? gui.findChild(page, "OpenCheckBox") : null;
    if (!open || !open.checked)
        return;
    openStarted = true;
    var target = String(installer.value("TargetDir"));
    if (systemInfo.kernelType === "darwin")
        installer.executeDetached("/usr/bin/open", [target + "/EasyDiffraction.app"]);
    else if (systemInfo.kernelType === "winnt")
        installer.executeDetached(target + "/bin/EasyDiffraction.exe", [], target);
    else
        installer.executeDetached(target + "/bin/EasyDiffraction", [], target);
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

// The one layout every page follows: the logo first, 32 under it (logo()), then the heading, then the
// rows, each 8 under the one above and all on one left edge. The Framework's own layouts have no names (ours all
// have one), so a script finds them as the page's unnamed children; each that has a spacing gets the row gap.
var rowGap = 8;
// Between the groups of a page (what it is, where it goes, the choices, the notes under them) three row gaps, as
// between the sections of a book: a group's rows read together.
var groupGap = 3 * rowGap;
// The logo, and the space under it: four row gaps, twice the gap between groups, so the logo stands apart from the
// page it heads.
var logoHeight = 44;
var logoStep = 4 * rowGap;
// The page's content stands this far in from the logo's left edge, and as far from the right: the logo starts with a
// circle (radius 22), whose edge reads as standing where its outline is at 45 degrees, 22 * (1 - cos 45) = 6.4 px in
// from its leftmost point. Text and rows lined up with the leftmost point looked shifted left of the circle. The
// widgets take it as a stylesheet margin (Installer.qss), the text as a paragraph margin.
var sideIndent = 6;
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
var ownLayout = /^(AssistantLayout|DoneLayout|ProgressColumn|[A-Za-z]*Row)$/;

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
        choices.update.text = "Update";
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

// Next on the maintenance tool's first page asks the repository first (the choices are disabled meanwhile). When that
// finds nothing to do or fails, the Framework stays on the page and writes why in a label of its own, which showed
// nothing here: the tool looked as if it had done nothing. The choices are watched while the page shows; once they
// are enabled again on the same page, its reason is said above the question.
var choicesWatched = false;

function watchChoices(page) {
    if (choicesWatched)
        return;
    choicesWatched = true;
    var busy = false;
    function look() {
        if (!page.visible) {
            choicesWatched = false;
            return;
        }
        var remove = maintenanceChoices(page).remove;
        if (remove && !remove.enabled) {
            busy = true;
            sayWhyStayed(page, "");
        } else if (busy) {
            busy = false;
            sayWhyStayed(page, stayReason(page));
        }
        later(250, look);
    }
    later(250, look);
}

// The Framework's words for staying (its error label, or any other text it wrote on the page), in plain text; empty
// when it wrote none. `raw` gives them as they are and clears them, so the next failure is told apart from this one.
function stayReason(page, raw) {
    function plain(label) { return String(label.text).replace(/<[^>]*>/g, "").trim(); }
    var labels = gui.findChildren(page, null).filter(function (item) {
        return item && typeof item.text === "string" && typeof item.wordWrap === "boolean"
            && item.objectName !== "MessageLabel" && plain(item) !== "";
    });
    // The error label by name; else a text that reads as a failure (not the "Retrieving information" line).
    var source = labels.filter(function (label) { return label.objectName === "ErrorLabel"; })[0]
        || labels.filter(function (label) {
            var failure = /cannot|could not|error|fail|lock|no updates|unavailable|repositor(y|ies) required/i;
            return failure.test(plain(label)) && !/^Retrieving/.test(plain(label));
        })[0];
    var words = source ? plain(source) : "";
    if (source) {
        source.visible = false;  // said in our own words instead
        if (raw)
            source.text = "";
    }
    if (raw)
        return words;
    if (/no updates available/i.test(words))
        return "EasyDiffraction is up to date: there is no update to install.";
    if (/lock/i.test(words))
        return "Another EasyDiffraction installer seems to be running. Close it, then open this installer again.";
    return words !== "" ? words : "Nothing was changed. Check your internet connection, then open this installer again.";
}

// The app's warning sign (exclamation-triangle in its orange, render_images.qml), before a line that says something
// is wrong or needs attention: never before neutral information or a question (owner point 35).
// Its picture carries the 4 px a button leaves between its icon and its text, so the gap is the same everywhere.
function warningSign() {
    return '<img style="vertical-align: middle" src=":/metadata/edi/'
        + (darkTheme() ? "warning-line-dark" : "warning-line") + '.png" width="20" height="16">';
}

// The reason between the logo and the question, after the warning sign unless all is well; empty clears it.
function sayWhyStayed(page, reason) {
    var ask = gui.findChild(page, "MessageLabel");
    if (!ask)
        return;
    var question = "What would you like to do?</p>";
    var text = logo() + PARA + question;
    if (reason !== "") {
        // In the text's colour: the warning sign alone marks a problem (owner point 36).
        text = logo() + PARA + (/up to date/.test(reason) ? "" : warningSign()) + reason + "</p>" + GROUP + question;
    }
    if (String(ask.text) !== text)
        ask.text = text;
}

// The installer's first page passes by itself, unless asking the repository fails there: most often because another
// installer holds the download cache's lock. The Framework then stays on that page with its own long message (a
// lock file's path) under a bare welcome, and leaves Next disabled for good: a script cannot enable it (the page's
// completion has no script property) and the fetch is not asked again. So the page says what to do in the design of
// the other pages and offers only Quit; the user opens the installer again once the other one is closed.
var welcomeWatched = false;
var stuckText = "";
var LOCKED = "Another EasyDiffraction installer seems to be running. Close it, then open this installer again.";

function watchWelcome(page) {
    if (welcomeWatched)
        return;
    welcomeWatched = true;
    function look() {
        if (!page.visible) {
            welcomeWatched = false;
            gui.setWizardPageButtonText(QInstaller.Introduction, buttons.CancelButton, "Cancel");
            return;
        }
        var reason = stayReason(page, true);
        if (reason !== "")
            stuckText = /lock/i.test(reason) ? LOCKED : reason + " Quit, then open this installer again.";
        // Once stuck it stays so: pressing Next makes the Framework write its welcome and its raw message again.
        if (stuckText !== "")
            sayStuck(page, stuckText);
        later(250, look);
    }
    later(250, look);
}

var lockedCaptured = false;

function sayStuck(page, text) {
    if (captureState === "locked" && !lockedCaptured) {
        lockedCaptured = true;
        later(0, function () { capture("Introduction"); });
    }
    var message = gui.findChild(page, "MessageLabel");
    var said = message ? logo() + PARA + warningSign() + text + "</p>" : "";
    if (message && String(message.text) === said)
        return;
    if (message) {
        message.textFormat = 1;  // Qt.RichText
        message.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
        message.wordWrap = true;
        message.text = said;
    }
    gui.setWizardPageButtonText(QInstaller.Introduction, buttons.CancelButton, "Quit");
}

// The assistant's own page in the maintenance tool (assistantscript.qs).
Controller.prototype.DynamicAssistantFormCallback = function () {
    var page = gui.pageWidgetByObjectName("DynamicAssistantForm");
    themePage(page);
    // That is our form; the page around it, whose layout the Framework made without margins, takes the template.
    templatePage(gui.pageByObjectName("DynamicAssistantForm"));
    page.title = "";
    page.subTitle = "";
    // The logo and the page's heading, as the summary after it: what the choice is for.
    var mark = gui.findChild(page, "FormLogo");
    if (mark) {
        mark.textFormat = 1;  // Qt.RichText
        mark.text = logo() + '<p style="margin: 0 ' + sideIndent + 'px">Change components</p>';
        gui.findChild(page, "LogoBox").visible = true;
    }
    choiceSizes(page);
    var box = gui.findChild(page, "AssistantCheckBox");
    if (box && !choiceHooked) {
        box.toggled.connect(function () { choiceSpace(page); });
        choiceHooked = true;
    }
    choiceSpace(page);
    settleSoon(page);
    capture("AssistantForm");
    // Adding components in capture mode turns the assistant over (added if absent, removed if there), so the mode
    // always has work to do and its progress page shows. Done once the picture is taken, so it shows the page as it
    // opens.
    if (captureFolder !== "" && box && maintenanceMode === "add")
        later(1600, function () { box.checked = !box.checked; });
    advance("AssistantForm", page);
};

var choiceHooked = false;

// The choice page's space line, as the install page's: what adding the assistant needs (and what the disk has), or
// what removing it frees.
function choiceSpace(page) {
    var label = gui.findChild(page, "SpaceLabel");
    var row = gui.findChild(page, "SpaceBox");
    var box = gui.findChild(page, "AssistantCheckBox");
    if (!label || !row || !box)
        return;
    var sizes = choiceSizes(page);
    var all = installer.components();
    var installed = false;
    for (var i = 0; i < all.length; ++i) {
        if (all[i].name === assistantComponent)
            installed = all[i].installed;
    }
    var free = freeSpace(String(installer.value("TargetDir")));
    var available = isNaN(free) ? "" : " · " + sizeText(free) + " available";
    var text = "";
    if (box.checked && !installed)
        text = sizeText(sizes.assistant) + " needed" + available;
    else if (!box.checked && installed)
        text = sizeText(sizes.assistant) + " freed";
    label.text = text;
    row.visible = text !== "";
    settleSoon(page);
}

// The assistant checkbox on the folder page decides the component, applied when that page is left and again before
// the summary counts what is installed: a selection made while the component scripts load does not last.
var assistantComponent = "org.easydiffraction.app.assistant";
var appComponent = "org.easydiffraction.app";
// The maintenance tool is a hidden (virtual) component, installed and updated with the rest. The pages show it as a
// row of its own, ticked and fixed as EasyDiffraction, between it and the AI assistant (owner, 2026-11-26).
var maintenanceComponent = "org.easydiffraction.app.maintenancetool";
// The tool's size: on Linux its component has no payload (the Framework writes the tool from its own binary), so
// package.py gives the size of that binary.
var toolBytes = Number("@TOOL_BYTES@") || 0;

function componentBytes(c) {
    return Number(c.value("UncompressedSize") || 0) || (c.name === maintenanceComponent ? toolBytes : 0);
}

// Whether a summary counts the component: what is installed, updated or removed. The maintenance tool's component
// carries the app version (ADR-0091), so an update takes it whenever it changes anything else; the Framework does not
// mark a virtual component for it, so that is decided here.
function requested(c, removing) {
    if (removing)
        return c.uninstallationRequested();
    // On update the tool follows its own state: with checksum updates it can be unchanged while the app changes, or be
    // the only change.
    if (c.name === maintenanceComponent && installer.isUpdater())
        return c.installationRequested() || c.updateRequested();
    return c.installationRequested();
}

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
// not name (the maintenance tool itself): EasyDiffraction's row carries them, so the rows add up to the space line.
// `boxed` shows each name as the choice page shows it: a ticked check box that cannot be changed here (drawn disabled),
// its name in the normal text colour, the box at the heading's edge and the rows one row gap apart. The box is 16 px,
// the check box's outside at the 14 px text (Installer.qss). `first` is the gap above the first row, where it follows
// the space line.
function summaryRows(removing, total, boxed, first, unticked) {
    var entries = summaryEntries(removing);
    var named = 0;
    entries.forEach(function (entry) { named += entry.bytes; });
    var rows = "";
    entries.forEach(function (entry) {
        var gap = rows === "" && first ? first : boxed ? rowGap : 2;
        var name = boxed
            ? '<td width="' + (16 + sideIndent) + '" style="padding: ' + gap + 'px 0 0 ' + sideIndent
              + 'px"><img style="vertical-align: middle" src='
              + '":/metadata/edi/' + (unticked ? "unchecked-disabled" : "checked-disabled") + (darkTheme() ? "-dark" : "")
              + '.png" width="16" height="16"></td>'
              + '<td valign="middle" style="padding: ' + gap + 'px 0 0 7px">' + entry.name + "</td>"
            : '<td style="padding: ' + gap + 'px 0 2px ' + (4 + sideIndent) + 'px">' + entry.name + "</td>";
        rows += "<tr>" + name + '<td align="right"' + (boxed ? ' valign="middle"' : "") + ' style="padding: '
            + gap + "px " + sideIndent + 'px 0 0">' + sizeText(entry.bytes
                       + (entry.app && total ? Math.max(0, total - named) : 0)) + "</td></tr>";
    });
    return rows;
}

// What a summary lists, in the pages' order: EasyDiffraction, the maintenance tool, the AI assistant. The Framework
// leaves its virtual components out of the list a script reads, so the tool is added here whenever EasyDiffraction is
// installed or updated (it is installed with it and taken by every update, ADR-0091).
function summaryEntries(removing) {
    var entries = [];
    var tool = false;
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var c = all[i];
        if (!listed(c) || !requested(c, removing))
            continue;
        tool = tool || c.name === maintenanceComponent;
        entries.push({name: displayName(c), bytes: componentBytes(c), app: c.name === appComponent,
                      order: c.name === appComponent ? 0 : c.name === maintenanceComponent ? 1 : 2});
    }
    var app = entries.some(function (entry) { return entry.app; });
    if (!removing && !tool && installer.isUpdater()) {
        // The Framework may leave the virtual tool out of components(); asked by name, it says whether it changes.
        var held = installer.componentByName(maintenanceComponent);
        if (held && requested(held, false))
            entries.push({name: "Maintenance Tool", bytes: componentBytes(held) || toolBytes, app: false, order: 1});
    } else if (!removing && app && !tool && installer.isInstaller()) {
        // A fresh installation makes its own tool, which no package holds: its size is the Framework's.
        entries.push({name: "Maintenance Tool", bytes: toolBytes, app: false, order: 1});
    }
    entries.sort(function (a, b) { return a.order - b.order; });
    return entries;
}

// A component the summary lists: every one users see, and the maintenance tool.
function listed(c) {
    return c.value("Virtual") !== "true" || c.name === maintenanceComponent;
}

function displayName(c) {
    return c.name === maintenanceComponent ? "Maintenance Tool" : c.value("DisplayName");
}

// The bytes the components to be installed (or removed) take.
function summaryBytes(removing) {
    var bytes = 0;
    summaryEntries(removing).forEach(function (entry) { bytes += entry.bytes; });
    return bytes;
}

// A list under its heading, its items 4 px in from the heading's edge (each name's cell padding), or with their boxes
// at that edge (summaryRows).
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
    // The heading in the text's weight, as every page's first line.
    var text = logo() + PARA + heading + "</p>";
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
    // The space line right under the heading, as under the install page's folder; the lists one group gap below it.
    // Adding or removing components says what the change needs or frees, and nothing when it changes no files.
    var spaceLine = "";
    if (installer.isPackageManager()) {
        var added = summaryBytes(false);
        var freed = summaryBytes(true);
        if (added > 0)
            spaceLine = sizeText(added) + " needed";
        else if (freed > 0)
            spaceLine = sizeText(freed) + " freed";
        if (space)
            space.visible = false;
    } else if (space && !removing) {
        // A change that needs no space (a figure of 0) says nothing about space.
        if (needed !== "" && parseFloat(needed) > 0)
            spaceLine = (neededBytes > 0 ? sizeText(neededBytes) : needed) + " needed · " + available + " available";
        space.visible = warned;  // a shortage stays said as the Framework says it
    }
    if (spaceLine !== "")
        text += PARA + spaceLine + "</p>";
    var first = spaceLine !== "" ? groupGap : 0;
    // Updating lists what is updated as the choice page before it showed it: ticked boxes.
    // A change of components lists every changed one as Ready to update does: ticked what is added, unticked what is
    // removed, in one list.
    var changing = installer.isPackageManager();
    var adding = summaryRows(false, neededBytes, installer.isUpdater() || changing, first);
    var dropping = removing ? summaryRows(true, 0, false, first)
        : (changing ? summaryRows(true, 0, true, adding === "" ? first : 0, true) : "");
    if (changing && adding + dropping !== "")
        text += summaryTable(adding + dropping);
    else {
        if (adding !== "")
            text += summaryTable(adding);
        if (dropping !== "")
            text += summaryTable(dropping);
    }
    // The lines under the lists are a group of their own: the first one group gap under the lists.
    var closing = [];
    if (removing) {
        closing.push({text: warningSign() + "Everything in " + breakablePath(target) + " will be removed."});
    } else if (installer.isInstaller()) {
        closing.push({text: "Install to " + breakablePath(target)});
    }
    closing.forEach(function (line, index) {
        text += '<p style="margin: ' + (index === 0 ? groupGap : rowGap) + "px " + sideIndent + "px 0 "
            + sideIndent + 'px">' + line.text + "</p>";
    });
    summary.textFormat = 1;  // Qt.RichText
    summary.text = text;
    summary.visible = true;
}

// The install page: where it goes, the choices, and the space it needs. What EasyDiffraction is, as easydiffraction.org's
// home page says it, is not on it (the shortcut, the desktop entry and the component say it: installscript.qs,
// package.py).
var DESCRIPTION = "Calculate diffraction patterns and fit a structural model to your data.";
var licenseUrl = "https://www.gnu.org/licenses/gpl-3.0.html";

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
    var bytes = 0, tool = false;
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var name = all[i].name;
        if (name === assistantComponent && !assistantChosen())
            continue;
        tool = tool || name === maintenanceComponent;
        bytes += componentBytes(all[i]);
    }
    // The maintenance tool, which a script does not see among the components (summaryEntries).
    return bytes + (tool ? 0 : toolBytes);
}

function updateSpace() {
    var label = installPageField("SpaceLabel");
    var folder = folderField();
    if (!label || !folder)
        return;
    var free = freeSpace(folderValue());
    label.text = sizeText(neededSpace()) + " needed" + (isNaN(free) ? "" : " · " + sizeText(free) + " available");
    choiceSizes(gui.pageWidgetByObjectName("TargetDirectoryPage"));
}

// Each choice's size on its right, as the update summary shows them: EasyDiffraction's carries everything that is
// neither the assistant nor the maintenance tool, so the rows add up to the space line when all are ticked.
function choiceSizes(page) {
    if (!page)
        return;
    var sizes = {app: 0, assistant: 0, maintenance: 0};
    var all = installer.components();
    for (var i = 0; i < all.length; ++i) {
        var bytes = componentBytes(all[i]);
        var part = all[i].name === assistantComponent ? "assistant"
            : all[i].name === maintenanceComponent ? "maintenance" : "app";
        sizes[part] += bytes;
    }
    // The maintenance tool, which a script does not see among the components (summaryEntries).
    if (sizes.maintenance === 0)
        sizes.maintenance = toolBytes;
    [["App", sizes.app], ["Assistant", sizes.assistant], ["Maintenance", sizes.maintenance]].forEach(function (row) {
        var size = gui.findChild(page, row[0] + "SizeLabel");
        if (size)
            size.text = sizeText(row[1]);
    });
    return sizes;
}

function setupInstallPage(page) {
    showIntro();
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
        if (String(folder.text) !== folderValue())
            folder.text = folderValue();
    }
    if (!installPageReady) {
        if (license)
            license.checked = true;
        if (shortcut) {
            gui.findChild(page, "ShortcutBox").visible = systemInfo.kernelType !== "darwin";
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
                if (!folder.focus && !showingShort)
                    refreshInstallPage();
            });
        }
        if (ownField) {
            // Shortened again when its editing ends, and shown whole once it is clicked into.
            folder.editingFinished.connect(shortenFolder);
            folder.cursorPositionChanged.connect(function () {
                if (folder.focus && String(folder.text) !== folderValue()) {
                    showingShort = true;
                    folder.text = folderValue();
                    showingShort = false;
                }
            });
            folder.textChanged.connect(function () {
                if (showingShort)
                    return;
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
                shortenFolder();
            });
        }
        installPageReady = true;
    }
    refreshInstallPage();
    // Once the page is laid out, so the field's width is known. The field gives up the keyboard focus the window
    // hands it as the page opens (macOS does), so it shows shortened, without a caret, until clicked into.
    if (ownField)
        [0, 150].forEach(function (delay) {
            later(delay, function () {
                if (folder.focus)
                    page.setFocus();
                shortenFolder();
            });
        });
}

// A folder too long for its field is shown shortened in the middle, its start and end kept, whole in its
// tooltip and while it is edited. The Framework's own field, hidden, keeps it whole: that is what is installed to and
// what the page checks (folderValue).
var showingShort = false;

function folderValue() {
    var theirs = installPageField("TargetDirectoryLineEdit");
    var field = installPageField("FolderLineEdit") && theirs ? theirs : folderField();
    return field ? String(field.text) : "";
}

function shortenFolder() {
    var folder = installPageField("FolderLineEdit");
    var theirs = installPageField("TargetDirectoryLineEdit");
    if (!folder || !theirs || folder.focus)
        return;
    var full = folderValue();
    // About 8 px a character at the pages' 14 px text (a little more than a path's average, so it fits), inside
    // the field's padding.
    var fit = Math.floor((folder.width - 20) / 8);
    var head = Math.ceil((fit - 1) / 2), tail = Math.floor((fit - 1) / 2);
    var text = full.length > fit && fit > 8 ? full.substr(0, head) + "\u2026" + full.substr(full.length - tail) : full;
    folder.toolTip = full;
    if (String(folder.text) !== text) {
        showingShort = true;
        folder.text = text;
        showingShort = false;
    }
}

// What the chosen folder says: an installation already in it is updated by its maintenance tool, not installed
// twice. A licence refusal stays said until Install is pressed again.
var licenseRefused = false;

// The form's rows stand one row gap apart and its groups one group gap (the logo one step above them), measured once
// the page shows: each gap widget above a row (AssistantForm.ui) takes what the drawn frames need. A row with nothing
// shown has no gap.
// The third field is the row's group: the first row shown of a group stands one group gap under the group before.
// On the install page: the folder with the space it needs right under it, then what is installed, then the licence
// and the shortcut, then any notice. A component row is measured by its box alone: the size beside it is no taller,
// and its text arrives as the page opens, which moved it while the rows were being measured.
var formRows = [["Logo", ["FormLogo"], 0], ["Folder", ["FolderLineEdit", "FolderBrowseButton"], 1],
                ["Space", ["SpaceLabel"], 1],
                ["App", ["AppCheckBox"], 2], ["Maintenance", ["MaintenanceCheckBox"], 2],
                ["Assistant", ["AssistantCheckBox"], 2],
                ["License", ["LicenseCheckBox", "LicenseLink"], 3], ["Shortcut", ["ShortcutCheckBox"], 3],
                ["Notice", ["NoticeLabel"], 4]];

// As soon as the page is laid out, so nobody sees it move, once more when the styles have reached every widget, and
// a last time once a page whose text changed as it opened (the warning over an installation) has laid itself out.
function settleSoon(page) {
    [0, 150, 400].forEach(function (delay) { later(delay, function () { settleForm(page); }); });
}

// Repeated until the page is laid out as last asked for and asks for nothing more (bounded), so the last word is always
// a reading of the page as it stands. In captures every reading and what it sets is logged (edi-gap).
function settleForm(page, round) {
    // Only a page on screen has frames to measure.
    if (!page || !page.visible)
        return;
    var previous = false;
    formRows.forEach(function (row) {
        var box = gui.findChild(page, row[0] + "Box");
        var gap = gui.findChild(page, row[0] + "RowGap");
        var shown = box !== null && box.visible;
        if (gap)
            gap.visible = shown && previous;
        previous = previous || shown;
    });
    var license = gui.findChild(page, "LicenseCheckBox");
    var link = gui.findChild(page, "LicenseLink");
    var licenseRow = gui.findChild(page, "LicenseRow");
    later(0, function () {
        // The licence and its link: one row gap between the box's frame and the link.
        if (license && link && licenseRow && license.visible && link.visible)
            adjustOnce(licenseRow, link.x - (license.x + license.width));
        // A page not yet laid out with the gaps last set reads every row below a changed gap at its old place, which
        // put the next gap's correction one row early (measured on Windows). Read only a page that has caught up.
        var lagging = formRows.some(function (row) {
            var gap = gui.findChild(page, row[0] + "RowGap");
            return gap && gap.visible && gap.maximumHeight < 1000 && gap.height !== gap.maximumHeight;
        });
        if (lagging && (round || 0) < 8) {
            later(60, function () { settleForm(page, (round || 0) + 1); });
            return;
        }
        var above = null;
        var unsettled = false;
        formRows.forEach(function (row) {
            var box = gui.findChild(page, row[0] + "Box");
            if (!box || !box.visible)
                return;
            var shown = row[1].map(function (name) { return gui.findChild(page, name); })
                .filter(function (widget) { return widget && widget.visible; });
            if (shown.length === 0)
                return;
            var top = box.y + Math.min.apply(null, shown.map(function (widget) { return widget.y; }));
            var bottom = box.y + Math.max.apply(null, shown.map(function (widget) { return widget.y + widget.height; }));
            var gap = gui.findChild(page, row[0] + "RowGap");
            if (above && gap) {
                // A logo carrying the page's heading (the maintenance tool's choice page) has its step inside.
                var wanted = above.name === "Logo" ? (installer.isInstaller() ? logoStep : rowGap)
                    : above.group !== row[2] ? groupGap : rowGap;
                // What lies between the rows besides the gap widget, all read from the page as it is laid out: a few
                // pixels where a native frame sits off its cell (2 on macOS).
                // More than 2 px is a row read at its old place, not a frame: no correction, and read again.
                var raw = (gap.y - above.bottom) + (top - (gap.y + gap.height));
                var besides = Math.abs(raw) <= 2 ? raw : 0;
                unsettled = unsettled || besides !== raw;
                var height = bounded(wanted - besides, wanted);
                if (captureFolder !== "")
                    console.log("edi-gap " + row[0] + " round " + (round || 0) + " above " + above.bottom + " gap " + gap.y + "+"
                        + gap.height + " (set " + gap.maximumHeight + ") row " + top + " -> " + height);
                unsettled = unsettled || gap.height !== gap.maximumHeight || gap.maximumHeight !== height;
                gap.minimumHeight = height;
                gap.maximumHeight = height;
            }
            above = {name: row[0], bottom: bottom, group: row[2]};
        });
        // On the installer's page the form's first row (our folder) stands one row gap under the page's text: the
        // page's spacing, that page's only gap, takes up where the row's frame sits.
        var install = gui.pageWidgetByObjectName("TargetDirectoryPage");
        var folder = gui.findChild(page, "FolderBox");
        var field = gui.findChild(page, "FolderLineEdit");
        var column = install ? firstLayout(install) : null;
        // The folder row never gives up height: with the window's height held, the warning over an installation
        // squeezed it on macOS (the field lost its lower border) while the space under the boxes stayed empty.
        var browse = gui.findChild(page, "FolderBrowseButton");
        if (folder && field && field.visible) {
            var rowHeight = Math.max(field.minimumHeight, browse ? browse.minimumHeight : 0, field.height);
            if (folder.minimumHeight < rowHeight)
                folder.minimumHeight = rowHeight;
        }
        if (folder && field && field.visible && column && page.objectName === "TargetDirectoryPage")
            column.spacing = bounded(rowGap - (folder.y + field.y), 2 * rowGap);
        if (unsettled && (round || 0) < 8)
            later(60, function () { settleForm(page, (round || 0) + 1); });
        if (captureFolder !== "")
            later(100, function () { logLayout(page, "settled"); });
    });
}

// One plain status line for the progress page: the Framework's changes per step and says little.
function progressStatus() {
    return installer.isInstaller() ? "Installing EasyDiffraction…"
        : installer.isUninstaller() ? "Removing EasyDiffraction…" : "Updating EasyDiffraction…";
}

// The removal's progress: the logo and one status line, then the bar with its percentage inside, laid out as the
// installing and updating page (ProgressForm.ui). Removing loads no component, so there is no form of ours, and the
// Framework's layout puts its bar first and its picture area further down; a script cannot reorder a layout. So the
// bar keeps its place but draws itself a margin lower, and the picture area, holding the logo and the line, is moved
// into that margin each time the page could have been laid out again.
var removalShown = false;
var removalPlaced = false;

function showRemoval(page, bar, label) {
    var area = gui.findChild(page, "ProductImagesScrollArea");
    var header = gui.findChild(page, "ProductImagesLabel");
    if (!area || !header)
        return;
    header.textFormat = 1;  // Qt.RichText
    header.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
    header.wordWrap = false;
    header.text = logo() + '<p style="margin: 0 ' + sideIndent + 'px">' + progressStatus() + "</p>";
    area.verticalScrollBarPolicy = 1;  // Qt.ScrollBarAlwaysOff
    area.horizontalScrollBarPolicy = 1;
    bar.textVisible = true;
    bar.format = "%p%";
    bar.visible = true;
    area.visible = true;
    header.visible = true;
    removalShown = true;
    // The Framework's step text says little and changes per step.
    label.visible = false;
    // The logo, its step and one line (17 px, the status line of the installing page on Linux), then the row gap
    // above the bar, as on the installing page. The track is drawn inside the padding only; the percentage centres in
    // the whole bar, so the same padding below keeps it in the track.
    var head = logoHeight + logoStep + 17;
    area.minimumHeight = head;
    area.maximumHeight = head;
    var pad = head + rowGap;
    bar.styleSheet = "QProgressBar { padding-top: " + pad + "px; padding-bottom: " + pad
        + "px; background-clip: content; }";
    // The logo and line sit over the bar's padding. Placed now, as the page opens, and again on every step: the page
    // lays itself out again as it opens, and a quick removal can end before its first step, which left the logo in
    // the middle of the page and the bar at the top for a frame or for good.
    var place = function () {
        if (page.visible && (area.x !== bar.x || area.y !== bar.y))
            area.pos = bar.pos;
    };
    place();
    later(0, place);
    if (!removalPlaced) {
        bar.valueChanged.connect(place);
        removalPlaced = true;
    }
}

// The done page's box one group gap under its sentence (what was done, then what to do next): on macOS a box's frame
// sits below where its row starts, so the page's spacing (that page's only gap) takes up the difference once shown.
function settleDone(page) {
    var text = gui.findChild(page, "MessageLabel");
    var form = gui.findChild(page, "DoneForm");
    var open = gui.findChild(page, "OpenCheckBox");
    var column = firstLayout(page);
    if (!page.visible || !text || !form || !open || !open.visible || !column)
        return;
    column.spacing = bounded(groupGap - open.y, groupGap);
    if (captureFolder !== "")
        later(100, function () { logLayout(page, "settled"); });
}

// The notice line: the licence refusal and the Framework's refusal of the folder (its warning line, which decides
// whether Install is allowed). Composed whole each time, so nothing stale stays.
var installedHere = false;

// The page's text: the logo and "Install to" over the folder. An installation already in the folder is said as a
// warning right above "Install to", from the moment the page opens with that folder.
var INSTALLED_HERE = "EasyDiffraction is already installed here. To update it, open its Maintenance Tool and choose "
    + "Update.";

function showIntro() {
    var intro = installPageField("MessageLabel");
    if (!intro)
        return;
    var text = logo() + (installedHere ? PARA + warningSign() + INSTALLED_HERE + "</p>" + GROUP : PARA)
        + "Install to</p>";
    intro.textFormat = 1;  // Qt.RichText
    if (String(intro.text) !== text)
        intro.text = text;
}

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
    showIntro();
    notice.textFormat = 1;  // Qt.RichText
    notice.text = lines.length > 0 ? warningSign() + lines.join(" ") : "";
    installPageField("NoticeBox").visible = lines.length > 0;
    settleSoon(gui.pageWidgetByObjectName("TargetDirectoryPage"));
}

// Our folder field, or the Framework's where our form is missing.
function folderField() {
    return installPageField("FolderLineEdit") || installPageField("TargetDirectoryLineEdit");
}

function refreshInstallPage() {
    var folder = folderField();
    var target = folder ? folderValue() : installer.value("TargetDir");
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
                    images.visible = removalShown;
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
var PARA = '<p style="margin: ' + rowGap + 'px ' + sideIndent + 'px 0 ' + sideIndent + 'px">';
// The first paragraph of a new group: one group gap above it.
var GROUP = '<p style="margin: ' + groupGap + 'px ' + sideIndent + 'px 0 ' + sideIndent + 'px">';

// The logo heading a page's text, logoStep above what follows it (templatePage).

function logo() {
    return '<p style="margin-bottom: ' + logoStep + 'px">' + headerWordmark() + "</p>";
}

// The logo drawn from app/web's SVG at the size shown, 2x and 3x (render_images.qml): the Framework's Qt has no SVG
// image plugin, and Qt picks the @2x or @3x file for a sharper screen by itself.
function headerWordmark() {
    if (wordmark === "")
        wordmark = '<img src=":/metadata/edi/' + (darkTheme() ? "logo-dark" : "logo") + '.png" width="140" height="'
            + logoHeight + '">';
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
        fixWindowHeight();
        // A maintenance tool restarted from its last page offers nothing to open until it is there again.
        if (name !== "Finished")
            openOffered = false;
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
            watchChoices(page);
            if (!introductionHooked) {
                page.left.connect(nameSummaryStep);
                introductionHooked = true;
            }
        }

        // The summary without the Framework's component trees: a tree view is what macOS accessibility clients
        // crashed (edi #150), so none may show. One plain sentence says what happens.
        if (name === "ReadyForInstallation") {
            writeSummary(page);
            // A change of components is applied, not an update.
            if (installer.isPackageManager())
                gui.setWizardPageButtonText(QInstaller.ReadyForInstallation, buttons.CommitButton, "Apply");
        }
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
            watchWelcome(page);
            if (captureFolder === "")
                gui.clickButton(buttons.NextButton, 50);
            else if (installerWalked)
                gui.clickButton(buttons.NextButton, 50);
            else {
                // Next fetches the components; a locked walk's page is noted and captured once it says why it
                // stays (sayStuck).
                if (captureState !== "locked")
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
                + "<p>" + DESCRIPTION + "</p>"
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
            // Cancel is never the page's main action, even as its only button (the style fills a default button).
            var cancel = gui.findChild(gui, "qt_wizard_cancel");
            if (cancel) {
                cancel.autoDefault = false;
                cancel["default"] = false;
            }
            // --verbose opens the details, which stops the Framework moving on by itself when done: they are closed
            // with their own button, which turns that back on, and the button and download count are hidden.
            var detailsBrowser = gui.findChild(page, "DetailsBrowser");
            var detailsButton = gui.findChild(page, "DetailsButton");
            // Our timer (later) opens and closes the details for a moment; with their own minimum height they made
            // the page ask for more room, and on macOS the window grew for the rest of the walk (8 px on updating).
            if (detailsBrowser) {
                detailsBrowser.minimumHeight = 0;
                detailsBrowser.maximumHeight = 0;
            }
            var closeDetails = function () {
                if (detailsBrowser && detailsBrowser.visible && detailsButton) {
                    closingDetails = true;
                    detailsButton.click();
                    closingDetails = false;
                }
            };
            closeDetails();
            // The product-images area is invisible but takes the page's height, which left our bar far below (the
            // removal uses it for its logo, showRemoval).
            ["DetailsButton", "DownloadStatus", "ProductImagesScrollArea", "ProductImagesLabel"].forEach(function (hidden) {
                var widget = gui.findChild(page, hidden);
                if (widget)
                    widget.visible = false;
            });
            // The Framework shows its download line again once a maintenance tool downloads (updating, changing
            // components), and the page then asked for its height: on macOS the window grew 8 px for the rest of the
            // walk. Kept without height, it changes nothing however often it is shown.
            ["DownloadStatus", "ProgressLabel"].forEach(function (name) {
                var widget = gui.findChild(page, name);
                if (widget) {
                    widget.minimumHeight = 0;
                    widget.maximumHeight = 0;
                }
            });
            // Our bar with its percentage inside (ProgressForm.ui), fed from the Framework's bar, which is hidden;
            // where our form is missing (no assistant component loaded), the Framework's bar stays, styled the same.
            var bar = gui.findChild(page, "ProgressBar");
            var label = gui.findChild(page, "ProgressLabel");
            var ours = gui.findChild(page, "EdiProgressBar");
            var status = gui.findChild(page, "EdiProgressStatus");
            var mark = gui.findChild(page, "EdiProgressLogo");
            // Removing loads no component, so there is no form of ours to show.
            if (bar && label && !ours)
                showRemoval(page, bar, label);
            if (bar && label && ours && status && !progressHooked) {
                bar.visible = false;
                label.visible = false;
                if (mark) {
                    mark.textFormat = 1;  // Qt.RichText
                    mark.text = headerWordmark();
                }
                status.text = progressStatus();
                bar.valueChanged.connect(function (value) {
                    var share = bar.maximum > bar.minimum
                        ? Math.round(100 * (value - bar.minimum) / (bar.maximum - bar.minimum)) : 0;
                    ours.value = share;
                });
                progressHooked = true;
            }
        }

        // Done: where to find it, and the program opened directly if wanted. No folder path.
        if (name === "Finished") {
            // The Maintenance Tool's last page offers to start it again for another change (the Framework's Restart).
            if (!installer.isInstaller())
                gui.setWizardPageButtonText(QInstaller.InstallationFinished, buttons.CommitButton, "Make more changes");
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
                done.textFormat = 1;  // Qt.RichText
                done.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop, as every page
                done.text = logo() + PARA + "EasyDiffraction is installed. You'll find it " + where
                    + ".</p>";
            }
            // The maintenance tool says what it did the same way, in one line; a failure keeps the Framework's words.
            if (done && !installer.isInstaller() && String(done.text).indexOf("<img") < 0) {
                done.textFormat = 1;  // Qt.RichText
                done.alignment = 0x0001 | 0x0020;  // Qt.AlignLeft | Qt.AlignTop
                var said = installer.isUninstaller() ? "EasyDiffraction is removed."
                    : installer.isUpdater() ? "EasyDiffraction is updated." : "Your changes are made.";
                done.text = logo() + PARA + (installer.status === QInstaller.Success ? said
                    : warningSign() + done.text) + "</p>";
            }
            ["LocationLabel", "FinishText"].forEach(function (hidden) {
                var widget = gui.findChild(page, hidden);
                if (widget)
                    widget.visible = false;
            });
            // Our own box in a row of its own (DoneForm.ui), ticked, after a successful installation or change; the
            // Framework's box has no program to run and stays hidden. Captures keep it ticked and open nothing.
            var run = gui.findChild(page, "RunItCheckBox");
            if (run)
                run.visible = false;
            var open = gui.findChild(page, "OpenCheckBox");
            later(0, function () { settleDone(page); });
            later(150, function () { settleDone(page); });
            if (open) {
                openOffered = installer.status === QInstaller.Success && !installer.isUninstaller();
                open.visible = openOffered;
                if (!openHooked) {
                    open.checked = true;
                    openHooked = true;
                }
            }
        }

        // No title, so no header: the logo heads the page's own content.
        keepUntitled(page);
        // The quit walk pictures only its question.
        if (captureState === "quit")
            notePage(name);
        else
            capture(name);
        advance(name, page);
    };
});
