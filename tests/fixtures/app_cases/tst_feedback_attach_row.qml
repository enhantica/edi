// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest

import edi.app

// Attach files is a short link at the right of the log box's row, its detail in a tooltip, inside the form; a 201 that
// does not confirm the attached files says they were not attached, never a plain success.
Item {
    id: root

    width: 1200
    height: 900

    property string answerText: "{}"

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
        endpoint: "https://feedback.invalid/feedback"
        transport: (url, payload, completed) => completed(201, "", root.answerText)
    }

    TestCase {
        name: "FeedbackAttachRow"
        when: windowShown

        function file(name) {
            return {
                "name": name,
                "type": "text/plain",
                "size": 4,
                "data": "ZGF0YQ=="
            };
        }
        function status() {
            return findChild(form, "feedback.status").text;
        }
        function open(files) {
            form.openAs("problem", "", "not a project directory", files);
            tryVerify(() => form.opened);
        }
        function cleanup() {
            form.close();
            tryVerify(() => !form.visible);
        }

        function test_attach_link_shares_the_log_row_and_fits() {
            open([]);
            const link = findChild(form, "feedback.files.add");
            const include = findChild(form, "feedback.include");
            verify(link.visible);
            compare(link.text, "Attach files");
            verify(link.ToolTip.text.indexOf("up to 5 files, 5 MB each, 10 MB in total") >= 0, link.ToolTip.text);
            verify(link.ToolTip.text.indexOf("dropped on the form") >= 0);
            const linkAt = link.mapToItem(form.contentItem, 0, 0);
            const includeAt = include.mapToItem(form.contentItem, 0, 0);
            verify(Math.abs((linkAt.y + link.height / 2) - (includeAt.y + include.height / 2)) <= 2, "the same row");
            verify(linkAt.x > includeAt.x + include.width, "at the right");
            verify(linkAt.x + link.width <= form.contentItem.width + 1, "not cut off");
        }
        function test_unconfirmed_files_are_said_not_attached() {
            root.answerText = JSON.stringify({
                "number": 55
            });
            open([file("hrpt.xye"), file("lbco.cif")]);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.sent);
            verify(status().indexOf("hrpt.xye, lbco.cif were not attached") >= 0, status());
        }
        function test_partly_confirmed_files_name_the_missing_one() {
            root.answerText = JSON.stringify({
                "number": 56,
                "attached": ["lbco.cif"]
            });
            open([file("hrpt.xye"), file("lbco.cif")]);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.sent);
            verify(status().indexOf("hrpt.xye was not attached") >= 0, status());
        }
        function test_confirmed_files_are_a_plain_success() {
            root.answerText = JSON.stringify({
                "number": 57,
                "attached": ["hrpt.xye", "lbco.cif"]
            });
            open([file("hrpt.xye"), file("lbco.cif")]);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.sent);
            compare(status(), "Your message was sent. Thank you!");
        }
        function test_no_files_needs_no_confirmation() {
            root.answerText = JSON.stringify({
                "number": 58
            });
            open([]);
            mouseClick(findChild(form, "feedback.send"));
            tryVerify(() => form.sent);
            compare(status(), "Your message was sent. Thank you!");
        }
    }
}
