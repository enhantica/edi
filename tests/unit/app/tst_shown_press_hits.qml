// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import ReportAcceptance 1.0
import EdiAcceptance 1.0
import "NativeTurn.js" as Turn

Item {
    width: 600
    height: 500
    Rectangle {
        width: 104; height: 38; x: 30; y: 34
        color: "#eeeeee"
        MouseArea {
            id: button
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: test.hits += 1
        }
    }
    Component {
        id: shield
        Item {
            property bool covers: false
            Rectangle { anchors.fill: parent; color: "#224455"; opacity: .2 }
            MouseArea {
                anchors.fill: parent
                enabled: parent.covers
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onPressed: test.coverHits += 1
            }
        }
    }
    ComboBox {
        id: chooser
        x: 30; y: 90; width: 220
        model: ["First phase", "Second phase"]
        property bool searchable: true
        property string searchText: ""
        delegate: ItemDelegate {
            required property string modelData
            width: chooser.width
            text: modelData
            onPressed: test.hits += 1
        }
        popup: Popup {
            y: chooser.height
            width: chooser.width
            height: 160
            contentItem: ListView {
                id: options
                model: chooser.delegateModel
                header: Item {
                    width: chooser.width; height: 30
                    TextInput {
                        id: search
                        objectName: "comboBox.search"
                        anchors.fill: parent
                        onTextChanged: chooser.searchText = text
                        onActiveFocusChanged: if (activeFocus) test.hits += 1
                    }
                }
            }
        }
    }
    TestCase {
        id: test
        name: "ShownPressHits"
        when: windowShown
        property int hits: 0
        property int coverHits: 0
        property string permit
        property var layers: []
        function init() {
            permit = Turn.begin(test, Probe);
            hits = coverHits = 0;
            chooser.currentIndex = 0;
        }
        function cleanup() {
            chooser.popup.close();
            for (const layer of layers) {
                if (Qt.isQtObject(layer))
                    layer.destroy();
            }
            layers = [];
            Turn.end(permit);
        }
        function test_native_hit_data() {
            const rows = [];
            for (const route of ["navigate", "context", "row", "search"])
                for (const covered of [false, true])
                    rows.push({tag: route + (covered ? "-cover" : "-decoration"), route, covered});
            return rows.sort((a, b) => a.tag < b.tag ? -1 : 1);
        }
        function test_native_hit(data) {
            const popup = data.route === "search" || data.route === "row";
            const search = () => findChild(options.headerItem, "comboBox.search");
            const maskTarget = () => !popup ? button : data.route === "search" ? search() : options.itemAtIndex(1);
            const buttonType = data.route === "context" ? Qt.RightButton : Qt.LeftButton;
            function cover(target) {
                const layer = shield.createObject(target.parent, {
                    x: target.x, y: target.y, width: target.width, height: target.height,
                    z: target.z + 5, covers: data.covered
                });
                layers.push(layer);
                if (data.covered)
                    SettingsProof.putBeforeInChildList(layer, target);
                return layer;
            }
            if (popup) {
                chooser.popup.open();
                tryVerify(() => chooser.popup.opened && maskTarget(), 3000,
                          "Qt opens the original popup and exposes the named target for the human control");
            }
            let layer = cover(maskTarget());
            const manual = maskTarget();
            const initial = hits;
            mouseClick(manual, manual.width / 2, manual.height / 2, buttonType);
            compare(coverHits, data.covered ? 1 : 0, "Qt's ordinary window dispatch identifies the covering input");
            compare(hits, initial + (data.covered ? 0 : 1), "Qt delivers an ordinary press through decoration");
            layer.visible = false;
            layer.destroy();
            if (popup) {
                chooser.popup.close();
                tryCompare(chooser.popup, "visible", false, 3000, "The human control's popup closes before replay");
                chooser.currentIndex = 0;
                search().clear();
            }
            hits = coverHits = 0;
            const result = SettingsProof.shownPress(popup ? chooser : button, data.route, count => {
                if (count === (popup ? 2 : 1))
                    layer = cover(maskTarget());
            });
            verify(result.completed && result.cues >= (popup ? 2 : 1),
                   "The production input driver reaches the requested press boundary");
            compare(coverHits, 0, "The assistant never presses the unrelated covering surface");
            compare(result.delivered, !data.covered,
                    "The assistant accepts the target Qt can reach and refuses the genuinely covered target");
            if (!data.covered) {
                verify(hits > 0, "A delivered press actually reaches the Qt-selected target");
                if (popup)
                    compare(chooser.currentIndex, 1, "The original popup settles the requested offered option");
            }
        }
    }
}
