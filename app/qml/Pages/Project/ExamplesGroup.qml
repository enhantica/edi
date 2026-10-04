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
        EaComponents.TableView {
            id: tableView
            objectName: "examples.list"

            showHeader: false
            tallRows: true
            maxRowCountShow: 6
            defaultInfoText: qsTr("No examples available")
            model: Session.examples

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    enabled: false
                    width: AppSizes.indexColumnWidth
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name / description")
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string exampleId
                required property string name
                required property string description

                objectName: `examples.open.${exampleId}`
                mouseArea.onPressed: Session.openExample(row.exampleId)

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }

                EaComponents.TableViewTwoRowsAdvancedLabel {
                    fontIcon: "archive"
                    text: row.name
                    minorText: row.description
                    ToolTip.text: row.exampleId
                }
            }
        }
    }
}
