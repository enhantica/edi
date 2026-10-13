// SPDX-License-Identifier: BSD-3-Clause
// Pinned gui-components copy; edi terminology and units in the parameter menu (ADR-0029).
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Templates as T
import QtQuick.Controls
import QtQuick.Controls.impl

import EasyApplication.Gui.Logic as EaLogic
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

EaElements.TextField {
    id: control

    property var parameter: {
        'value': 0.0,
        'error': 0.0,
        'enabled': true,
        'fittable': false,
        'fit': false,
        'category': '',
        'name': 'default',
        'prettyName': '',
        'shortPrettyName': '',
        'units': '',
        'url': '',
        'cifDict': ''
    }

    property var value: {
        if (typeof parameter.value === 'undefined') {
            return '';
        } else if (typeof parameter.value === 'number') {
            return EaLogic.Utils.toErrSinglePrecision(parameter.value, parameter.error);
        } else {
            return parameter.value;
        }
    }
    property var error: {
        if (typeof parameter.error === 'undefined') {
            return '';
        } else if (typeof parameter.value === 'number') {
            return EaLogic.Utils.toSinglePrecision(parameter.error);
        } else {
            return parameter.error;
        }
    }

    property bool fittable: parameter.fittable ?? false
    property bool fit: parameter.fit ?? false
    property string category: parameter.category ?? ''
    property string name: parameter.name ?? 'default'
    property string prettyName: parameter.prettyName ?? ''
    property string shortPrettyName: parameter.shortPrettyName ?? ''
    property string units: parameter.units ?? ''
    property string url: parameter.url ?? ''
    property string cifDict: parameter.cifDict ?? ''

    // The value's menu (its name, value, units, s.u. and free toggle) is made the first time it opens: a page
    // holds many values, and a menu each made up front was most of a large project's page build.
    property EaElements.Menu contextMenu: null
    // The menu's free toggle, once the menu is made.
    property EaElements.CheckBox fitCheckBox: null
    signal fitToggled(bool checked)

    function openContextMenu(parentItem) {
        if (contextMenu === null)
            contextMenu = contextMenuComponent.createObject(parentItem);
        contextMenu.popup();
    }

    readOnly: !parameter.enabled ?? false

    rightPadding: unitsPlaceholder.width
    topInset: control.shortPrettyName === '' ? 0 : EaStyle.Sizes.fontPixelSize * 1.5
    topPadding: topInset + padding

    // Shares the row's width with its siblings, a quarter of the font size apart (edi's AppSizes.inputSpacing).
    width: (EaStyle.Sizes.sideBarContentWidth - (parent.children.length - 1) * EaStyle.Sizes.fontPixelSize * 0.25) / parent.children.length

    text: control.value
    font.bold: control.fit && enabled

    onAccepted: focus = false

    // Title
    EaElements.Label {
        anchors.right: parent.right
        rightPadding: unitsPlaceholder.rightPadding

        color: EaStyle.Colors.themeForegroundMinor

        font.bold: false
        text: control.shortPrettyName
    }
    // Title

    // Units
    PlaceholderText {
        id: unitsPlaceholder

        x: control.width - width
        topPadding: control.topPadding
        leftPadding: text !== '' ? EaStyle.Sizes.fontPixelSize * 0.5 : 0
        rightPadding: EaStyle.Sizes.fontPixelSize * 0.75

        font.family: control.font.family
        font.pixelSize: control.font.pixelSize
        font.bold: false
        color: control.placeholderTextColor

        text: control.units
        textFormat: Text.RichText
    }
    // Units

    //Mouse area to react on click events
    MouseArea {
        id: menuArea
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        cursorShape: undefined  // prevents changing the cursor
        hoverEnabled: false
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton) {
                control.openContextMenu(menuArea);
            }
        }
        onPressAndHold: mouse => {
            if (mouse.source === Qt.MouseEventNotSynthesized) {
                control.openContextMenu(menuArea);
            }
        }
        // Menu
        Component {
            id: contextMenuComponent

            EaElements.Menu {
                width: layout.implicitWidth

                // Layout
                Grid {
                    id: layout

                    leftPadding: 1.25 * EaStyle.Sizes.fontPixelSize
                    rightPadding: 1.25 * EaStyle.Sizes.fontPixelSize
                    topPadding: 0.5 * EaStyle.Sizes.fontPixelSize
                    bottomPadding: 0.75 * EaStyle.Sizes.fontPixelSize
                    rowSpacing: 0.75 * EaStyle.Sizes.fontPixelSize
                    columnSpacing: 1.5 * EaStyle.Sizes.fontPixelSize

                    rows: 2

                    // Header
                    EaElements.Label {
                        color: EaStyle.Colors.themeForegroundMinor
                        text: control.cifDict ? 'cif name' : 'cif-like name'
                    }
                    EaElements.Label {
                        color: EaStyle.Colors.themeForegroundMinor
                        text: 'value'
                    }
                    EaElements.Label {
                        visible: control.units !== ''
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr("units")
                    }
                    EaElements.Label {
                        visible: control.fittable && control.error !== ''
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr("s.u.")
                    }
                    EaElements.Label {
                        visible: control.fittable && !control.readOnly
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr("free")
                    }
                    // Headert

                    // Content
                    EaElements.Button {
                        text: `${control.category}.${control.name}`
                        checked: true
                        onClicked: Qt.openUrlExternally(control.url)
                    }
                    EaElements.Label {
                        text: control.value
                        font.bold: control.fit
                    }
                    EaElements.Label {
                        visible: control.units !== ''
                        text: control.units
                        color: EaStyle.Colors.themeForegroundMinor
                    }
                    EaElements.Label {
                        visible: control.fittable && control.error !== ''
                        text: control.error
                    }
                    EaElements.CheckBox {
                        id: fitBox
                        visible: control.fittable && !control.readOnly
                        padding: 0
                        checked: control.fit
                        onToggled: control.fitToggled(checked)
                        Component.onCompleted: control.fitCheckBox = fitBox
                    }
                    // Content
                }
                // Layout
            }
        }
        // Menu
    }
    // Mouse area
}
