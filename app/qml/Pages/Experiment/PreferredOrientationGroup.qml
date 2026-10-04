// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `preferred_orientation` (March–Dollase, constant wavelength): the structure it
// corrects, the texture axis [h k l], r and the random fraction; at most one row.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property PrefOrientListModel rows: experiment ? experiment.preferredOrientation : null
    readonly property real indexWidth: EaStyle.Sizes.fontPixelSize * 2.5

    spacing: AppSizes.groupContentSpacing

    EaComponents.TableView {
        objectName: "preferredOrientation.list"
        defaultInfoText: qsTr("No preferred orientation")
        model: group.rows

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: qsTr("structure")
            }
            EaComponents.TableViewLabel {
                width: group.indexWidth
                text: "h"
            }
            EaComponents.TableViewLabel {
                width: group.indexWidth
                text: "k"
            }
            EaComponents.TableViewLabel {
                width: group.indexWidth
                text: "l"
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 6
                text: "r"
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 6
                text: qsTr("random")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            required property string structureId
            required property int indexH
            required property int indexK
            required property int indexL
            required property ParameterItem marchR
            required property ParameterItem marchRandomFract

            TextCell {
                objectName: `preferredOrientation.structureId.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 8
                value: row.structureId
                onCommitted: text => group.rows.setStructureId(row.index, text)
            }
            TextCell {
                objectName: `preferredOrientation.indexH.${row.index}`
                width: group.indexWidth
                value: row.indexH
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "h", Number(text))
            }
            TextCell {
                objectName: `preferredOrientation.indexK.${row.index}`
                width: group.indexWidth
                value: row.indexK
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "k", Number(text))
            }
            TextCell {
                objectName: `preferredOrientation.indexL.${row.index}`
                width: group.indexWidth
                value: row.indexL
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "l", Number(text))
            }
            ParameterCell {
                objectName: `preferredOrientation.marchR.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 6
                item: row.marchR
            }
            ParameterCell {
                objectName: `preferredOrientation.marchRandomFract.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 6
                item: row.marchRandomFract
            }
            EaComponents.TableViewButton {
                objectName: `preferredOrientation.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this row")
                onClicked: group.rows.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "preferredOrientation.append"
        wide: true  // the row to itself, as the original's append actions fill theirs
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        text: qsTr("Add preferred orientation")
        onClicked: group.rows.append()
    }
}
