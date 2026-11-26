// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "SequentialDataDirectory"
    when: windowShown
    property var app
    Component { id: windowFactory; Main {} }

    function init() {
        app = windowFactory.createObject(null);
        verify(app !== null, "Changing the fit directory needs the actual Analysis page");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The Analysis window receives real directory input");
    }

    function cleanup() {
        Session.closeProject();
        app.destroy();
    }

    function test_typed_directory_has_its_own_row_and_persists() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
        const oldPath = "experiments/d20_scan";
        const newPath = "experiments/alternate_scan";
        const dataset = "/all594687.dat";
        verify(SettingsProof.write(root, newPath + dataset, SettingsProof.text(root, oldPath + dataset)),
               "The directory edit has a second real directory inside the private project");
        verify(Session.openProject(root), "The scan template opens for the directory edit");
        Ui.click(test, Probe, app, "appBar.tab.analysis");
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        Ui.expandGroup(test, Probe, app, "group.sequential_fit");
        const scope = Ui.control(Probe, app, "group.sequential_fit");
        const field = findChild(scope, "sequentialFit.dataDir");
        const pattern = findChild(scope, "sequentialFit.filePattern");
        verify(field !== null && pattern !== null, "Analysis shows the directory and the filename pattern");
        verify(field.enabled && !field.readOnly, "The sequential fit data directory must be editable");
        verify(field.mapToItem(scope.contentItem, 0, field.height / 2).y
               !== pattern.mapToItem(scope.contentItem, 0, pattern.height / 2).y,
               "The directory is on its own row, apart from the filename pattern");
        const browse = Render.descendants(scope.contentItem).find(item => item.visible && item.enabled
            && typeof item.clicked === "function"
            && /browse|choose.*folder|select.*directory/i.test([item.objectName, item.text, item.toolTip].join(" ")));
        verify(browse !== undefined, "The data directory row includes an enabled browse control");
        const browsePoint = browse.mapToItem(field, 0, browse.height / 2);
        verify(browsePoint.y >= 0 && browsePoint.y <= field.height,
               "The browse control sits inside the data directory row");
        Ui.scrollIntoView(field);
        const point = Ui.clickPoint(field);
        verify(point !== null, "The data directory field is in the visible Analysis sidebar");
        Ui.click(test, Probe, app, "sequentialFit.dataDir");
        tryCompare(field, "activeFocus", true, 1000, "Clicking the directory field gives it keyboard focus");
        verify(SettingsProof.type(field, newPath) && SettingsProof.key(field, Qt.Key_Return),
               "The app accepts the typed directory through the field's normal editor");
        tryCompare(Session.project.analysis.sequentialFit, "dataDir", newPath, 2000,
                   "The declaration adopts the typed project-relative path");
        verify(Session.save(), "Saving the scan persists the new directory");
        Session.closeProject();
        verify(Session.openProject(root), "Reopening the scan loads the saved directory");
        compare(Session.project.analysis.sequentialFit.dataDir, newPath,
                "The new directory survives saving and reopening the project");
    }
}
