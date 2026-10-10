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

    objectName: "sequentialExtract.list"
    defaultInfoText: qsTr("No extraction rules")
    sourceModel: analysis ? analysis.sequentialExtract : null

    columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", qsTr("id")), width * 0.3), Math.min(textColumnWidth("target", qsTr("target")), width * 0.4), -1, textColumnWidth("required", qsTr("required"))]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
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
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("required")
        }
    }

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index
        // The roles by the model: `id` and `required` cannot be property names.
        required property var model

        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.id
            ToolTip.text: row.model.id
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.target
            ToolTip.text: row.model.target
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.pattern
            ToolTip.text: row.model.pattern
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: row.model.required ? qsTr("yes") : qsTr("no")
        }
    }
}
