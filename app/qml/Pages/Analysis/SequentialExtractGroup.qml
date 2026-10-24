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
    // These text-only columns can share more room than numeric parameter tables.
    maximumTextColumnShare: 0.4
    sourceModel: analysis ? analysis.sequentialExtract : null

    columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", Session.label("sequential_fit_extract.id")), width * 0.3), Math.min(textColumnWidth("target", Session.label("sequential_fit_extract.target")), width * 0.4), -1, AppSizes.iconOnlyColumnWidth]

    header: EaComponents.ListViewHeader {
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignLeft
            uid: "sequential_fit_extract.id"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignLeft
            uid: "sequential_fit_extract.target"
        }
        HeaderLabel {
            horizontalAlignment: Text.AlignLeft
            uid: "sequential_fit_extract.pattern"
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
    }

    delegate: TableRow {
        id: row

        // The roles by the model: `id` and `required` cannot be property names.
        required property var model

        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignHCenter
            marksCurrentRow: true
            text: row.index + 1
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.id
            ToolTip.text: row.model.id
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.target
            ToolTip.text: row.model.target
        }
        EaComponents.ListViewLabel {
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            text: row.model.pattern
            ToolTip.text: row.model.pattern
        }
        // Whether the rule is required, as the Linked structures table's enable toggle shows its state (the owner,
        // 2026-10-11); read-only, as the rule is.
        IconCell {
            horizontalAlignment: Text.AlignHCenter
            objectName: `sequentialExtract.required.${row.index}`
            icon: row.model.required ? "toggle-on" : "toggle-off"
            iconColor: String(EaStyle.Colors.themeForeground)
            toolTip: row.model.required ? qsTr("Required: a dataset whose file has no match for this pattern fails") : qsTr("Not required: a dataset whose file has no match leaves this column empty")
        }
    }
}
