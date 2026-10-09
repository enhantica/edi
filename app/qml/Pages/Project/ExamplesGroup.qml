// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Examples (easydiffractionbeta Pages/Project/SideBarBasic/Examples.qml): every project of edi's CLI
// registry, then the app's X-ray example; a row opens its project.
EaElements.GroupBox {
    icon: "database"
    objectName: "group.examples"
    title: qsTr("Examples")

    // A Column gives the group its content height (a ListView has no implicit height).
    Column {
        DataTable {
            id: tableView

            columnWidths: [numberColumnWidth, -1]
            defaultInfoText: qsTr("No examples available")
            maxRowCountShow: 6
            model: Session.examples
            objectName: "examples.list"
            tallRows: true

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property string description
                required property string exampleId
                required property int index
                required property string name

                objectName: `examples.open.${exampleId}`

                TapHandler {
                    onTapped: Session.openExample(row.exampleId)
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                EaComponents.TableViewTwoRowsAdvancedLabel {
                    ToolTip.text: row.exampleId
                    fontIcon: "archive"
                    minorText: row.description
                    text: row.name
                }
            }
            header: EaComponents.ListViewHeader {
                implicitHeight: 0
                visible: false

                EaComponents.TableViewLabel {
                    enabled: false
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name / description")
                }
            }
        }
    }
}
