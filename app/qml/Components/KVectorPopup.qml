// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The k-vector popup (owner, 2026-11-27): the propagation vectors that index the peaks marked on the pattern chart,
// a short list with the commensurate special points first, and only k whose magnetic cell holds at most 24 parent
// cells (crysta ADR-0137 A2, A11). Choosing one opens the magnetic symmetry popup with that k.
AppDialog {
    id: popup
    objectName: "chart.kVectorPopup"

    property ProjectViewModel project: null
    // Find k's snapshot, taken when Find k was pressed (review 16, F4): the search runs on its marks, and Analyse
    // carries it on to the analysis and Add.
    property var snapshot: ({})
    readonly property var markedPeaks: snapshot.marks ?? []

    property var rows: []
    // The chosen row: the first when the search answers, then wherever the user moves it in the table, by a click on
    // any cell or by Up and Down, the app table's own selection (owner, 2026-11-27).
    property int chosen: -1
    onRowsChanged: {
        chosen = rows.length > 0 ? 0 : -1;
        Qt.callLater(() => list.forceActiveFocus());  // Up and Down move the choice at once
    }
    // The chosen k; the chart opens the analysis with it.
    // The chosen row: its k, and its rank in the search, by which the analysis names it to the project.
    signal chosen(string k, int rank)
    property bool searching: true
    property string refusal: ""

    title: qsTr("Possible propagation vectors")
    // As tall as its rows, up to the height that keeps the navigation bar and the status bar clear, centred on the
    // window as the app's other dialogs are (conductor seq 48).
    readonly property real maximumHeight: parent ? parent.height - 2 * (EaStyle.Sizes.appBarHeight + EaStyle.Sizes.fontPixelSize) : 480
    width: parent ? Math.min(Math.round(parent.width * 0.6), 760) : 700
    height: Math.round(Math.min(maximumHeight, implicitHeight))
    anchors.centerIn: parent
    onClosed: destroy()

    Component.onCompleted: project.findPropagationVectors(snapshot.id)

    Connections {
        target: popup.project
        // Each answer names its snapshot; this dialog settles on its own only.
        function onPropagationVectorsFound(found, id) {
            if (id !== popup.snapshot.id)
                return;
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
        function onPropagationVectorsRefused(message, id) {
            if (id !== popup.snapshot.id)
                return;
            popup.searching = false;
            popup.refusal = message;
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: AppSizes.groupContentSpacing

        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: popup.searching
            text: qsTr("Searching…")
        }
        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text !== ""
            color: EaStyle.Colors.red
            text: popup.refusal
        }
        // The ranked vectors, in the app's table (DataTable, as Excluded regions and the parameter table): the row
        // number marks the chosen k, a click chooses it and a double click analyses it (conductor seq 50).
        DataTable {
            id: list
            objectName: "chart.kVectors"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(contentHeight, EaStyle.Sizes.tableRowHeight * 2)
            Layout.fillHeight: true
            clip: true
            marksCurrentRow: true
            currentIndex: popup.chosen
            onRowActivated: row => popup.chosen = row
            sourceModel: popup.rows
            defaultInfoText: popup.searching ? qsTr("Searching…") : qsTr("No propagation vector")
            columnKinds: ["index", "short", "text", "number", "number", "text"]
            spreadColumns: [5]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {}
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Special point")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("k")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Indexed")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Worst misfit")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Magnetic cell")
                }
            }
            delegate: TableRow {
                id: row
                required property var modelData
                objectName: `chart.kVector.${row.index}`
                // A double click analyses the row; a single click is the table's own selection, so this handler
                // only listens (a passive grab).
                TapHandler {
                    onDoubleTapped: {
                        popup.chosen = row.index;
                        popup.analyse();
                    }
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: row.modelData.label === "" ? "—" : row.modelData.label
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: `(${row.modelData.k})`
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("%1 of %2").arg(row.modelData.explained).arg(popup.markedPeaks.length)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: row.modelData.misfit.toFixed(2)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: row.modelData.parentCells === 1 ? qsTr("a, b, c (same as the crystal)") : qsTr("%1 parent cells").arg(row.modelData.parentCells)
                }
            }
        }
        // The details strip, as the symmetry popup's (owner, 2026-11-27): what the chosen k explains, each marked peak in
        // the pattern's order (by 2θ) with its role, in the normal text colour.
        EaElements.Label {
            objectName: "chart.kVectorRoles"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: {
                const r = popup.rows[popup.chosen];
                if (r === undefined)
                    return "";
                const names = {
                    satellite: qsTr("satellite"),
                    forbidden: qsTr("forbidden reflection"),
                    allowed: qsTr("allowed reflection"),
                    "": qsTr("not indexed")
                };
                const order = popup.markedPeaks.map((p, i) => i).sort((a, b) => popup.markedPeaks[a].x - popup.markedPeaks[b].x);
                const point = r.label === "" ? `(${r.k})` : `${r.label} (${r.k})`;
                return qsTr("%1 explains: %2").arg(point).arg(order.map(i => `${popup.markedPeaks[i].x.toFixed(2)}° ${names[r.roles[i] ?? ""] ?? r.roles[i]}`).join(", ")) + (r.equallyGood ? qsTr(" · equally good") : "");
            }
        }
    }

    // Analyse the chosen k: the data, links and marks the search ran on must still hold (review 12, F19).
    function analyse() {
        if (chosen < 0 || chosen >= rows.length)
            return;
        if (!project.kSnapshotCurrent(snapshot.id)) {
            refusal = qsTr("The data, the structures or the marked peaks changed; mark the peaks again.");
            return;
        }
        const k = rows[chosen].k;
        const rank = rows[chosen].rank;
        close();
        chosen(k, rank);
    }

    // Cancel and the primary Analyse at the right, as the app's other dialogs place their actions.
    footer: Item {
        implicitHeight: actions.implicitHeight + 2 * EaStyle.Sizes.fontPixelSize
        Row {
            id: actions
            anchors.right: parent.right
            anchors.rightMargin: popup.rightPadding
            anchors.verticalCenter: parent.verticalCenter
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Button {
                objectName: "chart.kVectorPopup.cancel"
                fontIcon: "times"
                text: qsTr("Cancel")
                onClicked: popup.close()
            }
            EaElements.Button {
                objectName: "chart.kVectorPopup.analyse"
                fontIcon: "magnet"
                text: qsTr("Analyse")
                enabled: popup.chosen >= 0 && !popup.searching
                onClicked: popup.analyse()
            }
        }
    }
}
