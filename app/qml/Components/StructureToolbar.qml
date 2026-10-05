// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The structure view's toolbar (edi ADR-0017 §16): diffraction-lib's modebar (`templates/structure.html.j2`),
// its buttons and behaviour, drawn as ChartToolButton with the chart toolbar's spacing and spacer. The features
// first, one button per feature the structure has, in diffraction-lib's order: atoms (all, asymmetric unit, none),
// labels, bonds, cell, axes. Then the camera group, ending at the right in Home: projection, view along a, b and c,
// reset view (owner, 2026-10-05). The colour scheme drop-down sits at the view's left, after the legend
// (StructureView).
Row {
    id: toolbar

    property StructureViewController controller: null
    property StructureViewOptions options: null
    readonly property real buttonSize: AppSizes.toolbarControlSize

    spacing: AppSizes.toolbarSpacing

    ChartToolButton {
        objectName: "structure.toolbar.atoms"
        visible: toolbar.controller !== null && toolbar.controller.hasSites
        fontIcon: "atom"
        toolTip: toolbar.controller && toolbar.controller.hasCopies ? qsTr("Atoms: all / asymmetric unit / none") : qsTr("Atoms: show / hide")
        checked: toolbar.options !== null && toolbar.options.atoms !== "none"
        onClicked: toolbar.options.cycleAtoms(toolbar.controller.hasCopies)
    }
    ChartToolButton {
        objectName: "structure.toolbar.labels"
        visible: toolbar.controller !== null && toolbar.controller.hasSites
        fontIcon: "tag"
        toolTip: qsTr("Labels")
        checked: toolbar.options !== null && toolbar.options.showLabels
        onClicked: toolbar.options.showLabels = !toolbar.options.showLabels
    }
    ChartToolButton {
        objectName: "structure.toolbar.bonds"
        visible: toolbar.controller !== null && toolbar.controller.hasSites && toolbar.controller.hasBonds
        fontIcon: "link"
        toolTip: qsTr("Bonds")
        checked: toolbar.options !== null && toolbar.options.bonds
        onClicked: toolbar.options.bonds = !toolbar.options.bonds
    }
    ChartToolButton {
        objectName: "structure.toolbar.cell"
        fontIcon: "vector-square"
        toolTip: qsTr("Cell")
        checked: toolbar.options !== null && toolbar.options.cell
        onClicked: toolbar.options.cell = !toolbar.options.cell
    }
    ChartToolButton {
        objectName: "structure.toolbar.axes"
        fontIcon: "location-arrow"
        toolTip: qsTr("Axes")
        checked: toolbar.options !== null && toolbar.options.axes
        onClicked: toolbar.options.axes = !toolbar.options.axes
    }
    Item {
        width: EaStyle.Sizes.fontPixelSize * 0.5
        height: 1
    }
    ChartToolButton {
        objectName: "structure.toolbar.projection"
        fontIcon: "cube"
        toolTip: toolbar.controller && toolbar.controller.projection === "perspective" ? qsTr("Perspective view") : qsTr("Parallel (orthographic) view")
        onClicked: toolbar.controller.toggleProjection()
    }
    Repeater {
        model: [
            {
                "name": "a",
                "axis": 0
            },
            {
                "name": "b",
                "axis": 1
            },
            {
                "name": "c",
                "axis": 2
            }
        ]
        delegate: ChartToolButton {
            id: axisButton

            required property var modelData

            objectName: "structure.toolbar." + modelData.name
            toolTip: qsTr("View along %1").arg(modelData.name)
            onClicked: toolbar.controller.viewAlong(modelData.axis)

            // The axis letter in bold in its axis colour, a label placed on the button.
            EaElements.Label {
                anchors.centerIn: parent
                font.family: EaStyle.Fonts.ptSansBold.name
                font.bold: true
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
                color: !toolbar.controller ? EaStyle.Colors.themeForeground : axisButton.modelData.axis === 0 ? toolbar.controller.axisColorA : axisButton.modelData.axis === 1 ? toolbar.controller.axisColorB : toolbar.controller.axisColorC
                text: axisButton.modelData.name
            }
        }
    }
    ChartToolButton {
        objectName: "structure.toolbar.reset"
        fontIcon: "home"
        toolTip: qsTr("Reset view")
        onClicked: toolbar.controller.resetView()
    }
}
