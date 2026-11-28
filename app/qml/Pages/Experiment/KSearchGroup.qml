// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The propagation vector (k) search, a group of its own, laid out like Excluded regions (owner decision 2026-11-27): the
// marked peaks' table always shown (2θ, d, and each peak's role after a search), each row removable and all of them
// by the remove column's header button, then Mark peaks and Find k below it. The marks belong to the chart.
SideBarGroup {
    id: group

    // The Experiment page's pattern chart (AppState.kChart), which draws the marks the project's k search holds.
    readonly property var chart: AppState.kChart
    readonly property bool marking: chart !== null && chart.peakMode
    // The marked peaks in the pattern's order, each with its index in the chart's candidates.
    readonly property var rows: {
        if (chart === null)
            return [];
        const out = chart.peakMarks.map(i => ({
                    "index": i,
                    "peak": chart.peakCandidates[i]
                })).filter(r => r.peak !== undefined);
        out.sort((a, b) => a.peak.x - b.peak.x);
        return out;
    }

    readonly property string openKey: "Extras:k_search"
    pinKey: openKey
    objectName: "group.k_search"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: group.rows.length > 0 ? qsTr("k-vector search (%1)").arg(group.rows.length) : qsTr("k-vector search")
    icon: "magnet"

    Column {
        width: parent ? parent.width : 0
        spacing: AppSizes.groupContentSpacing

        // Only when marking cannot start here: several crystal structures, or none, linked to the experiment.
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            visible: group.marking && text !== ""
            color: EaStyle.Colors.themeForegroundMinor
            text: group.marking ? group.chart.peakNote : ""
        }

        DataTable {
            objectName: "kSearch.list"
            // Empty and disabled until a peak is marked.
            enabled: group.rows.length > 0
            defaultInfoText: qsTr("No peaks marked yet")
            sourceModel: group.rows
            columnKinds: ["index", "number", "number", "text", "control"]
            // The role takes the room left, as the last value column of the app's sidebar tables does.
            spreadColumns: [3]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("2θ (°)")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("d (Å)")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Role")
                }
                // Above the remove column, the button that removes them all.
                EaComponents.ListViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: "kSearch.clear"
                    fontIcon: "minus-circle"
                    enabled: group.rows.length > 0
                    ToolTip.text: qsTr("Remove all marked peaks")
                    onClicked: group.chart.axisProject.clearKMarks()
                    // The header's own MouseArea, over its row of cells, takes every header click for the list's
                    // focus; this row goes above it so the button gets its click, while the labels, which take no
                    // clicks, still let theirs through (review 28).
                    Component.onCompleted: if (parent) parent.z = 1
                }
            }

            delegate: TableRow {
                id: row

                required property var modelData
                // The row and its line on the chart highlight together (owner, 2026-11-27): hovering the row marks the
                // line, and a hovered line shows its row in the current-row blue.
                readonly property bool lineHovered: group.chart !== null && group.chart.hoveredMark === row.modelData.index
                readonly property color textColor: lineHovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                HoverHandler {
                    onHoveredChanged: {
                        if (group.chart === null)
                            return;
                        if (hovered)
                            group.chart.hoveredMark = row.modelData.index;
                        else if (group.chart.hoveredMark === row.modelData.index)
                            group.chart.hoveredMark = -1;
                    }
                }

                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `kSearch.x.${row.index}`
                    color: row.textColor
                    text: row.modelData.peak.x.toFixed(2)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: row.textColor
                    text: row.modelData.peak.d.toFixed(4)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    color: row.textColor
                    // Once the k dialog lists its rows, the role its selected row gives this peak.
                    text: {
                        const names = {
                            satellite: qsTr("satellite"),
                            forbidden: qsTr("forbidden reflection"),
                            allowed: qsTr("allowed reflection"),
                            "": qsTr("not indexed")
                        };
                        const role = group.chart.peakRoles[row.modelData.index];
                        // Before a search: why the peak is marked, a suggestion's reason or the user's own mark.
                        const peak = row.modelData.peak;
                        if (role === undefined)
                            return !peak.suggested ? qsTr("added by hand") : peak.onAllowed ? qsTr("excess on an allowed reflection") : qsTr("forbidden reflection");
                        return names[role] ?? role;
                    }
                }
                EaComponents.ListViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `kSearch.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Drop this peak")
                    onClicked: group.chart.axisProject.removeKMark(row.modelData.index)
                }
            }
        }

        // While marking, a click on the pattern marks a peak and a click on a mark drops it.
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.SideBarButton {
                objectName: "kSearch.mark"
                fontIcon: "magnet"
                text: group.marking ? qsTr("Stop marking") : qsTr("Mark peaks")
                checkable: true
                checked: group.marking
                enabled: group.chart !== null
                onClicked: group.chart.setPeakMode(!group.marking)
            }
            EaElements.SideBarButton {
                objectName: "kSearch.findK"
                fontIcon: "search"
                text: qsTr("Find k")
                enabled: group.chart !== null && group.chart.peakMarks.length > 0
                onClicked: group.chart.openKVectors()
            }
        }
    }
}
