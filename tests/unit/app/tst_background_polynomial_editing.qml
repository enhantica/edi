import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui

// The bounded process exercises the actual Main-tab component. The compound
// full-Main/page witness stays in the correlation actor unchanged; unrelated
// charts do not need to start to judge coefficient editing or its real input.
TestCase {
    id: test
    name: "BackgroundPolynomialEditing"
    when: windowShown
    property var appWindow
    property var backgroundPanel
    property int savedTheme
    Component {
        id: application
        ApplicationWindow {
            width: 900
            height: 800
            visible: true
            // Ui's page lookup sees this window's single actual production pane.
            readonly property var contentArea: [backgroundPanel]
            readonly property QtObject appBarCentralTabs: QtObject { property int currentIndex: 0 }
        }
    }
    Component { id: backgroundComponent; BackgroundGroup { width: 650; x: 20; y: 20 } }
    function init() {
        savedTheme = Style.Colors.theme;
        Style.Colors.theme = Style.Colors.LightTheme;
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Polynomial editing must use a real Qt window");
        verify(waitForRendering(appWindow.contentItem), "The polynomial window must render before input");
    }
    function cleanup() {
        if (backgroundPanel) backgroundPanel.destroy();
        backgroundPanel = null;
        Session.closeProject();
        appWindow.close();
        appWindow.destroy();
        Probe.releaseScratchProjects();
        Style.Colors.theme = savedTheme;
    }
    function click(name) {
        Ui.click(test, Probe, appWindow, name);
    }
    function control(name) {
        return Ui.control(Probe, appWindow, name);
    }
    function test_background_coefficients_have_editing_parity() {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/polynomial-3"));
        verify(Session.openProject(input), "Polynomial editing opens the same disposable authored fixture");
        backgroundPanel = backgroundComponent.createObject(appWindow.contentItem,
            {experiment: Session.project.currentExperiment});
        verify(backgroundPanel !== null && waitForPolish(backgroundPanel),
               "The bounded actor must instantiate the actual Main BackgroundGroup");
        const terms = Session.project.currentExperiment.backgroundTerms;
        verify(control("background.terms") !== null, "Polynomial must show its term table");
        const count = terms.count;
        click("background.appendTerm");
        compare(terms.count, count + 1, "Append must add exactly one coefficient");
        compare(Probe.rows(terms)[count].order, 3, "Append must choose the lowest unused order");
        verify(!terms.setOrder(count, 0), "A duplicate coefficient order must be refused");
        verify(!terms.setOrder(count, 6), "Polynomial orders above five must be refused");
        verify(terms.setOrder(count, 5), "A unique supported order must be editable");
        const coefficient = control("background.coef.0");
        verify(coefficient !== null, "The coefficient value must have a visible editing control");
        coefficient.forceActiveFocus();
        verify(SettingsProof.type(coefficient, "6.25"), "The keyboard observer sends real text to the coefficient's own app window and active input, rather than the Quick Test runner window; actual text=" + coefficient.text);
        verify(SettingsProof.key(coefficient, Qt.Key_Return), "Return reaches the actual coefficient editor's own app window to commit its typed value");
        compare(Probe.rows(terms)[0].coef.value, 6.25, "Actual keyboard input plus Return commits the independently entered background coefficient; actual first term=" + JSON.stringify(Probe.rows(terms)[0]));
        click("background.removeTerm." + count);
        compare(terms.count, count, "Remove must erase exactly the selected coefficient");
        console.log("BACKGROUND_POLYNOMIAL_PARITY editing=typed append=clicked remove=clicked");
    }
}
