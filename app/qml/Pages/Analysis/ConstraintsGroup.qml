// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `constraint`: each constraint as declared, `<alias> = <expression>`, read-only like the aliases. A loop
// in `.edi`, so a table.
EaComponents.TableView {
    id: table

    property AnalysisViewModel analysis: null

    objectName: "constraints.list"
    defaultInfoText: qsTr("No constraints")
    model: analysis ? analysis.constraints : null

    header: EaComponents.TableViewHeader {
        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
            text: qsTr("No.")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 8
            horizontalAlignment: Text.AlignLeft
            text: qsTr("id")
        }
        EaComponents.TableViewLabel {
            flexibleWidth: true
            horizontalAlignment: Text.AlignLeft
            text: qsTr("expression")
        }
    }

    delegate: EaComponents.TableViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` cannot be a property name.
        required property var model

        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 8
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.id
            ToolTip.text: row.model.id
        }
        EaComponents.TableViewLabel {
            width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.expression
            ToolTip.text: row.model.expression
        }
    }
}
