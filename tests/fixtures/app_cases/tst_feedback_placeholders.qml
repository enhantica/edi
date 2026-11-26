// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The feedback form's placeholders are shown whole: none is wider than its field.
Item {
    id: root

    width: 1200
    height: 900

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
    }
    FontMetrics {
        id: metrics
    }

    TestCase {
        name: "FeedbackPlaceholders"
        when: windowShown

        function cleanup() {
            form.close();
            tryVerify(() => !form.visible);
        }
        function test_placeholders_fit_data() {
            return ["feedback.name", "feedback.email", "feedback.affiliation", "feedback.text"].map(name => ({
                        "tag": name
                    }));
        }
        function test_placeholders_fit(data) {
            form.open();
            tryVerify(() => form.opened);
            const field = findChild(form, data.tag);
            metrics.font = field.font;
            const room = field.width - field.leftPadding - field.rightPadding;
            for (const line of field.placeholderText.split("\n"))
                verify(metrics.advanceWidth(line) <= room, `${line}: ${metrics.advanceWidth(line)} of ${room}`);
            const drawn = Array.from(field.children).find(child => child.text === field.placeholderText);
            verify(drawn && drawn.visible);
            compare(drawn.truncated, false);
            compare(drawn.lineCount, field.placeholderText.split("\n").length);
        }
    }
}
