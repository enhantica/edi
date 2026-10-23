// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The application preferences (the base's Components/PreferencesDialog.qml, rebuilt from its pieces as the
// About dialog is; edi ADR-0017 §12): the base's tabs and layout and a Projects tab, with edi's changes — no 1D
// plotting row, a colour scheme and a Sidebar side selector in Appearance, the settings file in Develop, and what is
// not available yet (update checks, zoom, language) shown disabled with a "Not available yet" tooltip. Every tab has
// the same two columns, labels and controls. The base's
// own dialog stays hidden: the app bar opens this one.
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

    // One layout on every tab (the owner, 2026-10-14): the labels in one column as wide as the widest label, the controls
    // in one column as wide as the longest item of any box or the longest button text, and each label level with the
    // first line of its control.
    component RowGrid: Grid {
        columns: 2
        topPadding: EaStyle.Sizes.fontPixelSize * 0.5
        columnSpacing: EaStyle.Sizes.fontPixelSize
        rowSpacing: EaStyle.Sizes.fontPixelSize
        verticalItemAlignment: Grid.AlignTop
    }
    component RowLabel: EaElements.Label {
        readonly property bool rowLabel: true

        width: dialog.labelWidth
        topPadding: dialog.lineOffset
    }
    component RowBox: EaElements.ComboBox {
        readonly property bool rowBox: true

        width: dialog.controlWidth
    }
    component RowButton: EaElements.SideBarButton {
        readonly property bool rowButton: true

        width: dialog.controlWidth
        height: dialog.rowHeight
    }
    component RowCheckBox: EaElements.CheckBox {
        height: dialog.rowHeight
        leftPadding: -3
    }

    // Every item under `item` that `wanted` accepts.
    function itemsUnder(item, wanted) {
        let found = [];
        for (const child of item.children) {
            if (wanted(child))
                found.push(child);
            found = found.concat(itemsUnder(child, wanted));
        }
        return found;
    }
    // The width a box needs for its longest item: its paddings, its text's own and its arrow, which the box draws inside
    // its content.
    function boxNeed(box) {
        let widest = 0;
        for (let i = 0; i < box.count; ++i)
            widest = Math.max(widest, boxMetrics.advanceWidth(box.textAt(i)));
        return Math.ceil(widest + box.leftPadding + box.rightPadding + box.indicator.width + box.contentItem.leftPadding + box.contentItem.rightPadding);
    }
    // The width a button needs for its text with an em at each side (its content reports no width of its own).
    function buttonNeed(button) {
        return Math.ceil(boxMetrics.advanceWidth(button.text) + 2 * EaStyle.Sizes.fontPixelSize);
    }

    readonly property var rowItems: pages.contentChildren.reduce((all, page) => all.concat(itemsUnder(page, item => item.rowLabel === true || item.rowBox === true || item.rowButton === true)), [])
    readonly property real labelWidth: rowItems.reduce((widest, item) => item.rowLabel === true ? Math.max(widest, item.implicitWidth) : widest, 0)
    readonly property real controlWidth: rowItems.reduce((widest, item) => Math.max(widest, item.rowBox === true ? boxNeed(item) : item.rowButton === true ? buttonNeed(item) : 0), 0)
    readonly property real stackSpacing: EaStyle.Sizes.fontPixelSize * 0.5
    readonly property real rowHeight: themeBox.implicitHeight
    // A label's line, centred on a control's height.
    readonly property real lineOffset: Math.max(0, (rowHeight - lineMetrics.height) / 2)

    objectName: "preferences"
    visible: Preferences.dialogShown
    onClosed: Preferences.dialogShown = false

    title: qsTr("Preferences")
    standardButtons: Dialog.Ok

    contentWidth: Math.max(bar.implicitWidth, pages.leftPadding + pages.rightPadding + labelWidth + EaStyle.Sizes.fontPixelSize + controlWidth)
    // As tall as the tallest tab's rows need, so no tab's last row is cut (the owner, 2026-10-13).
    contentHeight: bar.implicitHeight + pages.topPadding + pages.bottomPadding + pages.contentChildren.reduce((tallest, page) => Math.max(tallest, page.implicitHeight), 0)

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
            objectName: "preferences.tab.prompts"
            fontIcon: "users"
            text: qsTr("Prompts")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.updates"
            fontIcon: "cloud-download-alt"
            text: qsTr("Updates")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.appearance"
            fontIcon: "paint-brush"
            text: qsTr("Appearance")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.projects"
            fontIcon: "archive"
            text: qsTr("Projects")
        }
        EaElements.AppBarTabButton {
            objectName: "preferences.tab.experimental"
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
        id: pages

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
        // A gap between the pages, so no tab's controls reach into the shown one.
        spacing: EaStyle.Sizes.fontPixelSize * 2
        // A tab shows at once, without the swipe's slide, so its columns are where every other tab has them.
        Component.onCompleted: (pages.contentItem as ListView).highlightMoveDuration = 0

        // Prompts, as the base's
        RowGrid {
            RowLabel {
                text: qsTr("Enable tool tips") + ":"
            }
            RowCheckBox {
                objectName: "preferences.toolTips"
                checked: Preferences.toolTips
                onToggled: Preferences.toolTips = checked
            }

            RowLabel {
                enabled: false
                text: qsTr("Enable user guides") + ":"
            }
            RowCheckBox {
                enabled: false
                checked: false
            }
        }

        // Updates: no update check exists yet, so both are disabled and the start check is off.
        RowGrid {
            RowLabel {
                enabled: false
                text: qsTr("Check on application start") + ":"
            }
            NotAvailable {
                RowCheckBox {
                    objectName: "preferences.checkUpdateOnStart"
                    enabled: false
                    checked: false
                }
            }

            Item {
                width: dialog.labelWidth
                height: 1
            }
            NotAvailable {
                RowButton {
                    objectName: "preferences.checkUpdateNow"
                    enabled: false
                    highlighted: true
                    text: qsTr("Check now")
                }
            }
        }

        // Appearance: the theme, the colour scheme, the sidebar's side and auto collapse; no 1D plotting row.
        RowGrid {
            RowLabel {
                id: themeLabel

                text: qsTr("Theme") + ":"
            }
            RowBox {
                id: themeBox

                objectName: "preferences.theme"
                model: [qsTr("Light"), qsTr("Dark"), qsTr("System")]
                currentIndex: EaStyle.Colors.theme === EaStyle.Colors.DarkTheme ? 1 : EaStyle.Colors.theme === EaStyle.Colors.SystemTheme ? 2 : 0
                onActivated: index => {
                    EaStyle.Colors.theme = index === 1 ? EaStyle.Colors.DarkTheme : index === 2 ? EaStyle.Colors.SystemTheme : EaStyle.Colors.LightTheme;
                }
            }

            // The colours, one choice for each thing coloured (the owner, 2026-10-22): the structures' and the
            // patterns' schemes, the Stacked view's lines and the Map's colour map. The schemes' tokens and names
            // (edi::colour_scheme_names) in the order the core lists them; the scan views' choices as their charts
            // offer them.
            RowLabel {
                text: qsTr("Structures") + ":"
            }
            RowBox {
                readonly property var schemes: ApplicationInfo.colourSchemes

                objectName: "preferences.structureColours"
                model: ApplicationInfo.colourSchemeTitles
                currentIndex: Math.max(0, schemes.indexOf(ApplicationInfo.colourSchemeOrDefault(Preferences.structureColours)))
                onActivated: index => Preferences.structureColourScheme = schemes[index]
                ToolTip.text: qsTr("The structures' colours: their icons, Bragg ticks and curves")
            }
            RowLabel {
                text: qsTr("Patterns") + ":"
            }
            RowBox {
                readonly property var schemes: ApplicationInfo.colourSchemes

                objectName: "preferences.patternColours"
                model: ApplicationInfo.colourSchemeTitles
                currentIndex: Math.max(0, schemes.indexOf(ApplicationInfo.colourSchemeOrDefault(Preferences.patternColours)))
                onActivated: index => Preferences.patternColourScheme = schemes[index]
                ToolTip.text: qsTr("The patterns' colours: the experiments' icons and measured data, and the calculated, background and residual lines")
            }
            RowLabel {
                text: qsTr("Stacked") + ":"
            }
            RowBox {
                readonly property var choices: Array.from(ApplicationInfo.colourSchemes).concat(Array.from(ApplicationInfo.scanColourMaps))
                // Empty follows the patterns' scheme.
                readonly property string current: Preferences.scanStackedPalette !== "" ? Preferences.scanStackedPalette : Preferences.patternColours

                objectName: "preferences.stackedColours"
                model: choices.map(choice => ApplicationInfo.scanColourTitle(choice))
                currentIndex: Math.max(0, choices.indexOf(current))
                onActivated: index => Preferences.scanStackedPalette = choices[index]
                ToolTip.text: qsTr("The Stacked view's patterns")
            }
            RowLabel {
                text: qsTr("Map") + ":"
            }
            RowBox {
                readonly property var choices: Array.from(ApplicationInfo.scanColourRamps).concat(Array.from(ApplicationInfo.scanColourMaps))

                objectName: "preferences.mapColours"
                model: choices.map(choice => ApplicationInfo.scanColourTitle(choice))
                currentIndex: Math.max(0, choices.indexOf(Preferences.scanMapColours))
                onActivated: index => Preferences.scanMapColours = choices[index]
                ToolTip.text: qsTr("The Map's colour map, also chosen on the Map's toolbar")
            }

            RowLabel {
                text: qsTr("Sidebar") + ":"
            }
            RowBox {
                objectName: "preferences.sideBarSide"
                model: [qsTr("Left"), qsTr("Right")]
                currentIndex: Preferences.sideBarOnLeft ? 0 : 1
                onActivated: index => Preferences.sideBarSide = index === 0 ? "Left" : "Right"
            }

            RowLabel {
                text: qsTr("Auto collapse") + ":"
            }
            RowCheckBox {
                objectName: "preferences.autoCollapse"
                checked: Preferences.autoCollapse
                onToggled: Preferences.autoCollapse = checked
                ToolTip.text: qsTr("Auto collapse for side bar groups")
            }
        }

        // Projects: only the defaults a new project takes. A project keeps its own: its s.u. rule on the Project
        // page's Extra tab, its report's libraries on the Report page.
        RowGrid {
            RowLabel {
                text: qsTr("New projects' uncertainties") + ":"
            }
            RowBox {
                objectName: "preferences.newProjectSuRule"
                model: [qsTr("IUCr recommendation"), qsTr("Always 2 digits")]
                currentIndex: Preferences.newProjectSuRule === "iucr_99" ? 1 : 0
                onActivated: index => Preferences.newProjectSuRule = index === 1 ? "iucr_99" : "iucr_19"
                ToolTip.text: qsTr("How a new project writes values with a standard uncertainty: 1 digit, or 2 from 10 to 19, or always 2")
            }

            RowLabel {
                text: qsTr("New reports' libraries") + ":"
            }
            RowBox {
                objectName: "preferences.newReportLibraries"
                model: [qsTr("Online"), qsTr("Embedded")]
                currentIndex: Preferences.newReportLibraries === "embedded" ? 1 : 0
                onActivated: index => Preferences.newReportLibraries = index === 1 ? "embedded" : "online"
                ToolTip.text: qsTr("Whether a new project's HTML reports load plotly.js and three.js from the web or carry them, so they open offline")
            }
        }

        // Experimental: zoom and language are not available yet — the default zoom, English.
        RowGrid {
            RowLabel {
                enabled: false
                text: qsTr("Zoom") + ":"
            }
            NotAvailable {
                RowBox {
                    objectName: "preferences.zoom"
                    enabled: false
                    model: ["100%"]
                }
            }

            RowLabel {
                enabled: false
                text: qsTr("Language") + ":"
            }
            NotAvailable {
                RowBox {
                    objectName: "preferences.language"
                    enabled: false
                    model: [qsTr("English")]
                }
            }
        }

        // Develop, as the base's
        RowGrid {
            RowLabel {
                enabled: false
                text: qsTr("Logging to") + ":"
            }
            RowBox {
                enabled: false
                model: ["Disabled", "Terminal", "File"]
                currentIndex: 1
            }

            RowLabel {
                text: qsTr("Logging level") + ":"
            }
            RowBox {
                model: ["Debug", "Info", "Error", "Disabled"]
                currentIndex: model.indexOf(EaGlobals.Vars.loggingLevel)
                onActivated: EaGlobals.Vars.loggingLevel = currentValue
            }

            // The engine's threads for every fill: Auto (the engine's policy) or a count, saved per machine.
            RowLabel {
                text: qsTr("Engine threads") + ":"
            }
            RowBox {
                objectName: "preferences.engineThreads"
                enabled: ApplicationInfo.engineThreadsSelectable
                model: {
                    if (!ApplicationInfo.engineThreadsSelectable)
                        return [qsTr("1 (single-thread build)")];
                    const counts = [qsTr("Auto")];
                    for (let count = 1; count <= ApplicationInfo.engineThreadsMaximum; ++count)
                        counts.push(String(count));
                    return counts;
                }
                currentIndex: ApplicationInfo.engineThreadsSelectable ? Math.min(Preferences.engineThreads, ApplicationInfo.engineThreadsMaximum) : 0
                onActivated: index => {
                    if (ApplicationInfo.engineThreadsSelectable)
                        Preferences.engineThreads = index;
                }
            }

            // What the app runs on and with, to read and to copy (the owner, 2026-10-06).
            RowLabel {
                text: qsTr("Diagnostics") + ":"
            }
            RowButton {
                objectName: "preferences.diagnostics"
                text: qsTr("Show")
                onClicked: diagnostics.open()
            }

            // ADR-0031 §5: where the app's settings are kept, the folder holding them and a reset. A long path is cut in
            // its middle, and the whole of it is the tooltip.
            RowLabel {
                text: qsTr("Settings") + ":"
            }
            Column {
                spacing: dialog.stackSpacing

                EaElements.Label {
                    id: settingsPath

                    objectName: "preferences.settingsPath"
                    width: dialog.controlWidth
                    topPadding: dialog.lineOffset
                    elide: Text.ElideMiddle
                    text: WebFiles.available ? qsTr("Stored in this browser") : ApplicationInfo.localPath(EaGlobals.Vars.settingsFile)

                    HoverHandler {
                        id: pathHover
                    }
                    EaElements.ToolTip {
                        text: settingsPath.text
                        visible: pathHover.hovered && settingsPath.truncated && EaGlobals.Vars.showToolTips
                    }
                }
                RowButton {
                    objectName: "preferences.openSettingsFolder"
                    visible: !WebFiles.available
                    text: qsTr("Open folder")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.folderOf(EaGlobals.Vars.settingsFile))
                }
                RowButton {
                    objectName: "preferences.resetSettings"
                    text: qsTr("Reset to defaults")
                    onClicked: resetConfirm.open()
                }
            }
        }
    }

    AppDialog {
        id: resetConfirm
        objectName: "preferences.resetConfirm"
        parent: Overlay.overlay
        title: qsTr("Reset the settings")
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: Preferences.resetToDefaults()

        EaElements.Label {
            text: qsTr("Set every preference and page setting back to its default? The open project is not changed.")
        }
    }

    FontMetrics {
        id: boxMetrics

        font: themeBox.font
    }
    FontMetrics {
        id: lineMetrics

        font: themeLabel.font
    }

    DiagnosticsDialog {
        id: diagnostics
        parent: Overlay.overlay
    }
}
