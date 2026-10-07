// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Logic as EaLogic
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `fit_parameter`: the persisted pre-fit start state — each fitted parameter's value and uncertainty
// before the last fit, which undo restores — read-only (a fit writes it). A loop in `.edi`, so a
// table.
EaComponents.TableView {
    id: table

    property AnalysisViewModel analysis: null

    // A start value at the base's default precision; the model keeps it whole.
    function shown(value) {
        return value === undefined ? "" : EaLogic.Utils.toDefaultPrecision(value);
    }

    objectName: "fitStart.list"
    defaultInfoText: qsTr("No fit start state")
    model: analysis ? analysis.fitStart : null

    header: EaComponents.TableViewHeader {
        EaComponents.TableViewLabel {
            width: AppSizes.indexColumnWidth
        }
        EaComponents.TableViewLabel {
            flexibleWidth: true
            horizontalAlignment: Text.AlignLeft
            text: qsTr("parameter")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 6
            text: qsTr("start value")
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 6
            text: qsTr("start error")
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
            width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideMiddle
            text: row.model.id
            ToolTip.text: row.model.id
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 6
            text: table.shown(row.model.startValue)
        }
        EaComponents.TableViewLabel {
            width: EaStyle.Sizes.fontPixelSize * 6
            text: table.shown(row.model.startUncertainty)
        }
    }
}
