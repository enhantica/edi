// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

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
        return ApplicationInfo.preferenceItemsUnder(item, wanted);
    }
    // The width a box needs for its longest item: its paddings, its text's own and its arrow, which the box draws inside
    // its content.
    function boxNeed(box) {
        return ApplicationInfo.preferenceBoxNeed(box);
    }
    // The width a button needs for its text with an em at each side (its content reports no width of its own).
    function buttonNeed(button) {
        return ApplicationInfo.preferenceButtonNeed(button);
    }

    readonly property var rowItems: ApplicationInfo.preferenceRowItems()
    readonly property real labelWidth: ApplicationInfo.preferenceRowWidth(false)
    readonly property real controlWidth: ApplicationInfo.preferenceRowWidth(true)
    readonly property real stackSpacing: EaStyle.Sizes.fontPixelSize * 0.5
    readonly property real rowHeight: themeBox.implicitHeight
    // A label's line, centred on a control's height.
    readonly property real lineOffset: Math.max(0, (rowHeight - lineMetrics.height) / 2)

    objectName: "preferences"
    visible: Preferences.dialogShown
    onClosed: ApplicationInfo.preferencesClosed()
    onOpened: Session.assistant.refreshSkillSources()

    title: qsTr("Preferences")
    standardButtons: Dialog.Ok

    contentWidth: Math.max(bar.implicitWidth, pages.leftPadding + pages.rightPadding + labelWidth + EaStyle.Sizes.fontPixelSize + controlWidth)
    // As tall as the tallest tab's rows need, so no tab's last row is cut (the owner, 2026-10-13).
    contentHeight: ApplicationInfo.preferenceContentHeight()

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
            objectName: "preferences.tab.aiAssistance"
            fontIcon: "robot"
            text: qsTr("AI assistance")
            enabled: ApplicationInfo.assistantAvailable
            ToolTip.text: ApplicationInfo.assistantUnavailableReason
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

            // Fitting works from every page's status bar, so whether a fit opens its results is an app preference
            // (the owner, 2026-10-26).
            RowLabel {
                text: qsTr("Show fit results after fitting") + ":"
            }
            RowCheckBox {
                objectName: "preferences.showFitResults"
                checked: Preferences.showFitResults
                onToggled: Preferences.showFitResults = checked
                ToolTip.text: qsTr("Open the results window when a fit ends; the fit status in the status bar opens it too")
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

        // Appearance: the theme, the colour scheme, the sidebar's side and whether one sidebar group is open at a time; no 1D plotting row.
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
                onActivated: index => ApplicationInfo.preferenceActivated(index, 0)
            }

            // The figure palette, one for experiments and structures (the owner, 2026-10-26), the palettes' tokens and
            // names (edi::colour_scheme_names) in the order the core lists them, with its colour order under it; then
            // the Stacked view's lines and the Map's colour map, as their charts offer them.
            RowLabel {
                text: qsTr("Palette") + ":"
            }
            Column {
                spacing: dialog.stackSpacing

                RowBox {
                    readonly property var schemes: ApplicationInfo.colourSchemes

                    objectName: "preferences.colours"
                    model: ApplicationInfo.colourSchemeTitles
                    currentIndex: Math.max(0, schemes.indexOf(ApplicationInfo.colourSchemeOrDefault(Preferences.colourScheme)))
                    onActivated: index => ApplicationInfo.preferenceActivated(index, 1)
                    ToolTip.text: qsTr("The colours of experiments and structures: their icons, patterns, Bragg ticks and curves")
                }
                PaletteStrip {
                    objectName: "preferences.colourOrder"
                }
            }
            RowLabel {
                text: qsTr("Stacked") + ":"
            }
            RowBox {
                readonly property var choices: ApplicationInfo.preferenceStackedChoices()
                // Empty follows the palette.
                readonly property string current: Preferences.scanStackedPalette !== "" ? Preferences.scanStackedPalette : Preferences.colourScheme

                objectName: "preferences.stackedColours"
                model: ApplicationInfo.preferenceColourTitles()
                currentIndex: Math.max(0, choices.indexOf(current))
                onActivated: index => ApplicationInfo.preferenceActivated(index, 2)
                ToolTip.text: qsTr("The Stacked view's patterns")
            }
            RowLabel {
                text: qsTr("Map") + ":"
            }
            RowBox {
                readonly property var choices: ApplicationInfo.scanColourMaps

                objectName: "preferences.mapColours"
                model: ApplicationInfo.preferenceColourTitles()
                currentIndex: Math.max(0, choices.indexOf(Preferences.scanMapColours))
                onActivated: index => ApplicationInfo.preferenceActivated(index, 3)
                ToolTip.text: qsTr("The Map's colour map, also chosen on the Map's toolbar")
            }
            RowLabel {
                text: qsTr("When a curve is hidden") + ":"
            }
            RowBox {
                readonly property list<string> choices: ["keep", "fit"]

                objectName: "preferences.hiddenRange"
                model: [qsTr("Keep the y range"), qsTr("Fit the range to visible curves")]
                currentIndex: Math.max(0, choices.indexOf(Preferences.chartHiddenRange))
                onActivated: index => ApplicationInfo.preferenceActivated(index, 4)
                ToolTip.text: qsTr("What the pattern chart's y range does when a click on its legend hides or shows a curve")
            }

            RowLabel {
                text: qsTr("Workflow sidebar side") + ":"
            }
            RowBox {
                objectName: "preferences.sideBarSide"
                model: [qsTr("Left"), qsTr("Right")]
                currentIndex: Preferences.sideBarOnLeft ? 0 : 1
                onActivated: index => ApplicationInfo.preferenceActivated(index, 6)
            }

            RowLabel {
                visible: !ApplicationInfo.assistantAvailable
                text: qsTr("Assistant") + ":"
            }
            EaElements.Label {
                objectName: "preferences.assistantUnavailableReason"
                visible: !ApplicationInfo.assistantAvailable
                width: dialog.controlWidth
                text: ApplicationInfo.assistantUnavailableReason
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }

            RowLabel {
                text: qsTr("One sidebar group open at a time") + ":"
            }
            RowCheckBox {
                objectName: "preferences.autoCollapse"
                checked: Preferences.autoCollapse
                onToggled: Preferences.autoCollapse = checked
                ToolTip.text: qsTr("Opening a group in the sidebar closes the other open groups")
            }

            RowLabel {
                text: qsTr("Text tab shows") + ":"
            }
            RowBox {
                readonly property list<string> choices: ["editable", "everything"]

                objectName: "preferences.textShow"
                model: [qsTr("Editable"), qsTr("Everything")]
                currentIndex: Math.max(0, choices.indexOf(Preferences.textShow))
                // Through the Text tabs, which settle an unapplied edit first; until then the box shows the setting.
                onActivated: index => ApplicationInfo.textTabShowChoice(index, () => {
                        currentIndex = Qt.binding(() => Math.max(0, choices.indexOf(Preferences.textShow)));
                    })
                ToolTip.text: qsTr("What every Text tab shows: the categories you can edit, or also the measured data and results, read-only")
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
                onActivated: index => ApplicationInfo.preferenceActivated(index, 7)
                ToolTip.text: qsTr("How a new project writes values with a standard uncertainty: 1 digit, or 2 from 10 to 19, or always 2")
            }

            RowLabel {
                text: qsTr("New reports' libraries") + ":"
            }
            RowBox {
                objectName: "preferences.newReportLibraries"
                model: [qsTr("Online"), qsTr("Embedded")]
                currentIndex: Preferences.newReportLibraries === "embedded" ? 1 : 0
                onActivated: index => ApplicationInfo.preferenceActivated(index, 8)
                ToolTip.text: qsTr("Whether a new project's HTML reports load plotly.js and three.js from the web or carry them, so they open offline")
            }
        }

        // The online sources Load ▾ From web… searches (ADR-0068): COD and EasyDiffraction's collection are built
        // in; a row can be disabled, and user rows added, edited or removed. A run started with --online-source or
        // EDI_ONLINE_SOURCES shows that URL in place of the stored one.
        Column {
            width: parent.width
            spacing: AppSizes.unit
            EaElements.Label {
                width: parent.width
                text: qsTr("Online sources")
                font.bold: true
            }
            DataTable {
                id: onlineTable
                objectName: "preferences.online.sources"
                width: parent.width
                maxRowCountShow: 6
                sourceModel: Session.onlineSources
                defaultInfoText: qsTr("No online sources")
                columns: [numberColumnWidth, AppSizes.dataColumnWidth * 1.8, -1, AppSizes.dataColumnWidth * 1.6, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]
                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {
                        text: qsTr("Name")
                        horizontalAlignment: Text.AlignLeft
                    }
                    EaComponents.ListViewLabel {
                        text: qsTr("URL")
                        horizontalAlignment: Text.AlignLeft
                    }
                    EaComponents.ListViewLabel {
                        text: qsTr("Holds")
                        horizontalAlignment: Text.AlignLeft
                    }
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {}
                }
                delegate: TableRow {
                    id: onlineRow
                    required property string id
                    required property string name
                    required property string url
                    required property var kinds
                    required property bool builtin
                    required property var model
                    required property bool overridden
                    EaComponents.ListViewLabel {
                        text: onlineRow.index + 1
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                    }
                    TextCell {
                        objectName: "preferences.online.source.name." + onlineRow.id
                        horizontalAlignment: Text.AlignLeft
                        value: onlineRow.name
                        enabled: !onlineRow.builtin
                        onCommitted: text => Session.onlineSources.setName(onlineRow.id, text)
                    }
                    TextCell {
                        objectName: "preferences.online.source.url." + onlineRow.id
                        horizontalAlignment: Text.AlignLeft
                        value: onlineRow.url
                        enabled: !onlineRow.builtin && !onlineRow.overridden
                        ToolTip.text: onlineRow.overridden ? qsTr("Set for this run by --online-source or EDI_ONLINE_SOURCES") : onlineRow.url
                        onCommitted: text => Session.onlineSources.setUrl(onlineRow.id, text)
                    }
                    EaComponents.ListViewLabel {
                        objectName: "preferences.online.source.kinds." + onlineRow.id
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideRight
                        text: onlineRow.kinds.map(k => k === "structure" ? qsTr("structures") : k === "experiment" ? qsTr("experiments") : qsTr("data")).join(", ")
                    }
                    EaComponents.ListViewButton {
                        objectName: "preferences.online.source.enabled." + onlineRow.id
                        fontIcon: onlineRow.model.enabled ? "toggle-on" : "toggle-off"
                        ToolTip.text: onlineRow.model.enabled ? qsTr("Leave this source out of the From web… popup") : qsTr("Offer this source in the From web… popup")
                        onClicked: Session.onlineSources.setEnabled(onlineRow.id, !onlineRow.model.enabled)
                    }
                    EaComponents.ListViewButton {
                        objectName: "preferences.online.source.remove." + onlineRow.id
                        fontIcon: "minus-circle"
                        enabled: !onlineRow.builtin
                        ToolTip.text: onlineRow.builtin ? qsTr("A built-in source cannot be removed, only disabled") : qsTr("Remove this source")
                        onClicked: Session.onlineSources.remove(onlineRow.id)
                    }
                }
            }
            EaElements.SideBarButton {
                objectName: "preferences.online.sources.add"
                width: dialog.controlWidth
                text: qsTr("Add online source")
                fontIcon: "plus-circle"
                ToolTip.text: qsTr("Add a collection to search: a URL holding an index.json and the files it names")
                onClicked: Session.onlineSources.add()
            }
        }

        ScrollView {
            id: aiPage
            implicitHeight: Math.min(aiContent.implicitHeight, Math.max(0, dialog.parent.height - bar.implicitHeight - AppSizes.unit * 8))
            readonly property var original: Session.assistant
            property string copyError: ""
            onOriginalChanged: ApplicationInfo.preferenceAssistantChanged()
            function copyDiagnostics(button, report) {
                ApplicationInfo.preferenceCopyDiagnostics(button, report);
            }
            clip: true
            Column {
                id: aiContent
                width: Math.max(0, aiPage.availableWidth)
                spacing: AppSizes.unit
                EaElements.Label {
                    width: parent.width
                    text: qsTr("Skill sources")
                    font.bold: true
                }
                DataTable {
                    id: sourceTable
                    objectName: "preferences.ai.sources"
                    width: parent.width
                    maxRowCountShow: 5
                    sourceModel: aiPage.original ? aiPage.original.skillSources : null
                    defaultInfoText: qsTr("No skill sources")
                    columns: [numberColumnWidth, -1, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]
                    header: EaComponents.ListViewHeader {
                        EaComponents.ListViewLabel {}
                        EaComponents.ListViewLabel {
                            text: qsTr("Source")
                            horizontalAlignment: Text.AlignLeft
                        }
                        EaComponents.ListViewLabel {}
                        EaComponents.ListViewLabel {}
                    }
                    delegate: TableRow {
                        id: sourceRow
                        readonly property string sourceId: model.id || ""
                        required property string label
                        required property string path
                        required property bool builtin
                        required property string status
                        required property var model
                        readonly property var original: aiPage.original
                        property int presentation: 0
                        onSourceIdChanged: ApplicationInfo.preferenceSourceRevision()
                        onOriginalChanged: ApplicationInfo.preferenceSourceRevision()
                        EaComponents.ListViewLabel {
                            text: sourceRow.index + 1
                            horizontalAlignment: Text.AlignHCenter
                            marksCurrentRow: true
                        }
                        EaComponents.ListViewLabel {
                            objectName: "preferences.ai.source.label." + sourceRow.sourceId
                            text: sourceRow.builtin ? qsTr("EasyDiffraction") : sourceRow.label.startsWith("https://github.com/") ? sourceRow.label : sourceRow.path
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            ToolTip.text: text + (sourceRow.status.length ? "\n" + sourceRow.status : "")
                        }
                        EaComponents.ListViewButton {
                            id: sourceEnabled
                            objectName: "preferences.ai.source.enabled." + sourceRow.sourceId
                            fontIcon: sourceRow.model.enabled ? "toggle-on" : "toggle-off"
                            enabled: ApplicationInfo.assistantAvailable && sourceRow.original && !sourceRow.original.canCancel
                            ToolTip.text: sourceRow.model.enabled ? qsTr("Disable this skill source") : qsTr("Enable this skill source")
                            Accessible.name: ToolTip.text
                            Accessible.checkable: true
                            Accessible.checked: sourceRow.model.enabled
                            property var gesture: null
                            onPressed: ApplicationInfo.preferenceSourceGesture(false, true)
                            onCanceled: gesture = null
                            onClicked: ApplicationInfo.preferenceSourceGesture(false, false)
                            Connections {
                                target: sourceRow.original
                                function onSkillSourcesChanged() {
                                    sourceEnabled.gesture = null;
                                }
                            }
                        }
                        EaComponents.ListViewButton {
                            id: sourceRemove
                            objectName: "preferences.ai.source.remove." + sourceRow.sourceId
                            fontIcon: "minus-circle"
                            enabled: ApplicationInfo.assistantAvailable && !sourceRow.builtin && sourceRow.original && !sourceRow.original.canCancel
                            ToolTip.text: sourceRow.builtin ? qsTr("The built-in source cannot be removed") : qsTr("Remove this skill source")
                            Accessible.name: ToolTip.text
                            property var gesture: null
                            onPressed: ApplicationInfo.preferenceSourceGesture(true, true)
                            onCanceled: gesture = null
                            onClicked: ApplicationInfo.preferenceSourceGesture(true, false)
                            Connections {
                                target: sourceRow.original
                                function onSkillSourcesChanged() {
                                    sourceRemove.gesture = null;
                                }
                            }
                        }
                    }
                }
                Row {
                    width: parent.width
                    spacing: AppSizes.unit
                    EaElements.SideBarButton {
                        objectName: "preferences.ai.sources.add"
                        width: (parent.width - parent.spacing) / 2
                        text: qsTr("Add skill source")
                        fontIcon: "plus-circle"
                        enabled: ApplicationInfo.assistantAvailable && !Session.assistant.canCancel && !Session.assistant.skillSourceImporting
                        onClicked: ApplicationInfo.preferenceBeginSourceSelection(false)
                    }
                    EaElements.SideBarButton {
                        objectName: "preferences.ai.sources.web"
                        width: (parent.width - parent.spacing) / 2
                        text: Session.assistant.skillSourceImporting ? qsTr("Cancel web import") : qsTr("Add skills from web")
                        fontIcon: Session.assistant.skillSourceImporting ? "times-circle" : "globe"
                        enabled: ApplicationInfo.assistantAvailable && !Session.assistant.canCancel
                        onClicked: ApplicationInfo.preferenceBeginSourceSelection(true)
                    }
                }
                EaElements.Label {
                    width: parent.width
                    text: Session.assistant.skillSourceError
                    visible: text.length > 0
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: EaStyle.Colors.red
                }
                EaElements.Label {
                    text: qsTr("Diagnostics")
                    font.bold: true
                }
                EaElements.CheckBox {
                    objectName: "preferences.ai.copyTechnicalDetails"
                    text: qsTr("Include technical details when copying steps")
                    checked: Preferences.assistantCopyTechnicalDetails
                    onToggled: Preferences.assistantCopyTechnicalDetails = checked
                }
                Row {
                    width: parent.width
                    spacing: AppSizes.unit
                    EaElements.SideBarButton {
                        id: copyWorkReport
                        objectName: "preferences.ai.workReport"
                        width: (parent.width - parent.spacing) / 2
                        property bool copied: false
                        text: copied ? qsTr("Copied") : qsTr("Copy work report")
                        fontIcon: copied ? "check" : "copy"
                        contentItem: Item {
                            implicitWidth: copyWorkReportContent.implicitWidth
                            Row {
                                id: copyWorkReportContent
                                anchors.centerIn: parent
                                spacing: AppSizes.unit * 0.5
                                EaElements.Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: copyWorkReport.fontIcon
                                    font.family: EaStyle.Fonts.iconsFamily
                                    color: copyWorkReport.copied ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                                    Accessible.ignored: true
                                }
                                EaElements.Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: copyWorkReport.text
                                    color: copyWorkReport.copied ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                                }
                            }
                        }
                        onClicked: aiPage.copyDiagnostics(copyWorkReport, true)
                        Timer {
                            id: reportCopyFeedback
                            interval: EaStyle.Times.introAnimation
                            onTriggered: copyWorkReport.copied = false
                        }
                    }
                    EaElements.SideBarButton {
                        id: copyConnection
                        objectName: "preferences.ai.copyConnection"
                        width: (parent.width - parent.spacing) / 2
                        property bool copied: false
                        text: copied ? qsTr("Copied") : qsTr("Copy connection details")
                        fontIcon: copied ? "check" : "copy"
                        contentItem: Item {
                            implicitWidth: copyConnectionContent.implicitWidth
                            Row {
                                id: copyConnectionContent
                                anchors.centerIn: parent
                                spacing: AppSizes.unit * 0.5
                                EaElements.Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: copyConnection.fontIcon
                                    font.family: EaStyle.Fonts.iconsFamily
                                    color: copyConnection.copied ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                                    Accessible.ignored: true
                                }
                                EaElements.Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: copyConnection.text
                                    color: copyConnection.copied ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                                }
                            }
                        }
                        onClicked: aiPage.copyDiagnostics(copyConnection, false)
                        Timer {
                            id: connectionCopyFeedback
                            interval: EaStyle.Times.introAnimation
                            onTriggered: copyConnection.copied = false
                        }
                    }
                }
                EaElements.Label {
                    width: parent.width
                    text: aiPage.copyError
                    visible: text.length > 0
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: EaStyle.Colors.red
                }
                EaElements.Label {
                    text: qsTr("History")
                    font.bold: true
                }
                EaElements.SideBarButton {
                    objectName: "preferences.ai.clearCachedHistory"
                    width: parent.width
                    text: Session.assistant.cachedHistoryClearing ? qsTr("Clearing cached chat history…") : qsTr("Clear cached chat history")
                    fontIcon: "eraser"
                    enabled: !Session.assistant.canCancel && !Session.assistant.cachedHistoryClearing
                    ToolTip.text: qsTr("Clear the app's saved chat display only. Projects, reports, runtime sessions and sign-in are kept.")
                    onClicked: Session.assistant.clearCachedHistory()
                }
                EaElements.Label {
                    width: parent.width
                    text: Session.assistant.cachedHistoryError
                    visible: text.length > 0
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: EaStyle.Colors.red
                }
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

        // Develop, as the base's. The run log goes to the terminal and to a file of each run (edi ADR-0062).
        RowGrid {
            RowLabel {
                text: qsTr("Logging level") + ":"
            }
            RowBox {
                objectName: "preferences.loggingLevel"
                model: ["Debug", "Info", "Error", "Disabled"]
                currentIndex: model.indexOf(Preferences.loggingLevel)
                onActivated: Preferences.loggingLevel = currentValue
            }

            // Help and feedback's service (edi ADR-0063): empty keeps Send off.
            RowLabel {
                text: qsTr("Feedback address") + ":"
            }
            EaElements.TextField {
                objectName: "preferences.feedbackEndpoint"
                width: dialog.controlWidth
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Not set up")
                text: Preferences.feedbackEndpoint
                onEditingFinished: Preferences.feedbackEndpoint = text.trim()
            }

            // The engine's threads for every fill: Auto (the engine's policy) or a count, saved per machine.
            RowLabel {
                text: qsTr("Engine threads") + ":"
            }
            RowBox {
                objectName: "preferences.engineThreads"
                enabled: ApplicationInfo.engineThreadsSelectable
                model: ApplicationInfo.preferenceEngineThreads()
                currentIndex: ApplicationInfo.engineThreadsSelectable ? Math.min(Preferences.engineThreads, ApplicationInfo.engineThreadsMaximum) : 0
                onActivated: index => ApplicationInfo.preferenceActivated(index, 9)
            }

            // What Qt draws with (edi ADR-0041): its graphics API and renderer, read in the first frame, and whether that
            // means no GPU.
            RowLabel {
                text: qsTr("Graphics") + ":"
            }
            EaElements.Label {
                objectName: "preferences.graphics"
                width: dialog.controlWidth
                topPadding: dialog.lineOffset
                wrapMode: Text.Wrap
                text: !RenderingInfo.detected ? qsTr("Not detected yet") : (RenderingInfo.renderer !== "" ? RenderingInfo.api + ", " + RenderingInfo.renderer : RenderingInfo.api) + " · " + (RenderingInfo.software ? qsTr("software rendering, no GPU") : qsTr("GPU"))
            }

            // How the Stacked view draws its lines: on the GPU, or painted, which is faster without one; Automatic takes
            // the graphics above. Saved per machine.
            RowLabel {
                text: qsTr("Scan views") + ":"
            }
            RowBox {
                objectName: "preferences.scanRenderer"
                readonly property var values: ["auto", "gpu", "software"]
                model: [qsTr("Automatic"), qsTr("GPU"), qsTr("Software painter")]
                currentIndex: Math.max(0, values.indexOf(Preferences.scanRenderer))
                onActivated: index => ApplicationInfo.preferenceActivated(index, 10)
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
        id: webSource
        objectName: "preferences.ai.sources.webDialog"
        property var selection: null
        readonly property string intent: selection ? selection.id : ""
        readonly property var original: selection ? selection.owner : null
        parent: Overlay.overlay
        title: qsTr("Add skills from web")
        standardButtons: Dialog.Ok | Dialog.Cancel
        // The FIRST footer derives its available width from this dialog. Give
        // the dialog one intrinsic upstream width, independent of that footer.
        width: contentItem.implicitWidth + leftPadding + rightPadding
        contentItem: Item {
            implicitWidth: dialog.controlWidth
            implicitHeight: webContent.implicitHeight
            Column {
                id: webContent
                width: parent.width
                spacing: AppSizes.unit
                EaElements.Label {
                    width: parent.width
                    text: qsTr("Public GitHub repository or skill folder URL. Companion files are captured; repository code is never run.")
                    wrapMode: Text.Wrap
                }
                EaElements.TextField {
                    id: sourceUrl
                    objectName: "preferences.ai.sources.webUrl"
                    width: parent.width
                    placeholderText: "https://github.com/owner/repo/tree/main/skills"
                    selectByMouse: true
                }
            }
        }
        onAccepted: ApplicationInfo.preferenceCompleteSourceSelection(true, true)
        onRejected: ApplicationInfo.preferenceCompleteSourceSelection(true, false)
        Component.onDestruction: ApplicationInfo.preferenceCompleteSourceSelection(true, false)
        Connections {
            target: webSource.original
            function onSkillSourceSelectionRetired(token) {
                ApplicationInfo.preferenceRetireSourceSelection(token, true);
            }
        }
    }

    FolderDialog {
        id: sourcesFolder
        objectName: "preferences.ai.sources.folder"
        property var selection: null
        readonly property string intent: selection ? selection.id : ""
        readonly property var original: selection ? selection.owner : null
        title: qsTr("Choose a skill folder or collection")
        onAccepted: ApplicationInfo.preferenceCompleteSourceSelection(false, true)
        onRejected: ApplicationInfo.preferenceCompleteSourceSelection(false, false)
        Component.onDestruction: ApplicationInfo.preferenceCompleteSourceSelection(false, false)
        Connections {
            target: sourcesFolder.original
            function onSkillSourceSelectionRetired(token) {
                ApplicationInfo.preferenceRetireSourceSelection(token, false);
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
