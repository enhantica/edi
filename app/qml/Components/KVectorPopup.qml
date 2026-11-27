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
    // The magnetic popup opened from here added `count` structures (the chart says so).
    signal added(int count)
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
            const other = buildable.filter(r => r.stage !== 1);
            popup.rows = special.concat(other).slice(0, 10);
            if (popup.rows.length === 0)
                popup.refusal = qsTr("No k with a magnetic cell of at most 24 parent cells indexes the marked peaks.");
        }
        function onPropagationVectorsRefused(message) {
            popup.searching = false;
            popup.refusal = message;
        }
    }

    Component {
        id: magneticPopupComponent
        MagneticPopup {}
    }

    ColumnLayout {
        width: popup.availableWidth
        height: popup.availableHeight
        spacing: EaStyle.Sizes.fontPixelSize * 0.5

        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: popup.searching ? qsTr("Searching %n marked peak(s)…", "", popup.marked.length) : qsTr("%n marked peak(s). Choose a k to analyse its magnetic symmetry.", "", popup.marked.length)
        }
        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text !== ""
            color: EaStyle.Colors.red
            text: popup.refusal
        }
        ListView {
            id: list
            objectName: "chart.kVectors"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar {}
            model: popup.rows
            delegate: Rectangle {
                id: row
                required property var modelData
                required property int index
                objectName: `chart.kVector.${index}`
                width: list.width
                height: EaStyle.Sizes.fontPixelSize * 2.6
                color: hover.hovered ? EaStyle.Colors.themeRowHovered : "transparent"
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    x: EaStyle.Sizes.fontPixelSize * 0.5
                    EaElements.Label {
                        font.bold: true
                        text: row.modelData.label === "" ? `k = (${row.modelData.k})` : `${row.modelData.label}  k = (${row.modelData.k})`
                    }
                    EaElements.Label {
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                        text: {
                            const roles = row.modelData.roles;
                            const forbidden = roles.filter(r => r === "forbidden").length;
                            const satellite = roles.filter(r => r === "satellite").length;
                            const allowed = roles.filter(r => r === "allowed").length;
                            const parts = [];
                            if (forbidden > 0)
                                parts.push(qsTr("%n at forbidden reflections", "", forbidden));
                            if (satellite > 0)
                                parts.push(qsTr("%n as satellites", "", satellite));
                            if (allowed > 0)
                                parts.push(qsTr("%n on allowed reflections", "", allowed));
                            return qsTr("indexes %1 of %2 marked peaks (%3) · worst misfit %4 · magnetic cell %5").arg(row.modelData.explained).arg(popup.marked.length).arg(parts.join(", ")).arg(row.modelData.parentCells === 1 ? qsTr("the crystal's") : qsTr("%1 parent cells").arg(row.modelData.parentCells)) + (row.modelData.equallyGood ? qsTr(" · equally good") : "");
                        }
                    }
                }
                HoverHandler {
                    id: hover
                }
                TapHandler {
                    onTapped: {
                        const next = magneticPopupComponent.createObject(Overlay.overlay, {
                            project: popup.project,
                            structureIndex: popup.structureIndex,
                            structure: popup.project.structureAt(popup.structureIndex),
                            initialK: row.modelData.k,
                            selectAfterAdd: false
                        }) as MagneticPopup;
                        next.added.connect(count => popup.added(count));
                        popup.close();
                        next.open();
                    }
                }
            }
        }
        RowLayout {
            Item {
                Layout.fillWidth: true
            }
            EaElements.Button {
                objectName: "chart.kVectorPopup.cancel"
                text: qsTr("Cancel")
                onClicked: popup.close()
            }
        }
    }
}
