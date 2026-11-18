// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// A magnetic CIF dropped on the whole window is loaded as a structure into the open project, through the window's own
// drop route (ApplicationInfo.dropProject), not opened as a project.
TestCase {
    id: test

    name: "WindowDropStructure"
    when: windowShown

    property var window: null

    function initTestCase() {
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "window.projectDrop") !== null, 10000);
    }
    function cleanupTestCase() {
        window.destroy();
    }

    function test_a_magnetic_cif_dropped_on_the_window_becomes_a_structure() {
        verify(Session.createProject("dropped", ""));
        const project = Session.project;
        const before = project.structures.count;
        let accepted = false;
        const drop = {
            "hasUrls": true,
            "urls": [Qt.resolvedUrl("../magnetic_pnma/cosio/isodistort.mcif")],
            "accept": () => {
                accepted = true;
            }
        };
        ApplicationInfo.dropProject(drop);
        verify(accepted, "the drop is taken");
        tryCompare(project.structures, "count", before + 1, 10000);
        compare(Session.project, project, "the open project stays open");
    }

    // A structure .edi is a structure too; the project the drop was made on keeps it.
    function test_b_a_structure_edi_dropped_on_the_window_becomes_a_structure() {
        const project = Session.project;
        const before = project.structures.count;
        ApplicationInfo.dropProject({
            "hasUrls": true,
            "urls": [Qt.resolvedUrl("../constraint_initial_context/project/structures/phase.edi")],
            "accept": () => {}
        });
        tryCompare(project.structures, "count", before + 1, 10000);
        compare(Session.project, project);
    }
}
