// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app
import edi.app.test

// Files dropped on the open Help and feedback form are attached with the same checks as Attach files, and the
// form shows where they go while one is dragged over it. Run with `edi_app_tests -input tests/fixtures/app_cases`.
Item {
    id: root

    width: 1200
    height: 900

    readonly property url structure: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20/project/structures/cosio.edi")
    readonly property url project: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20/project/project.edi")

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
    }

    TestCase {
        name: "FeedbackDrop"
        when: windowShown

        function init() {
            form.open();
            tryVerify(() => form.opened);
        }
        function cleanup() {
            form.close();
            tryVerify(() => !form.visible);
            form.attachedFiles = [];  // a draft keeps its files across closing; each case starts without any
        }
        function findNamed(item, name) {
            if (!item)
                return null;
            if (item.objectName === name)
                return item;
            for (let i = 0; i < item.children.length; ++i) {
                const found = findNamed(item.children[i], name);
                if (found)
                    return found;
            }
            return null;
        }

        function test_drop_target_covers_the_form() {
            const drop = findNamed(form.background, "feedback.drop");
            verify(drop, "the form has its own drop target");
            verify(drop.enabled);
            compare(drop.width, form.background.width);
            compare(drop.height, form.background.height);
        }

        function test_dropped_files_take_the_attach_checks() {
            form.attach([root.structure]);
            compare(form.attachedFiles.length, 1);
            compare(form.attachedFiles[0].name, "cosio.edi");
            compare(form.attachmentError, "");
            form.attach([root.structure, root.project, root.structure, root.project, root.structure]);
            compare(form.attachedFiles.length, 6);
            verify(form.attachmentError.indexOf("at most 5 files") >= 0, form.attachmentError);
        }

        function test_an_unreadable_file_is_named() {
            form.attach([Qt.resolvedUrl("no-such-file.cif")]);
            compare(form.attachedFiles.length, 0);
            verify(form.unreadableFiles.indexOf("no-such-file.cif") >= 0, form.unreadableFiles);
        }

        function test_dragging_highlights_and_dropping_attaches() {
            const highlight = findNamed(form.background, "feedback.dropHighlight");
            verify(highlight);
            const x = form.background.width / 2, y = form.background.height / 2;
            verify(TestDrop.enter(form.background, x, y, [root.structure]), "the form accepts a dragged file");
            tryVerify(() => form.dropping, 2000, "the form shows where the file goes");
            verify(highlight.visible);
            verify(TestDrop.drop(form.background, x, y), "the form takes the dropped file");
            compare(form.attachedFiles.length, 1);
            compare(form.attachedFiles[0].name, "cosio.edi");
            tryVerify(() => !highlight.visible);
        }
    }
}
