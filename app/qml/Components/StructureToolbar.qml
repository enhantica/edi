// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The structure view's toolbar (edi ADR-0017 §16): diffraction-lib's modebar (`templates/structure.html.j2`),
// its buttons and behaviour, drawn as ChartToolButton with the chart toolbar's spacing and spacer. The features
// first, one control per feature the structure has, in diffraction-lib's order: the atoms shown (a drop-down),
// labels, bonds, cell, magnetic moments (when the structure has them), axes. Then the camera group, ending in Home: projection, view along a, b and c, reset view
// (owner, 2026-10-05). The colour scheme drop-down precedes it in the view's centred toolbar line (StructureView).
Row {
    id: toolbar

    property StructureViewController controller: null
    property StructureViewOptions options: null
    readonly property real buttonSize: AppSizes.toolbarControlSize

    spacing: AppSizes.toolbarSpacing

    // Which atoms are drawn (the owner, 2026-11-03): the magnetic choices appear for a magnetic structure. The camera
    // stays where it is.
    ToolbarComboBox {
        readonly property var tokens: toolbar.options ? toolbar.options.atomChoices(toolbar.controller !== null && toolbar.controller.hasMoments) : []

        objectName: "structure.toolbar.atoms"
        visible: toolbar.controller !== null && toolbar.controller.hasSites
        // The closed box names the choice briefly; the list and the tooltip name it in full.
        readonly property var shortNames: ({
                "all": qsTr("All"),
                "asymmetric": qsTr("Crystal AU"),
                "asymmetric_magnetic": qsTr("Magnetic AU"),
                "magnetic": qsTr("Magnetic"),
                "none": qsTr("None")
            })
        toolTip: qsTr("Atoms: %1").arg(currentText)
        model: tokens.map(token => Session.optionLabel("structure_view.atoms", token))
        closedOnly: true
        closedTexts: tokens.map(token => shortNames[token] ?? token)
        shownIndex: Math.max(0, tokens.indexOf(toolbar.options ? toolbar.options.atoms : "all"))
        onActivated: index => toolbar.options.atoms = tokens[index]
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
        objectName: "structure.toolbar.moments"
        visible: toolbar.controller !== null && toolbar.controller.hasMoments
        fontIcon: "long-arrow-alt-up"
        toolTip: qsTr("Magnetic moments")
        checked: toolbar.options !== null && toolbar.options.showMoments
        onClicked: toolbar.options.showMoments = !toolbar.options.showMoments
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
