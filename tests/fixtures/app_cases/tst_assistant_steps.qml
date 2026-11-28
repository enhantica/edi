// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The finished steps between two replies of the assistant as one line (edi ADR-0057): it names their number and draws
// each kind's icon once, keeps its text in a narrow panel, and a click asks for the other state, which the model holds.
TestCase {
    id: test

    name: "AssistantSteps"
    when: windowShown
    width: 600
    height: 200
    visible: true

    Component {
        id: lineComponent

        AssistantSteps {
            width: 400
        }
    }
    SignalSpy {
        id: toggled

        signalName: "toggled"
    }

    function line(count, open, icons) {
        const made = createTemporaryObject(lineComponent, test);
        verify(made !== null);
        made.payload = {
            "type": "ediSteps",
            "group": "first",
            "open": open,
            "icons": icons ?? ["success"],
            "count": count
        };
        toggled.target = made;
        toggled.clear();
        waitForRendering(made);
        return made;
    }

    function test_a_names_its_steps() {
        const made = line(3, false);
        compare(made.icons.length, 1);
        compare(findChild(made, "assistant.steps.toggle").text, "3 steps");
        verify(made.implicitHeight > 0);
    }
    function test_e_each_kind_shows_its_icon_once() {
        const made = line(4, false, ["success", "success", "failed", "success"]);
        compare(made.icons, ["success", "failed"]);
        compare(findChild(made, "assistant.steps.toggle").text, "4 steps");
    }
    function test_b_a_click_asks_for_the_other_state() {
        const data = [[false, true], [true, false]];
        for (const [open, wanted] of data) {
            const made = line(2, open);
            mouseClick(findChild(made, "assistant.steps.toggle"));
            compare(toggled.count, 1);
            compare(toggled.signalArguments[0][0], "first");
            compare(toggled.signalArguments[0][1], wanted);
        }
    }
    function test_c_a_narrow_line_keeps_its_height() {
        const made = line(80, false);
        const height = made.implicitHeight;
        made.width = 120;
        waitForRendering(made);
        compare(made.implicitHeight, height);
        compare(findChild(made, "assistant.steps.toggle").text, "80 steps");
    }
    function test_d_a_row_of_another_kind_shows_nothing() {
        const made = line(2, true);
        made.payload = undefined;
        compare(made.icons.length, 0);
        verify(!made.open);
    }
}
