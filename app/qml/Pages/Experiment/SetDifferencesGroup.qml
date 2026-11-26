// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Differences (edi ADR-0087 point 2): for each experiment set, the values each member holds that differ from the set's
// template, read again when the group opens and after each edit; nothing about them is stored. Shown only while the
// project has a set.
SideBarGroup {
    id: group

    property ProjectViewModel project: null
    property var rows: []
    property bool hasSets: false
    function refresh() {
        hasSets = project !== null && project.experimentSetCount() > 0;
        rows = hasSets && !collapsed ? project.setDifferences() : [];
    }
    Component.onCompleted: refresh()

    objectName: "group.setDifferences"
    title: qsTr("Differences from the template (%1)").arg(rows.length)
    visible: hasSets
    collapsed: true
    onCollapsedChanged: refresh()
    Connections {
        target: group.project
        function onEdited() {
            group.refresh();
        }
        function onPathChanged() {
            group.refresh();
        }
    }

    Column {
        width: EaStyle.Sizes.sideBarContentWidth
        spacing: AppSizes.groupContentSpacing

        EaElements.Label {
            visible: group.rows.length === 0
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("Every member has the template's values.")
        }
        Repeater {
            model: group.rows
            delegate: EaElements.Label {
                required property var modelData
                width: parent.width
                elide: Text.ElideRight
                text: qsTr("%1 · %2: %3 (template %4)").arg(modelData.member).arg(modelData.path)
                          .arg(NumberText.compact(String(Number(modelData.value.toPrecision(6)))))
                          .arg(NumberText.compact(String(Number(modelData.template.toPrecision(6)))))
            }
        }
    }
}
