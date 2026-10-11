// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick3D

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The structure view (edi ADR-0017 §16, ADR-0022): the core's structure scene on Qt Quick 3D,
// diffraction-lib's view in easydiffractionbeta's toolbar style. The atoms and the bonds are instanced from
// C++ (one table per mesh, filled by the controller), with no QML object per atom, bond, edge or label. The
// colour scheme and the toolbar share one line centred at the view's top, and the element legend sits at its
// bottom left (owner, 2026-10-11). The 3D item exists only where Qt Quick draws through a 3D API; elsewhere the
// view shows a line of text, with the same state.
Rectangle {
    id: view

    property StructureViewModel structure: null
    property StructureViewOptions options: null
    // The view is on the page and the tab the window shows: its page binds it, as the pattern chart's (a loaded
    // page that is not shown stays visible, clipped out of the window). A view not shown prepares nothing and
    // presents once, with the latest source, when it is shown again; a view no page hides is shown.
    property bool shown: true

    // The controller's state, by name, for the tests and the toolbar.
    readonly property StructureViewController controller: controller
    readonly property bool current: controller.current
    readonly property int revision: controller.revision
    readonly property int atomCount: controller.atomCount
    readonly property int bondCount: controller.bondCount
    readonly property int cellEdgeCount: controller.cellEdgeCount
    readonly property string detail: controller.detail
    readonly property string projection: controller.projection
    // Where Qt Quick draws through a graphics API Qt Quick 3D supports (software OpenGL included). While the
    // API is unknown, before the view is in a window, neither the 3D item nor the text exists.
    readonly property bool apiKnown: GraphicsInfo.api !== GraphicsInfo.Unknown
    readonly property bool has3D: [GraphicsInfo.OpenGL, GraphicsInfo.Direct3D11, GraphicsInfo.Direct3D12, GraphicsInfo.Vulkan, GraphicsInfo.Metal].indexOf(GraphicsInfo.api) >= 0
    readonly property real margin: EaStyle.Sizes.fontPixelSize
    // The main area's margin, left of the legend and right of the toolbar (owner, 2026-10-05).
    readonly property real sideMargin: AppSizes.mainAreaMargin
    // How far the toolbar's right edge is from the view's: the block selector row above ends there too.
    readonly property real toolbarRightInset: sideMargin
    readonly property View3D view3d: scene.item as View3D

    objectName: "structure.view"
    // EasyApp's chart background, as easydiffractionbeta's structure view (the owner, 2026-10-02), opaque behind
    // the 3D item, which clears to it too.
    color: EaStyle.Colors.chartBackground
    clip: true

    StructureViewController {
        id: controller

        // First, so a view made where it is not shown prepares nothing until it is.
        active: view.shown && view.visible
        structure: view.structure
        options: view.options
        dark: EaStyle.Colors.isDarkPalette
        // Every style colour from EasyApp's EaStyle.Colors, as easydiffractionbeta's structure view uses them (the
        // owner, 2026-10-02): the cell edges grey, the axes red, green and blue, the labels in the foreground
        // colour over a halo of the background. Lighting and atom colours are diffraction-lib's.
        edgeColor: EaStyle.Colors.grey
        axisColorA: EaStyle.Colors.red
        axisColorB: EaStyle.Colors.green
        axisColorC: EaStyle.Colors.blue
        labelColor: EaStyle.Colors.themeForeground
        haloColor: EaStyle.Colors.chartBackground
        viewportWidth: view.width
        viewportHeight: view.height
        // The band kept clear at the top for the toolbar: its height with its margins.
        topBand: toolbar.height + 2 * view.margin
        spheres: structureScene.spheres
        cylinders: structureScene.cylinders
        triadShafts: structureScene.triadShafts
        triadHeads: structureScene.triadHeads
        shared: structureScene.shared
        labels: labelLayer
    }

    // The scene, on every platform; the View3D below draws it where there is a 3D API.
    StructureScene {
        id: structureScene

        controller: controller
    }

    // The scene, its labels and the legend.
    Item {
        id: capture

        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: view.color
        }
        Loader {
            id: scene

            anchors.fill: parent
            active: view.has3D
            sourceComponent: View3D {
                importScene: structureScene
                camera: structureScene.camera
                environment: SceneEnvironment {
                    backgroundMode: SceneEnvironment.Color
                    clearColor: view.color
                    antialiasingMode: SceneEnvironment.MSAA
                    antialiasingQuality: SceneEnvironment.High
                    // Linear light out to sRGB, as three.js renders diffraction-lib's view.
                    tonemapMode: SceneEnvironment.TonemapModeLinear
                }
            }
        }
        StructureLabelLayer {
            id: labelLayer

            objectName: "structure.view.labels"
            anchors.fill: parent
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
            font.weight: Font.DemiBold
            letterFont.family: EaStyle.Fonts.ptSansBold.name
            letterFont.bold: true
            letterFont.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
        }
        ChartLegend {
            id: legend
            objectName: "structure.view.legend"
            minimumHeight: AppSizes.toolbarControlSize
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.margins: view.margin
            anchors.leftMargin: view.sideMargin
            entries: controller.legend
            labelInColor: false
            visible: controller.legend.count > 0
        }
        EaElements.Label {
            objectName: "structure.view.unavailable"
            anchors.centerIn: parent
            visible: view.apiKnown && !view.has3D
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("The structure view needs a 3D graphics API, which this display does not provide")
        }
    }

    // Drag rotates, the wheel zooms about the pointer, a right drag pans; hovering names the atom under the
    // pointer by the surface Qt's pick hits (edi ADR-0022 §7).
    MouseArea {
        id: pointer

        property point last

        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        onPressed: mouse => {
            pointer.last = Qt.point(mouse.x, mouse.y);
            hover.text = "";
        }
        onPositionChanged: mouse => {
            const dx = mouse.x - pointer.last.x;
            const dy = mouse.y - pointer.last.y;
            pointer.last = Qt.point(mouse.x, mouse.y);
            if (mouse.buttons & Qt.LeftButton)
                controller.rotateBy(dx, dy);
            else if (mouse.buttons & Qt.RightButton)
                controller.panBy(dx, dy);
            else
                hover.show(mouse.x, mouse.y);
        }
        onExited: hover.text = ""
        onWheel: wheel => controller.zoomAt(wheel.x, wheel.y, wheel.angleDelta.y)
    }

    // The colour scheme and the toolbar, a toolbar group's spacing apart, in one line centred under the block
    // selector row (owner, 2026-10-11).
    Row {
        x: Math.round(view.sideMargin + (view.width - view.toolbarRightInset - view.sideMargin - width) / 2)
        y: view.margin
        spacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing

        ToolbarComboBox {
            objectName: "structure.toolbar.colors"
            toolTip: qsTr("Colour scheme")
            model: ["jmol", "vesta"]
            currentIndex: view.options && view.options.colorScheme === "vesta" ? 1 : 0
            onActivated: index => view.options.colorScheme = index === 1 ? "vesta" : "jmol"
        }
        StructureToolbar {
            id: toolbar

            controller: controller
            options: view.options
        }
    }

    // The atom under the pointer: its label, its parts and its coordinates, beside the pointer.
    Rectangle {
        id: hover

        property alias text: hoverLabel.text

        function show(x, y) {
            const result = view.view3d ? view.view3d.rayPick(controller.pickOrigin(x, y), controller.pickDirection(x, y)) : null;
            hover.text = result ? structureScene.hoverText(result) : "";
            hover.x = Math.min(x + view.margin, view.width - hover.width);
            hover.y = Math.min(y + view.margin, view.height - hover.height);
        }

        objectName: "structure.view.hover"
        visible: text !== ""
        width: hoverLabel.width
        height: hoverLabel.height
        color: EaStyle.Colors.mainContentBackgroundHalfTransparent
        border.color: EaStyle.Colors.chartGridLine
        border.width: EaStyle.Sizes.borderThickness

        EaElements.Label {
            id: hoverLabel

            padding: view.margin * 0.5
        }
    }
}
