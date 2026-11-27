// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The k-vector popup (owner, 2026-11-27): the propagation vectors that index the peaks marked on the pattern chart,
// a short list with the commensurate special points first, and only k whose magnetic cell holds at most 24 parent
// cells (crysta ADR-0137 A2, A11). Choosing one opens the magnetic symmetry popup with that k.
AppDialog {
    id: popup
    objectName: "chart.kVectorPopup"

    property ProjectViewModel project: null
    property int structureIndex: -1
    property int experimentIndex: -1
    property var marked: []

    property var rows: []
    // The marked peaks themselves ({x, d, ...}), for each row's identities.
    property var markedPeaks: []
    // The chosen k; the chart opens the analysis with it.
    signal chosen(string k)
    property bool searching: true
    property string refusal: ""

    title: qsTr("Possible propagation vectors")
    width: parent ? Math.min(Math.round(parent.width * 0.6), 760) : 700
    height: parent ? Math.min(Math.round(parent.height * 0.6), 520) : 480
    onClosed: destroy()

    Component.onCompleted: project.findPropagationVectors(structureIndex, experimentIndex, marked)

    Connections {
        target: popup.project
        function onPropagationVectorsFound(found) {
            popup.searching = false;
            // Buildable only; special points first, each group in the engine's ranking; at most ten.
            const buildable = found.filter(r => r.verdict === "buildable");
            const special = buildable.filter(r => r.stage === 1);
            // Another k is offered only when it indexes more marked peaks than every special point does.
            const best = special.reduce((most, r) => Math.max(most, r.explained), 0);
            const other = buildable.filter(r => r.stage !== 1 && r.explained > best);
            popup.rows = special.concat(other).slice(0, 10);
            if (popup.rows.length === 0)
                popup.refusal = qsTr("No k with a magnetic cell of at most 24 parent cells indexes the marked peaks.");
        }
        function onPropagationVectorsRefused(message) {
            popup.searching = false;
            popup.refusal = message;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: EaStyle.Sizes.fontPixelSize * 0.5

        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: popup.searching ? qsTr("Searching…") : qsTr("Choose a propagation vector to analyse the magnetic symmetry it allows.")
        }
        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text !== ""
            color: EaStyle.Colors.red
            text: popup.refusal
        }
        // The columns' header, as the app's tables have one.
        Row {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: [[qsTr("Point"), 0.12], [qsTr("k"), 0.22], [qsTr("Marked peaks indexed"), 0.24], [qsTr("Worst misfit"), 0.16], [qsTr("Magnetic cell"), 0.26]]
                delegate: EaElements.Label {
                    required property var modelData
                    width: list.width * modelData[1]
                    leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                    color: EaStyle.Colors.themeForegroundMinor
                    text: modelData[0]
                }
            }
        }
        ListView {
            id: list
            objectName: "chart.kVectors"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            currentIndex: popup.rows.length > 0 ? 0 : -1
            ScrollBar.vertical: EaElements.ScrollBar {}
            model: popup.rows
            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                readonly property bool current: ListView.isCurrentItem
                objectName: `chart.kVector.${index}`
                width: list.width
                height: EaStyle.Sizes.fontPixelSize * 3.2
                color: row.current ? EaStyle.Colors.contentBackground : hover.containsMouse ? EaStyle.Colors.themeRowHovered : "transparent"
                Rectangle {
                    visible: row.current
                    width: 3
                    height: parent.height
                    color: EaStyle.Colors.themeAccent
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width
                    Row {
                        Repeater {
                            model: [[row.modelData.label === "" ? "—" : row.modelData.label, 0.12], [`(${row.modelData.k})`, 0.22], [qsTr("%1 of %2").arg(row.modelData.explained).arg(popup.marked.length), 0.24], [row.modelData.misfit.toFixed(2), 0.16], [row.modelData.parentCells === 1 ? qsTr("a, b, c (same as the crystal)") : qsTr("%1 parent cells").arg(row.modelData.parentCells), 0.26]]
                            delegate: EaElements.Label {
                                required property var modelData
                                width: list.width * modelData[1]
                                leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                                elide: Text.ElideRight
                                text: modelData[0]
                            }
                        }
                    }
                    // Each marked peak, where it is and how this k indexes it.
                    EaElements.Label {
                        width: parent.width
                        leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                        elide: Text.ElideRight
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                        color: EaStyle.Colors.themeForegroundMinor
                        text: {
                            const names = {
                                satellite: qsTr("satellite"),
                                forbidden: qsTr("forbidden reflection"),
                                allowed: qsTr("allowed reflection"),
                                "": qsTr("not indexed")
                            };
                            return popup.markedPeaks.map((p, i) => `${p.x.toFixed(2)}°: ${names[row.modelData.roles[i] ?? ""] ?? row.modelData.roles[i]}`).join(" · ") + (row.modelData.equallyGood ? qsTr(" · equally good") : "");
                        }
                    }
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: list.currentIndex = row.index
                    onDoubleClicked: {
                        list.currentIndex = row.index;
                        popup.analyse();
                    }
                }
            }
        }
    }

    // Analyse the chosen k: the data, links and marks the search ran on must still hold (review 12, F19).
    function analyse() {
        if (list.currentIndex < 0 || list.currentIndex >= rows.length)
            return;
        if (!project.propagationSearchCurrent(experimentIndex)) {
            refusal = qsTr("The data or the structures changed; mark the peaks again.");
            return;
        }
        const k = rows[list.currentIndex].k;
        close();
        chosen(k);
    }

    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "chart.kVectorPopup.analyse"
            fontIcon: "magnet"
            text: qsTr("Analyse")
            enabled: list.currentIndex >= 0 && !popup.searching
            DialogButtonBox.buttonRole: DialogButtonBox.ApplyRole
            onClicked: popup.analyse()
        }
        EaElements.Button {
            objectName: "chart.kVectorPopup.cancel"
            text: qsTr("Cancel")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
        }
    }
}
