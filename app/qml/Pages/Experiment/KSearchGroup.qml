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

    // The Experiment page's pattern chart, which holds the marks (AppState.kChart).
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

        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            visible: text !== ""
            color: group.marking && group.chart.peakNote !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForegroundMinor
            text: !group.marking ? qsTr("Turn on Mark peaks in the pattern's toolbar, then click the peaks a magnetic structure should explain.") : group.chart.peakNote
        }

        DataTable {
            objectName: "kSearch.list"
            visible: group.marking
            defaultInfoText: qsTr("No peaks marked yet")
            sourceModel: group.rows
            columnKinds: ["index", "number", "number", -1, "control"]

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

                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `kSearch.x.${row.index}`
                    text: row.modelData.peak.x.toFixed(2)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: row.modelData.peak.d.toFixed(4)
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    // After a search, the role the best-ranked k gives this peak.
                    text: {
                        const names = {
                            satellite: qsTr("satellite"),
                            forbidden: qsTr("forbidden reflection"),
                            allowed: qsTr("allowed reflection"),
                            "": qsTr("not indexed")
                        };
                        const role = group.chart.peakRoles[row.modelData.index];
                        return role === undefined ? (row.modelData.peak.suggestion ? qsTr("added by hand") : qsTr("pre-marked")) : names[role] ?? role;
                    }
                }
                EaComponents.ListViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `kSearch.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Drop this peak")
                    onClicked: group.chart.peakMarks = group.chart.peakMarks.filter(i => i !== row.modelData.index)
                }
            }
        }

        Row {
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
                onClicked: group.chart.peakMarks = []
            }
        }
    }
}
