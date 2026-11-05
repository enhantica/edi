// SPDX-License-Identifier: BSD-3-Clause

function Controller() {}

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
        page.title = "";
        page.subTitle = "";
    };
});
