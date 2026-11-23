// Walks the installer's pages for the accessibility check (tools/installer/a11y-check.sh): each page stays up a few
// seconds while an accessibility client reads it, then the walk moves on; at the last page before installing it
// quits without installing anything.

var PAUSE = 6000;  // ms on each page, so the client reads it several times

function Controller() {
    installer.autoRejectMessageBoxes();
    installer.setMessageBoxAutomaticAnswer("cancelInstallation", QMessageBox.Yes);
    // The candidate fix for edi #150, tried on a released installer: no component selection page.
    if (installer.value("A11yHideComponents") === "true")
        installer.setDefaultPageVisible(QInstaller.ComponentSelection, false);
}

Controller.prototype.WelcomePageCallback = function() {
    gui.clickButton(buttons.NextButton, PAUSE);
};

Controller.prototype.IntroductionPageCallback = function() {
    gui.clickButton(buttons.NextButton, PAUSE);
};

Controller.prototype.TargetDirectoryPageCallback = function() {
    var page = gui.currentPageWidget();
    page.TargetDirectoryLineEdit.setText(installer.value("A11yTarget"));
    gui.clickButton(buttons.NextButton, PAUSE);
};

Controller.prototype.ComponentSelectionPageCallback = function() {
    gui.clickButton(buttons.NextButton, PAUSE);
};

Controller.prototype.LicenseAgreementPageCallback = function() {
    gui.currentPageWidget().AcceptLicenseRadioButton.setChecked(true);
    gui.clickButton(buttons.NextButton, PAUSE);
};

Controller.prototype.ReadyForInstallationPageCallback = function() {
    gui.clickButton(buttons.CancelButton, PAUSE);
};
