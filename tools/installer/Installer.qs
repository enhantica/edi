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

function Controller() {
    installer.installationFinished.connect(clearQuarantine);
    installer.updateFinished.connect(clearQuarantine);
}

var wordmark = "";

function headerWordmark() {
    if (wordmark === "") {
        var image = "@WORDMARK@";
        if (systemInfo.kernelType === "darwin") {
            var appearance = installer.execute("/usr/bin/defaults", ["read", "-g", "AppleInterfaceStyle"]);
            if (appearance[1] === 0 && appearance[0].trim() === "Dark")
                image = "@DARK_WORDMARK@";
        }
        wordmark = '<img src="data:image/png;base64,' + image + '" width="140" height="44">';
    }
    return wordmark;
}

[
    "Introduction", "TargetDirectory", "ComponentSelection", "LicenseAgreement",
    "StartMenuDirectory", "ReadyForInstallation", "PerformInstallation", "Finished"
].forEach(function (name) {
    Controller.prototype[name + "PageCallback"] = function () {
        if (!installer.isInstaller())
            return;
        var page = gui.pageWidgetByObjectName(name + "Page");
        if (!page)
            return;

        if (name === "Introduction") {
            var welcome = gui.findChild(page, "MessageLabel");
            welcome.openExternalLinks = true;
            welcome.text = "<p>Welcome to EasyDiffraction Setup.</p>"
                + "<p>EasyDiffraction calculates diffraction patterns from a structural model "
                + "and refines its parameters against experimental data.</p>"
                + '<p>Learn more at <a href="https://easydiffraction.org">easydiffraction.org</a>.</p>';
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
    };
});
