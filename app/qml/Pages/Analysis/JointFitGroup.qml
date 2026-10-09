// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `joint_fit`: each experiment's weight in a joint fit, editable. The rows are the
// project's experiments, so a weight is written through the experiment's own `datasetWeight` setter; a
// refused weight returns the cell to the stored value and shows why. Shown in every mode: the loop is
// written in every mode, and a loop is a table; the weights act in joint mode.
DataTable {
    id: table

    property ProjectViewModel project: null

    objectName: "jointFit.list"
    defaultInfoText: qsTr("No joint-fit weights")
    model: project ? project.experiments : null

    // The common table design (edi ADR-0017 §8): No., the experiment's icon in its colour, its name, then the
    // weight, a number centred at display precision as every table's numbers.
    columnWidths: [numberColumnWidth, EaStyle.Sizes.tableRowHeight, -1, EaStyle.Sizes.fontPixelSize * 8]

    header: EaComponents.ListViewHeader {
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: qsTr("experiment")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            text: qsTr("weight")
        }
    }

    delegate: EaComponents.ListViewDelegate {
        id: row

        required property int index  // the base delegate's row colour reads it
        required property string name
        required property ExperimentViewModel experiment

        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignHCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: row.index + 1
        }
        IconCell {
            horizontalAlignment: Text.AlignHCenter
            objectName: `jointFit.color.${row.index}`
            icon: "microscope"
            iconColor: AppColors.experiment(row.index)
            toolTip: qsTr("Measured pattern color")
        }
        EaComponents.TableViewLabel {
            horizontalAlignment: Text.AlignLeft
            text: row.name
        }
        TextCell {
            horizontalAlignment: Text.AlignHCenter
            objectName: `jointFit.weight.${row.index}`
            accepts: "number"
            value: row.experiment ? row.experiment.datasetWeight : ""
            onCommitted: text => row.experiment.datasetWeight = Number(text)
        }
    }
}
