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
// (owner, 2026-10-05). The colour scheme drop-down precedes it in the view's centred toolbar line (StructureView); Save image is the main view's.
Item {
    id: toolbar

    // ToolbarLines takes these controls into its row, the spacer starting the camera group.
    readonly property bool toolbarUnits: true

    property StructureViewController controller: null
    property StructureViewOptions options: null
    // Off on a report's preview figure: the camera buttons only, as what is drawn is the report's.
    property bool features: true
    readonly property real buttonSize: AppSizes.toolbarControlSize

    // Which atoms are drawn (the owner, 2026-11-03): the magnetic choices appear for a magnetic structure. The camera
    // stays where it is.
    ToolbarComboBox {
        readonly property var tokens: toolbar.options ? toolbar.options.atomChoices(toolbar.controller !== null && toolbar.controller.hasMoments) : []

        objectName: "structure.toolbar.atoms"
        toolbarGroup: "atoms"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasSites
        // The closed box names the choice briefly; the list and the tooltip name it in full.
        readonly property var shortNames: ({
                "all": Session.optionLabel("structure_view.atoms", "all"),
                "asymmetric": qsTr("Crystal AU"),
                "asymmetric_magnetic": qsTr("Magnetic AU"),
                "magnetic": qsTr("Magnetic"),
                "none": Session.optionLabel("structure_view.atoms", "none")
            })
        toolTip: qsTr("Atoms: %1").arg(currentText)
        model: tokens.map(token => Session.optionLabel("structure_view.atoms", token))
        closedOnly: true
        closedTexts: tokens.map(token => shortNames[token] ?? token)
        shownIndex: Math.max(0, tokens.indexOf(toolbar.options ? toolbar.options.atoms : "all"))
        onActivated: index => toolbar.options.atoms = tokens[index]
    }
    // How the atoms are drawn, the same setting as Extra's Appearance group: radius model or ADP ellipsoids.
    ToolbarComboBox {
        readonly property OptionListModel choices: toolbar.options ? toolbar.options.atomViewOptions : null
        readonly property var tokens: choices && choices.revision >= 0 ? Array.from({ length: choices.count }, (_, i) => choices.tokenAt(i)) : []
        readonly property var shortNames: ({
                "covalent": qsTr("Covalent"),
                "vdw": qsTr("vdW"),
                "ionic": qsTr("Ionic"),
                "adp": qsTr("ADP")
            })

        objectName: "structure.toolbar.atomView"
        toolbarGroup: "atomView"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasSites && toolbar.options !== null && toolbar.options.atoms !== "none"
        toolTip: qsTr("Atom view: %1").arg(currentText)
        model: tokens.map(token => Session.optionLabel("structure_view.atom_view", token))
        closedOnly: true
        closedTexts: tokens.map(token => shortNames[token] ?? token)
        shownIndex: Math.max(0, tokens.indexOf(toolbar.options ? toolbar.options.atomView : "covalent"))
        onActivated: index => toolbar.options.atomView = tokens[index]
    }
    ChartToolButton {
        objectName: "structure.toolbar.labels"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasSites
        fontIcon: "tag"
        toolTip: qsTr("Labels")
        checked: toolbar.options !== null && toolbar.options.showLabels
        onClicked: toolbar.options.showLabels = !toolbar.options.showLabels
    }
    ChartToolButton {
        objectName: "structure.toolbar.bonds"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasSites && toolbar.controller.hasBonds
        fontIcon: "link"
        toolTip: qsTr("Bonds")
        checked: toolbar.options !== null && toolbar.options.bonds
        onClicked: toolbar.options.bonds = !toolbar.options.bonds
    }
    // Coordination polyhedra, defined in Extra's Polyhedra group: one click shows or hides them.
    ChartToolButton {
        objectName: "structure.toolbar.polyhedra"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasSites && toolbar.controller.hasBonds
        fontIcon: "dice-d20"
        toolTip: qsTr("Polyhedra")
        checked: toolbar.options !== null && toolbar.options.polyhedra
        onClicked: toolbar.options.polyhedra = !toolbar.options.polyhedra
    }
    ChartToolButton {
        objectName: "structure.toolbar.cell"
        visible: toolbar.features
        fontIcon: "vector-square"
        toolTip: qsTr("Cell")
        checked: toolbar.options !== null && toolbar.options.cell
        onClicked: toolbar.options.cell = !toolbar.options.cell
    }
    ChartToolButton {
        objectName: "structure.toolbar.moments"
        visible: toolbar.features && toolbar.controller !== null && toolbar.controller.hasMoments
        fontIcon: "long-arrow-alt-up"
        toolTip: Session.categoryTitle("atom_site_moment")
        checked: toolbar.options !== null && toolbar.options.showMoments
        onClicked: toolbar.options.showMoments = !toolbar.options.showMoments
    }
    ChartToolButton {
        objectName: "structure.toolbar.axes"
        visible: toolbar.features
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
    // Three buttons rather than a Repeater: ToolbarLines takes each into its row once, when it is made.
    AxisButton {
        axis: 0
    }
    AxisButton {
        axis: 1
    }
    AxisButton {
        axis: 2
    }
    ChartToolButton {
        objectName: "structure.toolbar.reset"
        fontIcon: "home"
        toolTip: qsTr("Reset view")
        onClicked: toolbar.controller.resetView()
    }

    // A view-along button, its axis letter in bold in the axis' colour.
    component AxisButton: ChartToolButton {
        id: axisButton

        property int axis: 0
        readonly property string name: ["a", "b", "c"][axis]
        // Read by the copy in the toolbar's More popup too.
        readonly property color letterColor: !toolbar.controller ? EaStyle.Colors.themeForeground : axis === 0 ? toolbar.controller.axisColorA : axis === 1 ? toolbar.controller.axisColorB : toolbar.controller.axisColorC

        objectName: "structure.toolbar." + name
        toolTip: qsTr("View along %1").arg(name)
        onClicked: toolbar.controller.viewAlong(axis)

        EaElements.Label {
            anchors.centerIn: parent
            font.family: EaStyle.Fonts.ptSansBold.name
            font.bold: true
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
            color: axisButton.letterColor
            text: axisButton.name
        }
    }
}
