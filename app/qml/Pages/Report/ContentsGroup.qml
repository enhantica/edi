// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What the report holds (the owner's note 31): its sections, all or only the free parameters, and the correlation
// level (automatic: the five most correlated parameters, as the Correlations tab).
EaElements.GroupBox {
    id: group

    // Only the top group opens on first view, as on the other pages; each remembers its state.
    readonly property string openKey: "Main:reportContents"
    property ReportViewModel report: null
    readonly property var sectionNames: ["summary", "analysis", "parameters", "correlations", "evolution", "structures", "experiments"]
    readonly property var sectionTitles: [qsTr("Project summary"), qsTr("Analysis"), qsTr("Parameters"), qsTr("Correlations"), qsTr("Evolution"), qsTr("Structures"), qsTr("Experiments")]

    function toggle(name, on) {
        const chosen = group.report.sections.filter(section => section !== name);
        if (on)
            chosen.push(name);
        group.report.sections = chosen;
    }

    objectName: "group.reportContents"
    title: qsTr("Contents")
    icon: "list"
    collapsed: !SideBarGroups.isOpen(openKey)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed)
    last: SideBarGroups.isLast(group)
    enabled: report !== null

    Column {
        spacing: AppSizes.groupContentSpacing

        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: 0
            Repeater {
                model: group.sectionNames.length
                delegate: EaElements.CheckBox {
                    required property int index
                    objectName: "report.section." + group.sectionNames[index]
                    width: (EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize) / 2
                    text: group.sectionTitles[index]
                    checked: group.report ? group.report.sections.indexOf(group.sectionNames[index]) >= 0 : true
                    onToggled: group.toggle(group.sectionNames[index], checked)
                }
            }
        }
        EaElements.GroupRow {
            spacing: AppSizes.inputSpacing
            EaElements.ComboBox {
                objectName: "report.parameters"
                width: (EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing) / 2
                model: [qsTr("All parameters"), qsTr("Free parameters")]
                currentIndex: group.report && group.report.freeParametersOnly ? 1 : 0
                onActivated: index => group.report.freeParametersOnly = index === 1
            }
            EaElements.ComboBox {
                objectName: "report.correlationLevel"
                width: (EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing) / 2
                // The level, from automatic up to the strongest correlations only.
                readonly property var levels: [-1, 0.5, 0.7, 0.8, 0.9, 0.95]
                model: [qsTr("Correlations: 5 strongest"), qsTr("Correlations ≥ 0.5"), qsTr("Correlations ≥ 0.7"), qsTr("Correlations ≥ 0.8"), qsTr("Correlations ≥ 0.9"), qsTr("Correlations ≥ 0.95")]
                currentIndex: !group.report || group.report.automaticLevel ? 0 : Math.max(0, levels.indexOf(group.report.correlationLevel))
                onActivated: index => {
                    if (index === 0) {
                        group.report.automaticLevel = true;
                    } else {
                        group.report.correlationLevel = levels[index];
                    }
                }
            }
        }
    }
}
