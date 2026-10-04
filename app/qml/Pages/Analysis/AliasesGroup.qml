// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `alias`: the short names constraints use, each with the parameter it stands for, read-only (aliases
// are declared in the file or from Python). A loop in `.edi`, so a table.
EaComponents.TableView {
    id: table

    property AnalysisViewModel analysis: null

    objectName: "aliases.list"
    defaultInfoText: qsTr("No aliases")
    model: analysis ? analysis.aliases : null

    header: EaComponents.TableViewHeader {
        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
            text: qsTr("No.")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 8
            horizontalAlignment: Text.AlignLeft
            text: qsTr("alias")
        }
        EaComponents.TableViewLabel {
            flexibleWidth: true
            horizontalAlignment: Text.AlignLeft
            text: qsTr("parameter")
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
            elide: Text.ElideMiddle
            text: row.model.parameter
            ToolTip.text: row.model.parameter
        }
    }
}
