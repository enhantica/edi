// SPDX-License-Identifier: BSD-3-Clause

function Controller() {}

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
