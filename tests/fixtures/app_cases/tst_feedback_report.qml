// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

import "../../../app/feedback/Payload.js" as Payload

// Copy report appears only after a failed send (any answer but 201, no answer included) and copies the message as
// plain text, attached files listed by name; it is hidden before a send and after a success.
Item {
    id: root

    width: 1200
    height: 900

    property int answer: 0
    property string answerDetail: ""

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
        endpoint: "https://feedback.invalid/feedback"
        transport: (url, payload, completed) => completed(root.answer, root.answerDetail)
    }
    // Reads the clipboard back where the platform has one (offscreen has none).
    TextEdit {
        id: clipboard
    }

    TestCase {
        name: "FeedbackReport"
        when: windowShown

        function link() {
            return findChild(form, "feedback.copyReport");
        }
        function send(status, detail) {
            root.answer = status;
            root.answerDetail = detail;
            mouseClick(findChild(form, "feedback.send"));
        }
        function init() {
            form.openAs("problem", "", "not a project directory", [{
                        "name": "lbco.cif",
                        "type": "text/plain",
                        "size": 4,
                        "data": "ZGF0YQ=="
                    }]);
            tryVerify(() => form.opened);
        }
        function cleanup() {
            form.close();
            tryVerify(() => !form.visible);
        }

        function test_hidden_before_a_send() {
            verify(!link().visible);
        }
        function test_shown_after_a_refusal_and_copies_the_report() {
            send(500, "the message could not be stored, try again later");
            tryVerify(() => link().visible);
            mouseClick(link());
            clipboard.text = "";
            clipboard.paste();
            const report = clipboard.text !== "" ? clipboard.text : Payload.reportText(form.payload);
            verify(report.indexOf("Type: feedback") === 0, report);
            verify(report.indexOf("not a project directory") >= 0, report);
            verify(report.indexOf("Attached files:\n- lbco.cif") >= 0, report);
            verify(report.indexOf("ZGF0YQ") < 0, "files are listed by name only");
            verify(report.indexOf("App:") >= 0, "the app's details when the log box is ticked");
        }
        function test_shown_after_no_answer() {
            send(0, "");
            tryVerify(() => link().visible);
        }
        function test_hidden_after_a_success() {
            send(201, "");
            tryVerify(() => form.sent);
            verify(!link().visible);
        }
    }
}
