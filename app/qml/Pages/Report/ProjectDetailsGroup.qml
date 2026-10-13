// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The report's project details (the owner's note 31): the title, the authors and the description, saved in the
// project (`project.edi` `_metadata`), each an edit that Undo reverts.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    objectName: "group.reportProjectDetails"
    title: qsTr("Project details")
    icon: "id-card"
    collapsed: false
    last: SideBarGroups.isLast(group)

    component DetailField: EaElements.TextField {
        width: EaStyle.Sizes.sideBarContentWidth
        horizontalAlignment: TextInput.AlignLeft
        enabled: group.project !== null
    }

    Column {
        spacing: AppSizes.groupContentSpacing

        DetailField {
            objectName: "report.details.title"
            placeholderText: qsTr("Title")
            text: group.project ? group.project.title : ""
            onEditingFinished: if (group.project && text !== group.project.title)
                group.project.title = text
        }
        DetailField {
            objectName: "report.details.authors"
            placeholderText: qsTr("Authors, separated by ;")
            text: group.project ? group.project.authors : ""
            onEditingFinished: if (group.project && text !== group.project.authors)
                group.project.authors = text
        }
        DetailField {
            objectName: "report.details.description"
            placeholderText: qsTr("Description")
            text: group.project ? group.project.description : ""
            onEditingFinished: if (group.project && text !== group.project.description)
                group.project.description = text
        }
    }
}
