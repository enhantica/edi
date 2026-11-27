// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The propagation vector (k) search, a group of its own (owner, 2026-11-27): the peaks marked on the pattern chart as a
// table built like Excluded regions (2θ, d, and each peak's role after a search), each row removable, and Find k and
// Clear as the group's buttons. The chart's toolbar keeps only its Mark peaks toggle; the marks belong to the chart.
SideBarGroup {
    id: group

    // The Experiment page's pattern chart (AppState.kChart), which draws the marks the project's k search holds.
    readonly property var chart: AppState.kChart
    readonly property bool marking: chart !== null && chart.peakMode
    // The marked peaks in the pattern's order, each with its index in the chart's candidates.
    readonly property var rows: {
        if (!marking)
            return [];
        const out = chart.peakMarks.map(i => ({
                    "index": i,
                    "peak": chart.peakCandidates[i]
                })).filter(r => r.peak !== undefined);
        out.sort((a, b) => a.peak.x - b.peak.x);
        return out;
    }

    readonly property string openKey: "Basic:k_search"
    pinKey: openKey
    objectName: "group.k_search"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: group.marking ? qsTr("Propagation vector (k) search (%1)").arg(group.rows.length) : qsTr("Propagation vector (k) search")
    icon: "magnet"

    Column {
        width: parent ? parent.width : 0
        spacing: AppSizes.groupContentSpacing

        // The group starts with this toggle alone (owner decision 2026-11-27); on, the marked peaks, Find k and Clear
        // follow. While it is on, a click on the pattern marks a peak and a click on a mark drops it.
        EaElements.SideBarButton {
            objectName: "kSearch.mark"
            fontIcon: "magnet"
            text: group.marking ? qsTr("Stop marking peaks") : qsTr("Mark peaks")
            checkable: true
            checked: group.marking
            enabled: group.chart !== null
            onClicked: group.chart.setPeakMode(!group.marking)
        }

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
            visible: group.marking
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
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
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

        Row {
            visible: group.marking
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.SideBarButton {
                objectName: "kSearch.findK"
                fontIcon: "search"
                text: qsTr("Find k")
                enabled: group.marking && group.chart.peakMarks.length > 0
                onClicked: group.chart.openKVectors()
            }
            EaElements.SideBarButton {
                objectName: "kSearch.clear"
                fontIcon: "eraser"
                text: qsTr("Clear")
                enabled: group.marking && group.chart.peakMarks.length > 0
                onClicked: group.chart.axisProject.clearKMarks()
            }
        }
    }
}
