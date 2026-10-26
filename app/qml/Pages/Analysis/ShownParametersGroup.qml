// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Which values the Analysis table lists besides those a fit can free (edi ADR-0053 §7): one box per reason a value
// cannot be fitted, each with how many such values are fixed. A value marked free is always listed. A setting of this
// user, not part of the project, so it is on the page's Settings tab (edi ADR-0031 §2).
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    readonly property string openKey: "Settings:shownParameters"
    readonly property var counts: project ? project.parameters.groupCounts : [0, 0, 0, 0]
    readonly property real boxWidth: (EaStyle.Sizes.sideBarContentWidth - grid.columnSpacing) / 2

    objectName: "group.shownParameters"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    title: qsTr("Parameters shown")
    icon: "filter"

    component ShowBox: EaElements.CheckBox {
        width: group.boxWidth
        leftPadding: 0
    }

    // In ParameterItem.FitGroup's order, two to a row.
    Grid {
        id: grid

        columns: 2
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        ShowBox {
            objectName: "analysis.show.notMeasured"
            text: qsTr("Not measured in this fit (%1)").arg(group.counts[0])
            checked: Preferences.analysisShowNotMeasured
            onToggled: Preferences.analysisShowNotMeasured = checked
            ToolTip.text: qsTr("Values this fit's data cannot determine, or the fit cannot vary yet")
        }
        ShowBox {
            objectName: "analysis.show.bySymmetry"
            text: qsTr("Fixed by symmetry (%1)").arg(group.counts[1])
            checked: Preferences.analysisShowBySymmetry
            onToggled: Preferences.analysisShowBySymmetry = checked
            ToolTip.text: qsTr("Values the space group fixes or ties to another value")
        }
        ShowBox {
            objectName: "analysis.show.byConstraint"
            text: qsTr("Set by a constraint (%1)").arg(group.counts[2])
            checked: Preferences.analysisShowByConstraint
            onToggled: Preferences.analysisShowByConstraint = checked
            ToolTip.text: qsTr("Values one of your constraints computes from others")
        }
        ShowBox {
            objectName: "analysis.show.fixedSettings"
            text: qsTr("Fixed settings (%1)").arg(group.counts[3])
            checked: Preferences.analysisShowFixedSettings
            onToggled: Preferences.analysisShowFixedSettings = checked
            ToolTip.text: qsTr("Values that describe the setup and are never fitted")
        }
    }
}
