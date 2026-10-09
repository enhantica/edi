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
    objectName: "group.examples"
    title: qsTr("Examples")
    icon: "database"

    // A Column gives the group its content height (a ListView has no implicit height).
    Column {
        DataTable {
            id: tableView
            objectName: "examples.list"

            tallRows: true
            maxRowCountShow: 6
            defaultInfoText: qsTr("No examples available")
            model: Session.examples

            columnWidths: [numberColumnWidth, -1]

            header: EaComponents.ListViewHeader {
                visible: false
                implicitHeight: 0
                EaComponents.TableViewLabel {
                    enabled: false
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name / description")
                }
            }

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property string exampleId
                required property string name
                required property string description

                objectName: `examples.open.${exampleId}`
                TapHandler {
                    onTapped: Session.openExample(row.exampleId)
                }

                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }

                EaComponents.TableViewTwoRowsAdvancedLabel {
                    fontIcon: "archive"
                    text: row.name
                    minorText: row.description
                    ToolTip.text: row.exampleId
                    onClicked: Session.openExample(row.exampleId)
                }
            }
        }
    }
}
