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
DataTable {
    id: table

    property AnalysisViewModel analysis: null

    columnWidths: [numberColumnWidth, EaStyle.Sizes.fontPixelSize * 5, EaStyle.Sizes.fontPixelSize * 9, -1, EaStyle.Sizes.fontPixelSize * 4]
    defaultInfoText: qsTr("No extraction rules")
    model: analysis ? analysis.sequentialExtract : null
    objectName: "sequentialExtract.list"

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` and `required` cannot be property names.
        required property var model

        EaComponents.TableViewLabel {
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
            text: row.model.id
        }
        EaComponents.TableViewLabel {
            ToolTip.text: row.model.target
            elide: Text.ElideMiddle
            horizontalAlignment: Text.AlignLeft
            text: row.model.target
        }
        EaComponents.TableViewLabel {
            ToolTip.text: row.model.pattern
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
            text: row.model.pattern
        }
        EaComponents.TableViewLabel {
            text: row.model.required ? qsTr("yes") : qsTr("no")
        }
    }
    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: qsTr("id")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: qsTr("target")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: qsTr("pattern")
        }
        EaComponents.TableViewLabel {
            text: qsTr("required")
        }
    }
}
