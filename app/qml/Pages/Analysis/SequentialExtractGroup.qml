// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `sequential_fit_extract`: the scan's extraction rules — each a pattern read from a scan file into a
// results column — read-only, as the scan declaration is (scanning is E05). A loop in `.edi`, so a
// table.
EaComponents.TableView {
    id: table

    property AnalysisViewModel analysis: null

    objectName: "sequentialExtract.list"
    defaultInfoText: qsTr("No extraction rules")
    model: analysis ? analysis.sequentialExtract : null

    header: EaComponents.TableViewHeader {
        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 5
            horizontalAlignment: Text.AlignLeft
            text: qsTr("id")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 9
            horizontalAlignment: Text.AlignLeft
            text: qsTr("target")
        }
        EaComponents.TableViewLabel {
            flexibleWidth: true
            horizontalAlignment: Text.AlignLeft
            text: qsTr("pattern")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 4
            text: qsTr("required")
        }
    }

    delegate: EaComponents.TableViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` and `required` cannot be property names.
        required property var model

        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 5
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.id
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 9
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.target
            ToolTip.text: row.model.target
        }
        EaComponents.TableViewLabel {
            width: table.headerLabelItems.length > 3 ? table.headerLabelItems[3].width : 0
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.pattern
            ToolTip.text: row.model.pattern
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 4
            text: row.model.required ? qsTr("yes") : qsTr("no")
        }
    }
}
