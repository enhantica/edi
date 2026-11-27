// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// A sequential fit's data directory has a row of its own with its browse button inside it: a typed path and a chosen
// folder are the same edit with the same Undo, a path that is no folder is refused at the field, and where no folder
// can be named (a browser) the field is read-only.
Item {
    id: root

    width: 600
    height: 300

    readonly property url cosio: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project")
    readonly property url other: Qt.resolvedUrl("../../../docs/user/cli/pd-xray-cwl_latp_scan-4f/project/experiments/bm01_scan")

    SequentialFitGroup {
        id: group
        width: root.width
        project: Session.project
        analysis: Session.project ? Session.project.analysis : null
    }

    TestCase {
        id: test

        name: "SequentialDataDirectory"
        when: windowShown

        readonly property string here: "experiments/d20_scan"
        property var field: null
        property var browse: null

        function init() {
            verify(Session.openProject(root.cosio), Session.lastError);
            field = findChild(group, "sequentialFit.dataDir");
            browse = findChild(group, "sequentialFit.dataDir.browse");
            tryCompare(field, "text", here);
            wait(300);
        }
        function cleanup() {
            group.folderEditable = true;
            Session.closeProject();
        }
        function type(text) {
            field.forceActiveFocus();
            field.selectAll();
            field.remove(0, field.length);
            field.insert(0, text);
            keyClick(Qt.Key_Return);
        }
        function local(url) {
            return decodeURIComponent(String(url).replace(/^file:\/\/(\/[A-Za-z]:)?/, "$1"));
        }

        function test_a_its_own_row_with_the_button_inside() {
            const pattern = findChild(group, "sequentialFit.filePattern");
            verify(field.mapToItem(group, 0, field.height).y <= pattern.mapToItem(group, 0, 0).y);
            verify(field.width > pattern.width * 1.5);
            verify(browse.visible);
            const corner = browse.mapToItem(field, browse.width, browse.height);
            verify(corner.x <= field.width + 0.5 && corner.y <= field.height + 0.5);
            verify(field.rightPadding >= browse.width);
        }
        function test_b_a_typed_path_and_its_undo() {
            // The example is open as a copy, so the path is from where that copy is.
            const place = Session.project.path.replace(/\\/g, "/").split("/").filter(part => part !== "");
            const relative = "../".repeat(place.length) + local(root.other).replace(/^\//, "");
            type(relative);
            tryCompare(Session.project.analysis.sequentialFit, "dataDir", relative, 10000);
            compare(field.refusal, "");
            verify(Session.project.canUndo);
            tryVerify(() => {
                if (Session.project.analysis.sequentialFit.dataDir !== here)
                    Session.project.undo();
                return Session.project.analysis.sequentialFit.dataDir === here;
            }, 10000);
            tryCompare(field, "text", here);
        }
        function test_c_an_absolute_path_is_the_chosen_folder() {
            type(local(root.other));
            tryVerify(() => Session.project.analysis.sequentialFit.dataDir.endsWith("bm01_scan"), 10000, field.refusal);
            const typed = Session.project.analysis.sequentialFit.dataDir;
            tryVerify(() => {
                if (Session.project.analysis.sequentialFit.dataDir !== here)
                    Session.project.undo();
                return Session.project.analysis.sequentialFit.dataDir === here;
            }, 10000);
            wait(2000);  // the dataset before is read
            verify(Session.project.locateDataFolder(root.other), Session.project.lastError);
            compare(Session.project.analysis.sequentialFit.dataDir, typed);
        }
        function test_d_no_folder_is_refused_at_the_field() {
            type("experiments/nowhere");
            tryVerify(() => field.refusal.indexOf("is not a folder") >= 0, 5000, field.refusal);
            compare(Session.project.analysis.sequentialFit.dataDir, here);
            compare(field.text, here);
            verify(!Session.project.canUndo);
        }
        function test_e_read_only_without_folders() {
            group.folderEditable = false;
            verify(field.readOnly);
            verify(!browse.visible);
            compare(field.text, here);
        }
    }
}
