// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The application preferences (the base's Components/PreferencesDialog.qml, rebuilt from its pieces as the
// About dialog is; edi ADR-0017 §12): the same five tabs and layout, with edi's changes — no 1D plotting row,
// a Sidebar side selector in Appearance, and what is not available yet (update checks, zoom, language) shown
// disabled with a "Not available yet" tooltip. The base's own dialog stays hidden: the app bar opens this one.
AppDialog {
    id: dialog

    // A disabled control takes no hover, so its tooltip hangs on the item around it (§4).
    component NotAvailable: Item {
        implicitWidth: childrenRect.width
        implicitHeight: childrenRect.height

        HoverHandler {
            id: hover
        }
        EaElements.ToolTip {
            text: qsTr("Not available yet")
            visible: hover.hovered && EaGlobals.Vars.showToolTips
        }
    }

    objectName: "preferences"
    visible: Preferences.dialogShown
    onClosed: Preferences.dialogShown = false

    title: qsTr("Preferences")
    standardButtons: Dialog.Ok

    contentWidth: bar.implicitWidth
    contentHeight: bar.implicitHeight + implicitHeaderHeight + topPadding + bottomPadding + EaStyle.Sizes.fontPixelSize * 9

    EaElements.TabBar {
        id: bar

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right

        background: Rectangle {
            z: 2
            anchors.fill: parent
            color: "transparent"
            border.color: EaStyle.Colors.appBarBorder
        }

        EaElements.AppBarTabButton {
            fontIcon: "users"
            text: qsTr("Prompts")
        }
        EaElements.AppBarTabButton {
            fontIcon: "cloud-download-alt"
            text: qsTr("Updates")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.appearance"
            fontIcon: "paint-brush"
            text: qsTr("Appearance")
        }
        EaElements.AppBarTabButton {
            fontIcon: "flask"
            text: qsTr("Experimental")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.develop"
            fontIcon: "laptop-code"
            text: qsTr("Develop")
        }
    }

    SwipeView {
        anchors.top: bar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        topPadding: EaStyle.Sizes.fontPixelSize * 0.75
        leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
        bottomPadding: EaStyle.Sizes.fontPixelSize * 3

        currentIndex: bar.currentIndex
        interactive: false
        clip: true

        // Prompts, as the base's
        Grid {
            columns: 2
            topPadding: EaStyle.Sizes.fontPixelSize * 0.5
            rowSpacing: EaStyle.Sizes.fontPixelSize * 1.5
            columnSpacing: EaStyle.Sizes.fontPixelSize
            verticalItemAlignment: Grid.AlignVCenter

            EaElements.Label {
                text: qsTr("Enable tool tips") + ":"
            }
            EaElements.CheckBox {
                objectName: "preferences.toolTips"
                checked: Preferences.toolTips
                onToggled: Preferences.toolTips = checked
            }

            EaElements.Label {
                enabled: false
                text: qsTr("Enable user guides") + ":"
            }
            EaElements.CheckBox {
                enabled: false
                checked: false
            }
        }

        // Updates: no update check exists yet, so both are disabled and the start check is off.
        Column {
            topPadding: EaStyle.Sizes.fontPixelSize * 0.5
            spacing: EaStyle.Sizes.fontPixelSize * 1.5

            NotAvailable {
                Row {
                    id: checkOnStartRow
                    spacing: EaStyle.Sizes.fontPixelSize

                    EaElements.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        enabled: false
                        text: qsTr("Check on application start") + ":"
                    }
                    EaElements.CheckBox {
                        objectName: "preferences.checkUpdateOnStart"
                        padding: 0
                        enabled: false
                        checked: false
                    }
                }
            }

            NotAvailable {
                EaElements.SideBarButton {
                    objectName: "preferences.checkUpdateNow"
                    width: checkOnStartRow.width
                    enabled: false
                    highlighted: true
                    text: qsTr("Check now")
                }
            }
        }

        // Appearance: the theme, the sidebar's side, auto collapse; no 1D plotting row.
        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: EaStyle.Sizes.fontPixelSize
            verticalItemAlignment: Grid.AlignVCenter

            EaElements.Label {
                text: qsTr("Theme") + ":"
            }
            EaElements.ComboBox {
                objectName: "preferences.theme"
                model: [qsTr("Light"), qsTr("Dark"), qsTr("System")]
                currentIndex: EaStyle.Colors.theme === EaStyle.Colors.DarkTheme ? 1 : EaStyle.Colors.theme === EaStyle.Colors.SystemTheme ? 2 : 0
                onActivated: index => {
                    EaStyle.Colors.theme = index === 1 ? EaStyle.Colors.DarkTheme : index === 2 ? EaStyle.Colors.SystemTheme : EaStyle.Colors.LightTheme;
                }
            }

            EaElements.Label {
                text: qsTr("Sidebar") + ":"
            }
            EaElements.ComboBox {
                objectName: "preferences.sideBarSide"
                model: [qsTr("Left"), qsTr("Right")]
                currentIndex: Preferences.sideBarOnLeft ? 0 : 1
                onActivated: index => Preferences.sideBarSide = index === 0 ? "Left" : "Right"
            }

            EaElements.Label {
                topPadding: autoCollapseCheckBox.topPadding
                text: qsTr("Auto collapse") + ":"
            }
            EaElements.CheckBox {
                id: autoCollapseCheckBox
                objectName: "preferences.autoCollapse"
                topPadding: 0.5 * EaStyle.Sizes.fontPixelSize
                leftPadding: -3
                checked: Preferences.autoCollapse
                onToggled: Preferences.autoCollapse = checked
                ToolTip.text: qsTr("Auto collapse for side bar groups")
            }
        }

        // Experimental: zoom and language are not available yet — the default zoom, English.
        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: EaStyle.Sizes.fontPixelSize
            verticalItemAlignment: Grid.AlignVCenter

            EaElements.Label {
                enabled: false
                text: qsTr("Zoom") + ":"
            }
            NotAvailable {
                EaElements.ComboBox {
                    objectName: "preferences.zoom"
                    enabled: false
                    model: ["100%"]
                }
            }

            EaElements.Label {
                enabled: false
                text: qsTr("Language") + ":"
            }
            NotAvailable {
                EaElements.ComboBox {
                    objectName: "preferences.language"
                    enabled: false
                    model: [qsTr("English")]
                }
            }
        }

        // Develop, as the base's
        Grid {
            columns: 2
            columnSpacing: EaStyle.Sizes.fontPixelSize
            rowSpacing: EaStyle.Sizes.fontPixelSize
            verticalItemAlignment: Grid.AlignVCenter

            EaElements.Label {
                enabled: false
                text: qsTr("Logging to") + ":"
            }
            EaElements.ComboBox {
                enabled: false
                model: ["Disabled", "Terminal", "File"]
                currentIndex: 1
            }

            EaElements.Label {
                text: qsTr("Logging level") + ":"
            }
            EaElements.ComboBox {
                model: ["Debug", "Info", "Error", "Disabled"]
                currentIndex: model.indexOf(EaGlobals.Vars.loggingLevel)
                onActivated: EaGlobals.Vars.loggingLevel = currentValue
            }

            // What the app runs on and with, to read and to copy (the owner, 2026-10-06).
            EaElements.Label {
                text: qsTr("Diagnostics") + ":"
            }
            EaElements.Button {
                objectName: "preferences.diagnostics"
                text: qsTr("Show")
                onClicked: diagnostics.open()
            }
        }
    }

    DiagnosticsDialog {
        id: diagnostics
        parent: Overlay.overlay
    }
}
