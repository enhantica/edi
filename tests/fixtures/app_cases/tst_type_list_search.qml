// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// A searchable list (edi ADR-0017 §7): the entries starting with the typed text come first, the list is as tall as the
// entries left and says when there are none, and the chosen entry is the model's own row.
Item {
    id: root

    width: 600
    height: 700

    property int rowOfSelected: 0

    SearchableComboBox {
        id: box

        objectName: "box"
        y: 40
        width: 200
        searchThreshold: 0
        noMatchText: "No type matches"
        model: ["Ac", "Ag", "Cd", "Cl", "D", "Db", "Dy", "Fe", "Gd", "H", "Nd", "Pd", "Yb"]
        currentIndex: root.rowOfSelected
        onActivated: index => root.rowOfSelected = index
    }
    SearchableComboBox {
        id: low

        y: root.height - height - 60
        width: 200
        searchThreshold: 0
        model: box.model
    }
    SignalSpy {
        id: activated
        target: box
        signalName: "activated"
    }

    TestCase {
        name: "TypeListSearch"
        when: windowShown

        function list(of) {
            return of.popup.contentItem;
        }
        function open(of) {
            root.rowOfSelected = 0;
            activated.clear();
            mouseClick(of, of.width - 10, of.height / 2);
            tryVerify(() => of.popup.opened);
            tryVerify(() => findChild(list(of), "comboBox.search")?.activeFocus === true);
        }
        function shownEntries(of) {
            const entries = [];
            const all = list(of).contentItem.children;
            for (let i = 0; i < all.length; ++i)
                if (all[i].matching === true && all[i].height > 0 && all[i].visible)
                    entries.push(all[i]);
            return entries.sort((a, b) => a.y - b.y);
        }
        function shown(of) {
            return shownEntries(of).map(entry => entry.text).join(" ");
        }
        function type(text) {
            for (const letter of text)
                keyClick(letter);
        }
        function cleanup() {
            box.popup.close();
            low.popup.close();
            tryVerify(() => !box.popup.visible && !low.popup.visible);
            compare(box.ordered, null);
        }

        function test_starting_entries_come_first() {
            open(box);
            type("d");
            tryVerify(() => shown(box) === "D Db Dy Cd Gd Nd Pd", 5000, "D Db Dy Cd Gd Nd Pd");
            type("b");
            tryVerify(() => shown(box) === "Db", 5000, "Db");
            keyClick(Qt.Key_Backspace);
            tryVerify(() => shown(box) === "D Db Dy Cd Gd Nd Pd", 5000, "D Db Dy Cd Gd Nd Pd");
            keyClick(Qt.Key_Backspace);
            tryVerify(() => shown(box) === box.model.join(" "), 5000, box.model.join(" "));
        }

        function test_a_click_picks_the_row_of_the_model_data() {
            return [
                {
                    "tag": "Dy",
                    "row": 6
                },
                {
                    "tag": "Cd",
                    "row": 2
                },
                {
                    "tag": "Pd",
                    "row": 11
                }
            ];
        }
        function test_a_click_picks_the_row_of_the_model(data) {
            open(box);
            type("d");
            tryVerify(() => shown(box) === "D Db Dy Cd Gd Nd Pd", 5000, "D Db Dy Cd Gd Nd Pd");
            const entry = shownEntries(box).find(each => each.text === data.tag);
            mouseClick(entry);
            tryVerify(() => !box.popup.visible);
            compare(activated.count, 1);
            compare(activated.signalArguments[0][0], data.row);
            compare(box.currentIndex, data.row);
            compare(box.currentText, data.tag);
            // The box still follows what it is bound to.
            root.rowOfSelected = 9;
            compare(box.currentText, "H");
        }
        function test_enter_picks_the_first_shown_data() {
            return [
                {
                    "tag": "d",
                    "picked": "D"
                },
                {
                    "tag": "y",
                    "picked": "Yb"
                },
                {
                    "tag": "b",
                    "picked": "Db"
                }
            ];
        }
        function test_enter_picks_the_first_shown(data) {
            open(box);
            type(data.tag);
            keyClick(Qt.Key_Return);
            tryVerify(() => !box.popup.visible);
            compare(activated.count, 1);
            compare(box.currentText, data.picked);
            root.rowOfSelected = 9;
            compare(box.currentText, "H");
        }
        function test_escape_keeps_the_choice() {
            open(box);
            type("d");
            keyClick(Qt.Key_Escape);
            tryVerify(() => !box.popup.visible);
            compare(activated.count, 0);
            compare(box.currentIndex, 0);
        }
        function test_the_list_follows_the_matches_and_says_when_there_are_none() {
            open(box);
            const full = box.popup.height;
            const line = findChild(list(box), "comboBox.noMatch");
            verify(!line.visible);
            type("f");
            tryVerify(() => box.popup.height < full / 2, 5000, "one entry is left");
            const one = box.popup.height;
            type("q");
            tryVerify(() => line.visible && line.height > 0);
            compare(line.text, "No type matches");
            tryVerify(() => Math.abs(box.popup.height - (list(box).headerItem.height + box.popup.topPadding + box.popup.bottomPadding)) < 1);
            verify(line.mapToItem(list(box), 0, line.height).y <= list(box).height + 1, "the line is inside the list");
            keyClick(Qt.Key_Backspace);
            tryVerify(() => !line.visible && Math.abs(box.popup.height - one) < 1);
            keyClick(Qt.Key_Backspace);
            tryVerify(() => Math.abs(box.popup.height - full) < 1);
        }
        function test_a_list_above_its_box_stays_above() {
            open(low);
            verify(low.popup.y < 0);
            type("fe");
            tryVerify(() => Math.abs(low.popup.y + low.popup.height) < 1 && low.popup.height < low.height * 4);
            verify(low.popup.y < 0);
        }
        // Text set by the program keeps the model's order: who set it finds the entry by the model's row.
        function test_text_set_by_the_program_keeps_the_rows() {
            open(box);
            type("d");
            tryVerify(() => shown(box) === "D Db Dy Cd Gd Nd Pd", 5000, "D Db Dy Cd Gd Nd Pd");
            findChild(list(box), "comboBox.search").text = "Nd";
            tryVerify(() => box.ordered === null);
            list(box).forceLayout();
            compare(list(box).itemAtIndex(10).text, "Nd");
        }
    }
}
