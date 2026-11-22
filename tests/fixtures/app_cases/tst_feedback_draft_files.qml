// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// An unsent draft keeps its attached files across closing and opening the form, as it keeps its text; they go only
// after a successful send or when the user removes them.
Item {
    id: root

    width: 1200
    height: 900

    property int answer: 201

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
        endpoint: "https://feedback.invalid/feedback"
        transport: (url, payload, completed) => completed(root.answer, "", JSON.stringify({
                "number": 1,
                "attached": (payload.attachments ?? []).map(file => file.name)
            }))
    }

    TestCase {
        name: "FeedbackDraftFiles"
        when: windowShown

        function file(name) {
            return {
                "name": name,
                "type": "text/plain",
                "size": 4,
                "data": "ZGF0YQ=="
            };
        }
        // A Repeater's delegates are visual children only, which findChild does not walk.
        function removeLink(index) {
            const visit = item => {
                if (!item)
                    return null;
                if (item.objectName === "feedback.files.remove." + index)
                    return item;
                for (const child of item.children) {
                    const found = visit(child);
                    if (found)
                        return found;
                }
                return null;
            };
            return visit(findChild(form, "feedback.files"));
        }
        function reopen() {
            form.close();
            tryVerify(() => !form.visible);
            form.openAs("feedback", "");
            tryVerify(() => form.opened);
        }
        function cleanup() {
            form.close();
            tryVerify(() => !form.visible);
            form.attachedFiles = [];
            findChild(form, "feedback.text").text = "";
        }

        function test_files_stay_with_the_unsent_draft() {
            form.openAs("problem", "", "the message", [file("hrpt.xye"), file("lbco.cif")]);
            tryVerify(() => form.opened);
            reopen();
            compare(findChild(form, "feedback.text").text, "the message");
            compare(form.attachedFiles.map(item => item.name), ["hrpt.xye", "lbco.cif"]);
        }
        function test_a_removed_file_stays_removed() {
            form.openAs("problem", "", "the message", [file("hrpt.xye"), file("lbco.cif")]);
            tryVerify(() => form.opened);
            tryVerify(() => removeLink(0) !== null);
            mouseClick(removeLink(0));
            compare(form.attachedFiles.map(item => item.name), ["lbco.cif"]);
            reopen();
            compare(form.attachedFiles.map(item => item.name), ["lbco.cif"]);
        }
        function test_a_failed_send_keeps_them() {
            root.answer = 500;
            form.openAs("problem", "", "the message", [file("lbco.cif")]);
            tryVerify(() => form.opened);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.lastStatus === 500);
            reopen();
            compare(form.attachedFiles.length, 1);
            root.answer = 201;
        }
        function test_a_successful_send_clears_them() {
            root.answer = 201;
            form.openAs("problem", "", "the message", [file("lbco.cif")]);
            tryVerify(() => form.opened);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.sent);
            compare(form.attachedFiles.length, 0);
            compare(findChild(form, "feedback.text").text, "");
        }
    }
}
