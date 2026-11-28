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
// cells. Choosing one opens the magnetic symmetry popup with that k.
AppDialog {
    id: popup
    objectName: "chart.kVectorPopup"

    property ProjectViewModel project: null
    // Find k's snapshot, taken when Find k was pressed: the search runs on its marks, and Analyse carries it on
    // to the analysis and Add.
    property var snapshot: ({})
    readonly property var markedPeaks: snapshot.marks ?? []

    property var rows: []
    // The chosen row: the first when the search answers, then wherever the user moves it in the table, by a click on
    // any cell or by Up and Down, the app table's own selection (owner, 2026-11-27).
    // Named `current`, not `chosen`: the signal below is `chosen`, and a property of the same name hid it, so the chart
    // could not connect and the dialog never opened (owner, 2026-11-27).
    // The table's own current row, which a click, Up and Down move (the base row sets the list's currentIndex), so
    // nothing here binds it: a bound currentIndex was replaced by the first click and the choice stayed on row 1.
    readonly property int current: list.currentIndex
    // The marks show their roles under the row selected here, and only once the dialog lists its rows.
    onCurrentChanged: if (current >= 0 && current < rows.length)
        project.showKRoles(snapshot.id, rows[current].rank)
    onRowsChanged: {
        list.currentIndex = rows.length > 0 ? 0 : -1;
        Qt.callLater(() => list.forceActiveFocus());  // Up and Down move the choice at once
    }
    // The chosen k; the chart opens the analysis with it.
    // The chosen row: its k, and its rank in the search, by which the analysis names it to the project.
    signal chosen(string k, int rank)
    property bool searching: true
    property string refusal: ""

    title: qsTr("Possible propagation vectors")
    // As tall as its rows, up to the height that keeps the navigation bar and the status bar clear, centred on the
    // window as the app's other dialogs are.
    readonly property real maximumHeight: parent ? parent.height - 2 * (EaStyle.Sizes.appBarHeight + EaStyle.Sizes.fontPixelSize) : 480
    width: parent ? Math.min(Math.round(parent.width * 0.6), 760) : 700
    height: Math.round(Math.min(maximumHeight, implicitHeight))
    // Centred on whole pixels by AppDialog, as the app's other dialogs are, so its text is sharp (owner, Retina).
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
        // number marks the chosen k, a click chooses it and a double click analyses it.
        DataTable {
            id: list
            objectName: "chart.kVectors"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(contentHeight, EaStyle.Sizes.tableRowHeight * 2)
            Layout.fillHeight: true
            clip: true
            marksCurrentRow: true
            // The marker draws the base's currentRow: the row a click or the keys made current.
            currentRow: currentIndex
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
                // A press anywhere on the row makes it current, from an area over all its cells: it takes no
                // press for itself, so the cells and the double click below still get theirs.
                MouseArea {
                    objectName: `chart.kVector.${row.index}.press`
                    parent: row
                    anchors.fill: parent
                    z: 100
                    acceptedButtons: Qt.LeftButton
                    hoverEnabled: false
                    onPressed: mouse => {
                        list.currentIndex = row.index;
                        list.forceActiveFocus();
                        mouse.accepted = false;
                    }
                }
                // A click makes the row current, as a row's own click handler does (TableRow.activated), and gives
                // the table the keys; a double click analyses it.
                TapHandler {
                    onTapped: {
                        list.currentIndex = row.index;
                        list.forceActiveFocus();
                        row.activated();
                    }
                    onDoubleTapped: {
                        list.currentIndex = row.index;
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
                    id: indexedCell
                    objectName: `chart.kVector.${row.index}.indexedCell`
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("%1 of %2").arg(row.modelData.explained).arg(popup.markedPeaks.length)
                    // Hovered, every marked reflection with its role for this k: the app's check when the k indexes
                    // it, its cross when not (owner, 2026-11-27).
                    HoverHandler {
                        id: indexedHover
                    }
                    // The app's own tooltip (EaElements.ToolTip, as the table cells and toolbar buttons use): its
                    // style, and placed below the cell, or above where there is no room, never over it. It shows
                    // data, so at once whatever the tooltip level (owner, 2026-11-27).
                    EaElements.ToolTip {
                        id: indexedTip
                        objectName: `chart.kVector.${row.index}.indexed`
                        parent: indexedCell
                        requested: indexedHover.hovered
                        data: true
                        text: popup.markRoles(row.modelData).map(r => r.text).join("\n")
                        contentItem: Column {
                            spacing: Math.round(EaStyle.Sizes.fontPixelSize * 0.25)
                            Repeater {
                                model: popup.markRoles(row.modelData)
                                delegate: Row {
                                    id: roleRow
                                    required property var modelData
                                    spacing: Math.round(EaStyle.Sizes.fontPixelSize * 0.4)
                                    IconCell {
                                        width: Math.round(EaStyle.Sizes.fontPixelSize * 1.2)
                                        height: roleText.height
                                        icon: roleRow.modelData.indexed ? "check-circle" : "times-circle"
                                        iconColor: String(roleRow.modelData.indexed ? EaStyle.Colors.green : EaStyle.Colors.red)
                                    }
                                    EaElements.Label {
                                        id: roleText
                                        color: indexedTip.textColor
                                        font: indexedTip.font
                                        text: roleRow.modelData.text
                                    }
                                }
                            }
                        }
                    }
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
    }

    // Each marked reflection of row `r` in the pattern's order (by 2θ): its 2θ and role, and whether the k indexes it.
    function markRoles(r) {
        const names = {
            satellite: qsTr("satellite"),
            forbidden: qsTr("forbidden reflection"),
            allowed: qsTr("allowed reflection"),
            "": qsTr("not indexed")
        };
        const order = markedPeaks.map((p, i) => i).sort((a, b) => markedPeaks[a].x - markedPeaks[b].x);
        return order.map(i => {
            const role = r.roles[i] ?? "";
            return {
                "indexed": role !== "",
                "text": `${markedPeaks[i].x.toFixed(2)}° ${names[role] ?? role}`
            };
        });
    }

    // Analyse the chosen k: the data, links and marks the search ran on must still hold.
    function analyse() {
        if (current < 0 || current >= rows.length)
            return;
        if (!project.kSnapshotCurrent(snapshot.id)) {
            refusal = qsTr("The data, the structures or the marked peaks changed; mark the peaks again.");
            return;
        }
        const k = rows[current].k;
        const rank = rows[current].rank;
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
                enabled: popup.current >= 0 && !popup.searching
                onClicked: popup.analyse()
            }
        }
    }
}
