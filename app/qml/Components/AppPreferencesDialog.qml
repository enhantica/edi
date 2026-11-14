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

// The application preferences (edi ADR-0017 §12, ADR-0084): seven tabs, each one grid of two equal columns. Every
// control has its label above it, a choice is a box rather than a checkbox, explanations are tooltips, and every
// colour choice shows its colours in a strip under its box. Groups have a title with an icon, without a frame.
AppDialog {
    id: dialog

    signal maintenanceRequested

    // A disabled control takes no hover, so its tooltip hangs on the item around it (§4): why it is disabled.
    component NotAvailable: Item {
        id: notAvailable
        property string reason: qsTr("Not available yet")

        implicitWidth: childrenRect.width
        implicitHeight: childrenRect.height

        HoverHandler {
            id: hover
        }
        EaElements.ToolTip {
            text: notAvailable.reason
            requested: hover.hovered
        }
    }
    // A group's title: its icon, then its name, not foldable and without a frame, as a sidebar group's title reads.
    // A later group's title has one more row space above it than below, so it reads with the controls under it.
    component GroupTitle: Column {
        id: groupTitle

        property string icon
        property string text
        property bool first: true

        topPadding: first ? 0 : dialog.rowSpacing

        Row {
            spacing: EaStyle.Sizes.fontPixelSize * 0.5

            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                font.family: EaStyle.Fonts.iconsFamily
                text: groupTitle.icon
            }
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: groupTitle.text
            }
        }
    }
    // A control's label, above it.
    component FieldLabel: EaElements.Label {
        width: dialog.columnWidth
        bottomPadding: dialog.labelSpacing
        elide: Text.ElideRight
        color: EaStyle.Colors.themeForegroundMinor
    }
    // A long choice ends with "…", as long table cells do.
    component FieldBox: EaElements.ComboBox {
        width: dialog.columnWidth
        elide: Text.ElideRight
    }
    component FieldButton: EaElements.SideBarButton {
        width: dialog.columnWidth
        height: dialog.rowHeight
    }
    // A number box whose minus and plus sit at its right, the plus where a box's arrow is, at the arrow's size.
    component FieldSpinBox: EaElements.SpinBox {
        id: spin

        // The right edge of a box's arrow, and its size.
        readonly property real iconRight: themeBox.indicator.x + themeBox.indicator.width
        readonly property real iconSize: EaStyle.Sizes.fontPixelSize * 0.8

        width: dialog.columnWidth
        // The text stops short of the minus and plus, so a press on them reaches the spin box, which steps the
        // value and repeats while held, instead of the text field selecting its text.
        rightPadding: EaStyle.Sizes.fontPixelSize * 3.5
        // Plain whole numbers, without a thousands separator.
        textFromValue: value => String(value)
        valueFromText: text => parseInt(text, 10)
        contentItem: TextInput {
            leftPadding: EaStyle.Sizes.fontPixelSize * 0.75
            readOnly: !spin.editable
            validator: spin.validator
            inputMethodHints: Qt.ImhDigitsOnly
            font: spin.font
            text: spin.displayText
            color: EaStyle.Colors.themeForeground
            selectionColor: EaStyle.Colors.themeAccent
            selectedTextColor: EaStyle.Colors.themeBackground
            verticalAlignment: Qt.AlignVCenter
            selectByMouse: true
        }
        up.indicator: EaElements.Label {
            x: spin.iconRight - width
            height: spin.height
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: spin.iconSize
            text: "plus"
        }
        down.indicator: EaElements.Label {
            x: spin.iconRight - width - EaStyle.Sizes.fontPixelSize * 1.5
            height: spin.height
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: spin.iconSize
            text: "minus"
        }
    }
    // A value to read: plain text on a box's row height, without a frame, so it never looks like an input. A long
    // value ends with "…" and shows whole as the tooltip.
    component ReadOnlyField: EaElements.Label {
        id: readOnly

        property string toolTipText: text

        width: dialog.columnWidth
        height: dialog.rowHeight
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        textFormat: Text.PlainText

        EaElements.ToolTip {
            text: readOnly.toolTipText
            requested: readOnlyHover.hovered
        }
        HoverHandler {
            id: readOnlyHover
        }
    }
    // One column of a tab, its rows the same distance apart.
    component TabColumn: Column {
        width: dialog.columnWidth
        spacing: dialog.rowSpacing
    }
    // A tab: two columns side by side, or rows that span both.
    component TabRow: Row {
        spacing: dialog.columnSpacing
    }
    // A label with its control (and a strip, if any) under it, as one row of a column.
    component Field: Column {
        property alias label: fieldLabel.text

        width: dialog.columnWidth

        FieldLabel {
            id: fieldLabel
        }
    }

    readonly property real columnSpacing: EaStyle.Sizes.fontPixelSize * 2
    readonly property real rowSpacing: EaStyle.Sizes.fontPixelSize
    readonly property real labelSpacing: EaStyle.Sizes.fontPixelSize * 0.3
    readonly property real contentRowWidth: Math.max(0, pages.availableWidth)
    readonly property real columnWidth: Math.floor((contentRowWidth - columnSpacing) / 2)
    readonly property real rowHeight: themeBox.implicitHeight
    readonly property string updatesOff: qsTr("Available in installed desktop releases")
    readonly property real stripSpacing: EaStyle.Sizes.fontPixelSize * 0.25
    // One line of an online source's three.
    readonly property real onlineLineHeight: Math.round(EaStyle.Sizes.fontPixelSize * 1.6)

    objectName: "preferences"
    visible: Preferences.dialogShown
    onClosed: ApplicationInfo.preferencesClosed()
    onOpened: if (ApplicationInfo.assistantBuilt)
        Session.assistant.refreshSkillSources()
    // A page's Performance line opens the dialog on that tab.
    onAboutToShow: {
        for (let index = 0; index < bar.count; ++index) {
            if (Preferences.dialogTab !== "" && bar.itemAt(index).objectName === "preferences.tab." + Preferences.dialogTab)
                bar.currentIndex = index;
        }
        Preferences.dialogTab = "";
        scanWorkersBox.show();
    }

    title: qsTr("Preferences")
    standardButtons: Dialog.Ok

    // 720 px wide, so the online sources table fits its columns without wide gaps.
    width: 720
    // As tall as the tallest tab's rows need, so no tab's last row is cut.
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
            width: bar.width / bar.count
            objectName: "preferences.tab.appearance"
            fontIcon: "paint-brush"
            text: qsTr("Appearance")
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.interface"
            fontIcon: "sliders-h"
            text: qsTr("Interface")
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.projects"
            fontIcon: "archive"
            text: qsTr("Projects")
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.performance"
            fontIcon: "tachometer-alt"
            text: qsTr("Performance")
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.updates"
            fontIcon: "cloud-download-alt"
            text: qsTr("Updates")
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.aiAssistance"
            fontIcon: "robot"
            text: qsTr("AI assistance")
            enabled: ApplicationInfo.assistantAvailable
            ToolTip.text: ApplicationInfo.assistantUnavailableReason
        }
        EaElements.AppBarTabButton {
            width: bar.width / bar.count
            objectName: "preferences.tab.advanced"
            fontIcon: "cogs"
            text: qsTr("Advanced")
        }
    }

    SwipeView {
        id: pages

        anchors.top: bar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        topPadding: EaStyle.Sizes.fontPixelSize
        leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
        rightPadding: EaStyle.Sizes.fontPixelSize * 0.5
        bottomPadding: EaStyle.Sizes.fontPixelSize * 2

        currentIndex: bar.currentIndex
        interactive: false
        clip: true
        // A gap between the pages, so no tab's controls reach into the shown one.
        spacing: EaStyle.Sizes.fontPixelSize * 2
        // A tab shows at once, without the swipe's slide.
        Component.onCompleted: (pages.contentItem as ListView).highlightMoveDuration = 0

        // Appearance: the theme, then the structure view's arrows, then the charts' behaviour and colours. Rows with
        // colour strips pair up.
        TabColumn {
            width: dialog.contentRowWidth

            GroupTitle {
                icon: "adjust"
                text: qsTr("General")
            }
            TabRow {
                Field {
                    label: qsTr("Theme")
                    FieldBox {
                        id: themeBox

                        objectName: "preferences.theme"
                        model: [qsTr("Light"), qsTr("Dark"), qsTr("System")]
                        currentIndex: EaStyle.Colors.theme === EaStyle.Colors.DarkTheme ? 1 : EaStyle.Colors.theme === EaStyle.Colors.SystemTheme ? 2 : 0
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 0)
                    }
                }
            }
            GroupTitle {
                first: false
                icon: "cubes"
                text: qsTr("Structure view")
            }
            TabRow {
                Field {
                    label: qsTr("Magnetic moment arrows")
                    spacing: dialog.stripSpacing
                    FieldBox {
                        readonly property var schemes: ["atom", "greyed", "single"]

                        objectName: "preferences.momentColours"
                        model: [qsTr("Atom colour"), qsTr("Greyed atom colour"), qsTr("Single grey")]
                        currentIndex: Math.max(0, schemes.indexOf(Preferences.momentColours))
                        onActivated: index => Preferences.momentColours = schemes[index]
                        ToolTip.text: qsTr("How the structure view colours the magnetic moment arrows")
                    }
                    PaletteStrip {
                        objectName: "preferences.momentColourStrip"
                        width: dialog.columnWidth
                        colours: ApplicationInfo.momentColourSamples(Preferences.momentColours, EaStyle.Colors.isDarkPalette)
                    }
                }
            }
            GroupTitle {
                first: false
                icon: "chart-area"
                text: qsTr("Charts")
            }
            TabRow {
                Field {
                    label: qsTr("When a legend click hides a curve")
                    FieldBox {
                        readonly property list<string> choices: ["keep", "fit"]

                        objectName: "preferences.hiddenRange"
                        model: [qsTr("Keep the y range"), qsTr("Fit the range to visible curves")]
                        currentIndex: Math.max(0, choices.indexOf(Preferences.chartHiddenRange))
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 4)
                    }
                }
            }
            TabRow {
                // The figure palette of experiments and structures, the Pattern and Stacked views alike (ADR-0084).
                Field {
                    label: qsTr("Palette")
                    spacing: dialog.stripSpacing
                    FieldBox {
                        readonly property var schemes: ApplicationInfo.colourSchemes

                        objectName: "preferences.colours"
                        model: ApplicationInfo.colourSchemeTitles
                        currentIndex: Math.max(0, schemes.indexOf(ApplicationInfo.colourSchemeOrDefault(Preferences.colourScheme)))
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 1)
                        ToolTip.text: qsTr("The colours of experiments and structures in every chart, icon and report. From nine patterns in one view, they shade from the first experiment's colour to the second's")
                    }
                    PaletteStrip {
                        objectName: "preferences.colourOrder"
                        width: dialog.columnWidth
                        colours: ApplicationInfo.paletteColours(Preferences.colourScheme, EaStyle.Colors.isDarkPalette)
                    }
                }
                // The Map view's colour map, also chosen on the Map's toolbar.
                Field {
                    label: qsTr("Map colours")
                    spacing: dialog.stripSpacing
                    FieldBox {
                        id: mapBox

                        readonly property var choices: ApplicationInfo.scanColourMaps

                        objectName: "preferences.mapColours"
                        model: ApplicationInfo.preferenceColourTitles()
                        currentIndex: Math.max(0, choices.indexOf(Preferences.scanMapColours))
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 3)
                        ToolTip.text: qsTr("The Map view's colours, also chosen on its toolbar")
                    }
                    ColourMapBar {
                        objectName: "preferences.mapColourStrip"
                        map: mapBox.choices[mapBox.currentIndex] ?? "blue-red"
                        dark: EaStyle.Colors.isDarkPalette
                        barWidth: dialog.columnWidth
                        barHeight: Math.round(EaStyle.Sizes.fontPixelSize * 0.4)
                    }
                }
            }
        }

        // Interface: tooltips and fitting on the left, the sidebar and the Text tabs on the right.
        TabRow {
            TabColumn {
                GroupTitle {
                    icon: "comment-dots"
                    text: qsTr("Tooltips")
                }
                Field {
                    label: qsTr("Show tooltips for")
                    FieldBox {
                        readonly property var levels: ["All", "Important", "Off"]

                        objectName: "preferences.toolTipLevel"
                        model: [qsTr("All controls"), qsTr("Important controls"), qsTr("None")]
                        currentIndex: Math.max(0, levels.indexOf(Preferences.toolTipLevel))
                        onActivated: index => Preferences.toolTipLevel = levels[index]
                        ToolTip.text: qsTr("Important: controls whose label or icon does not say what they do, and disabled ones")
                    }
                }
                Field {
                    label: qsTr("Tooltip delay (ms)")
                    FieldSpinBox {
                        objectName: "preferences.toolTipDelay"
                        from: 0
                        to: 10000
                        stepSize: 100
                        editable: true
                        value: Preferences.toolTipDelay
                        onValueModified: Preferences.toolTipDelay = value
                        ToolTip.text: qsTr("How long the pointer rests on a control before its tooltip opens")
                    }
                }
                GroupTitle {
                    first: false
                    icon: "calculator"
                    text: qsTr("Fitting")
                }
                Field {
                    label: qsTr("When a fit ends")
                    FieldBox {
                        objectName: "preferences.showFitResults"
                        model: [qsTr("Open the results window"), qsTr("Do nothing")]
                        currentIndex: Preferences.showFitResults ? 0 : 1
                        onActivated: index => Preferences.showFitResults = index === 0
                        ToolTip.text: qsTr("The fit status in the status bar opens the results window too")
                    }
                }
            }
            TabColumn {
                GroupTitle {
                    icon: "columns"
                    text: qsTr("Sidebar")
                }
                Field {
                    label: qsTr("Sidebar side")
                    FieldBox {
                        objectName: "preferences.sideBarSide"
                        model: [qsTr("Left"), qsTr("Right")]
                        currentIndex: Preferences.sideBarOnLeft ? 0 : 1
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 6)
                    }
                }
                Field {
                    label: qsTr("Sidebar groups open at once")
                    FieldBox {
                        objectName: "preferences.autoCollapse"
                        model: [qsTr("One"), qsTr("Any number")]
                        currentIndex: Preferences.autoCollapse ? 0 : 1
                        onActivated: index => Preferences.autoCollapse = index === 0
                        ToolTip.text: qsTr("With One, opening a group in the sidebar closes the other open groups")
                    }
                }
                GroupTitle {
                    first: false
                    icon: "file-alt"
                    text: qsTr("Text tabs")
                }
                Field {
                    label: qsTr("Text tab shows")
                    FieldBox {
                        readonly property list<string> choices: ["editable", "everything"]

                        objectName: "preferences.textShow"
                        model: [qsTr("Editable categories"), qsTr("Everything")]
                        currentIndex: Math.max(0, choices.indexOf(Preferences.textShow))
                        // Through the Text tabs, which settle an unapplied edit first; until then the box shows the setting.
                        onActivated: index => ApplicationInfo.textTabShowChoice(index, () => {
                                currentIndex = Qt.binding(() => Math.max(0, choices.indexOf(Preferences.textShow)));
                            })
                        ToolTip.text: qsTr("Everything adds the measured data and results, read-only")
                    }
                }
            }
        }

        // Projects: the defaults a new project takes (a project keeps its own), then the online sources (ADR-0068).
        TabColumn {
            width: dialog.contentRowWidth

            GroupTitle {
                icon: "archive"
                text: qsTr("New projects")
            }
            TabRow {
                Field {
                    label: qsTr("Uncertainty digits")
                    FieldBox {
                        objectName: "preferences.newProjectSuRule"
                        model: [qsTr("IUCr recommendation"), qsTr("Always 2 digits")]
                        currentIndex: Preferences.newProjectSuRule === "iucr_99" ? 1 : 0
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 7)
                        ToolTip.text: qsTr("Only new projects use this; an open project keeps its own, on the Project page")
                    }
                }
                Field {
                    label: qsTr("Report chart libraries")
                    FieldBox {
                        objectName: "preferences.newReportLibraries"
                        model: [qsTr("Online"), qsTr("Embedded")]
                        currentIndex: Preferences.newReportLibraries === "embedded" ? 1 : 0
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 8)
                        ToolTip.text: qsTr("Embedded reports open offline. Only new projects use this; an open project keeps its own, on the Report page")
                    }
                }
            }
            GroupTitle {
                first: false
                icon: "globe"
                text: qsTr("Online sources")
            }
            DataTable {
                id: onlineTable
                objectName: "preferences.online.sources"
                width: parent.width
                maxRowCountShow: 3
                sourceModel: Session.onlineSources
                defaultInfoText: qsTr("No online sources")
                // Each source on three lines, as the Examples list draws an example: its name, what it holds and its
                // URL, so every text shows whole.
                tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * 5.5)
                columns: [numberColumnWidth, -1, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]
                // Without a header, as the Examples list: each row's three lines say what they are.
                header: EaComponents.ListViewHeader {
                    visible: false
                    implicitHeight: 0
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {}
                }
                delegate: TableRow {
                    id: onlineRow
                    required property string name
                    required property string url
                    required property var kinds
                    required property bool builtin
                    required property var model
                    required property bool overridden
                    EaComponents.ListViewLabel {
                        elide: Text.ElideRight
                        text: onlineRow.index + 1
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                    }
                    // A built-in source's name and URL are read, not edited: the cell's own text is hidden under a
                    // label, which ends with "…" when too long, the whole text its tooltip.
                    Item {
                        height: onlineRow.height

                        // A read-only source's lines whole, as the tooltip; an editable one shows its own.
                        HoverHandler {
                            id: onlineHover
                        }
                        EaElements.ToolTip {
                            requested: onlineHover.hovered && onlineRow.builtin
                            text: [onlineRow.name, onlineRow.url, onlineRow.overridden ? qsTr("Set for this run by --online-source or EDI_ONLINE_SOURCES") : ""].filter(line => line !== "").join("\n")
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            spacing: EaStyle.Sizes.fontPixelSize * 0.1

                            Item {
                                width: parent.width
                                height: dialog.onlineLineHeight
                                TextCell {
                                    id: nameCell

                                    objectName: "preferences.online.source.name." + onlineRow.model.id
                                    width: parent.width
                                    horizontalAlignment: Text.AlignLeft
                                    value: onlineRow.name
                                    enabled: !onlineRow.builtin
                                    color: onlineRow.builtin ? "transparent" : activeFocus || hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
                                    onCommitted: text => Session.onlineSources.setName(onlineRow.model.id, text)
                                    EaElements.Label {
                                        anchors.fill: parent
                                        leftPadding: parent.leftPadding
                                        rightPadding: parent.rightPadding
                                        visible: onlineRow.builtin
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        // Read, not disabled: the name in the text colour, as the Examples titles.
                                        color: EaStyle.Colors.themeForeground
                                        text: onlineRow.name
                                    }
                                }
                            }
                            // What it holds, as tags in the Examples list's style, one per kind with its icon.
                            Row {
                                objectName: "preferences.online.source.kinds." + onlineRow.model.id
                                height: dialog.onlineLineHeight
                                leftPadding: nameCell.leftPadding
                                spacing: AppSizes.fieldSpacing / 2

                                Repeater {
                                    model: ApplicationInfo.sourceKindTags(onlineRow.kinds)
                                    delegate: TagChip {
                                        required property var modelData
                                        label: modelData.label
                                        icon: modelData.icon
                                        ink: EaStyle.Colors.isDarkPalette ? modelData.dark : modelData.light
                                    }
                                }
                            }
                            Item {
                                width: parent.width
                                height: dialog.onlineLineHeight
                                TextCell {
                                    objectName: "preferences.online.source.url." + onlineRow.model.id
                                    width: parent.width
                                    horizontalAlignment: Text.AlignLeft
                                    value: onlineRow.url
                                    enabled: !onlineRow.builtin && !onlineRow.overridden
                                    color: !enabled ? "transparent" : activeFocus || hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForegroundMinor
                                    ToolTip.text: enabled ? onlineRow.url : ""
                                    onCommitted: text => Session.onlineSources.setUrl(onlineRow.model.id, text)
                                    EaElements.Label {
                                        anchors.fill: parent
                                        leftPadding: parent.leftPadding
                                        rightPadding: parent.rightPadding
                                        visible: !parent.enabled
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideMiddle
                                        color: EaStyle.Colors.themeForegroundMinor
                                        text: onlineRow.url
                                    }
                                }
                            }
                        }
                    }
                    EaComponents.ListViewButton {
                        objectName: "preferences.online.source.enabled." + onlineRow.model.id
                        // Square, as in a one-line row, centred in the taller row.
                        height: EaStyle.Sizes.tableRowHeight
                        fontIcon: onlineRow.model.enabled ? "toggle-on" : "toggle-off"
                        ToolTip.text: onlineRow.model.enabled ? qsTr("Leave this source out of the From web… popup") : qsTr("Offer this source in the From web… popup")
                        onClicked: Session.onlineSources.setEnabled(onlineRow.model.id, !onlineRow.model.enabled)
                    }
                    EaComponents.ListViewButton {
                        objectName: "preferences.online.source.remove." + onlineRow.model.id
                        height: EaStyle.Sizes.tableRowHeight
                        fontIcon: "minus-circle"
                        enabled: !onlineRow.builtin
                        ToolTip.text: onlineRow.builtin ? qsTr("A built-in source cannot be removed, only disabled") : qsTr("Remove this source")
                        onClicked: Session.onlineSources.remove(onlineRow.model.id)
                    }
                }
            }
            FieldButton {
                objectName: "preferences.online.sources.add"
                text: qsTr("Add online source")
                fontIcon: "plus-circle"
                ToolTip.text: qsTr("Add a collection to search: a URL holding an index.json and the files it names")
                onClicked: Session.onlineSources.add()
            }
        }

        // Performance: this computer's calculation and drawing, never saved in a project. Where the app runs
        // single-threaded (a browser without WebAssembly threads) both counts are one and disabled.
        TabRow {
            TabColumn {
                GroupTitle {
                    icon: "microchip"
                    text: qsTr("Calculation")
                }
                Field {
                    label: qsTr("Threads per calculation")
                    NotAvailable {
                        reason: ApplicationInfo.engineThreadsSelectable ? "" : qsTr("This browser runs the app on one thread")
                        FieldBox {
                            id: threadsBox

                            objectName: "preferences.engineThreads"
                            enabled: ApplicationInfo.engineThreadsSelectable
                            model: {
                                if (!ApplicationInfo.engineThreadsSelectable)
                                    return ["1"];
                                const counts = [qsTr("Auto")];
                                for (let count = 1; count <= ApplicationInfo.engineThreadsMaximum; ++count)
                                    counts.push(String(count));
                                return counts;
                            }
                            currentIndex: ApplicationInfo.engineThreadsSelectable ? Math.min(Preferences.engineThreads, ApplicationInfo.engineThreadsMaximum) : 0
                            // While several scan files are fitted at once, each of those fits runs on one thread.
                            displayText: Preferences.scanWorkersApplied > 1 ? `${currentText} <font color="${EaStyle.Colors.themeForegroundDisabled}">· ${qsTr("1 per scan fit")}</font>` : currentText
                            onActivated: index => {
                                if (ApplicationInfo.engineThreadsSelectable)
                                    Preferences.engineThreads = index;
                            }
                            ToolTip.text: Preferences.scanWorkersApplied > 1 ? qsTr("Threads one calculation or one fit runs on. While several scan files are fitted at once, each of those fits runs on one thread") : qsTr("Threads one calculation or one fit runs on; Auto leaves a core or two free")
                        }
                    }
                }
                Field {
                    label: qsTr("Parallel fits in a scan")
                    NotAvailable {
                        reason: ApplicationInfo.engineThreadsSelectable ? "" : qsTr("This browser runs the app on one thread")
                        FieldBox {
                            id: scanWorkersBox

                            property int maximum: ApplicationInfo.scanWorkersMaximum
                            signal chosen(int count)

                            // The count the engine runs with, set rather than bound: the list is rebuilt when the
                            // machine's maximum is read.
                            function show() {
                                currentIndex = Math.max(0, Math.min(Preferences.scanWorkersApplied, maximum) - 1);
                            }

                            // A plain list of every count up to the cores of this machine: a click opens it.
                            objectName: "preferences.scanWorkers"
                            enabled: ApplicationInfo.engineThreadsSelectable
                            model: {
                                const counts = [];
                                for (let count = 1; count <= Math.max(1, maximum); ++count)
                                    counts.push(String(count));
                                return counts;
                            }
                            Component.onCompleted: show()
                            onModelChanged: show()
                            onActivated: index => chosen(index + 1)
                            onChosen: count => {
                                Preferences.scanWorkers = count;
                                show();
                            }
                            Connections {
                                target: Preferences
                                function onScanWorkersAppliedChanged() {
                                    scanWorkersBox.show();
                                }
                            }
                            ToolTip.text: qsTr("How many data files of a sequential or independent scan are fitted at once, up to the %1 cores of this machine. Each file of a group starts from where the previous group ended; 1 fits them one after another, each from the previous result").arg(maximum)
                        }
                    }
                }
            }
            TabColumn {
                GroupTitle {
                    icon: "desktop"
                    text: qsTr("Graphics")
                }
                // How the Stacked view draws its lines: on the GPU, or painted, which is faster without one; Automatic
                // takes the detected graphics below (edi ADR-0041).
                Field {
                    label: qsTr("Scan view drawing")
                    FieldBox {
                        readonly property var values: ["auto", "gpu", "software"]

                        objectName: "preferences.scanRenderer"
                        model: [qsTr("Automatic"), qsTr("GPU"), qsTr("Software painter")]
                        currentIndex: Math.max(0, values.indexOf(Preferences.scanRenderer))
                        onActivated: index => ApplicationInfo.preferenceActivated(index, 10)
                        ToolTip.text: qsTr("Software drawing is faster on a computer without a GPU")
                    }
                }
                // What Qt draws with (edi ADR-0041), read in the first frame.
                Field {
                    label: qsTr("Detected graphics")
                    ReadOnlyField {
                        objectName: "preferences.graphics"
                        text: !RenderingInfo.detected ? qsTr("Not detected yet") : (RenderingInfo.renderer !== "" ? RenderingInfo.api + ", " + RenderingInfo.renderer : RenderingInfo.api) + " · " + (RenderingInfo.software ? qsTr("software rendering, no GPU") : qsTr("GPU"))
                    }
                }
            }
        }

        // Updates: availability always updates in the background; the notice is the optional prompt.
        TabRow {
            TabColumn {
                Field {
                    label: qsTr("New version notice")
                    FieldBox {
                        objectName: "preferences.checkUpdateOnStart"
                        enabled: DesktopUpdates.managed
                        model: [qsTr("Show"), qsTr("Don't show")]
                        currentIndex: Preferences.updateNotifications ? 0 : 1
                        onActivated: index => Preferences.updateNotifications = index === 0
                        ToolTip.text: DesktopUpdates.managed ? qsTr("The app checks at startup and every hour") : dialog.updatesOff
                    }
                }
                NotAvailable {
                    reason: DesktopUpdates.managed ? "" : dialog.updatesOff
                    FieldButton {
                        objectName: "preferences.checkUpdateNow"
                        enabled: DesktopUpdates.managed && !DesktopUpdates.checking
                        highlighted: true
                        fontIcon: "sync-alt"
                        text: DesktopUpdates.checking ? qsTr("Checking…") : qsTr("Check now")
                        onClicked: DesktopUpdates.checkNow(true)
                    }
                }
            }
            TabColumn {
                Field {
                    label: qsTr("Status")
                    ReadOnlyField {
                        objectName: "preferences.updateStatus"
                        text: DesktopUpdates.status
                    }
                }
                FieldButton {
                    objectName: "preferences.openMaintenanceTool"
                    visible: DesktopUpdates.managed
                    fontIcon: "cogs"
                    text: qsTr("Open Maintenance Tool")
                    onClicked: dialog.maintenanceRequested()
                }
            }
        }

        // AI assistance: the skill sources, then support and the cached history.
        ScrollView {
            id: aiPage
            implicitHeight: Math.min(aiContent.implicitHeight, Math.max(0, dialog.parent.height - bar.implicitHeight - AppSizes.unit * 8))
            readonly property var original: ApplicationInfo.assistantBuilt ? Session.assistant : null
            property string copyError: ""
            onOriginalChanged: if (ApplicationInfo.assistantBuilt)
                ApplicationInfo.preferenceAssistantChanged()
            function copyDiagnostics(button, report) {
                ApplicationInfo.preferenceCopyDiagnostics(button, report);
            }
            clip: true
            TabColumn {
                id: aiContent
                width: dialog.contentRowWidth

                GroupTitle {
                    icon: "book"
                    text: qsTr("Skill sources")
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
                            elide: Text.ElideRight
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
                            elide: Text.ElideRight
                            text: sourceRow.index + 1
                            horizontalAlignment: Text.AlignHCenter
                            marksCurrentRow: true
                        }
                        EaComponents.ListViewLabel {
                            objectName: "preferences.ai.source.label." + sourceRow.sourceId
                            text: sourceRow.builtin ? qsTr("EasyDiffraction") : sourceRow.label.startsWith("https://github.com/") ? sourceRow.label : sourceRow.path
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
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
                TabRow {
                    FieldButton {
                        objectName: "preferences.ai.sources.add"
                        text: qsTr("Add skill source")
                        fontIcon: "plus-circle"
                        enabled: ApplicationInfo.assistantAvailable && !(aiPage.original ? aiPage.original.canCancel : false) && !(aiPage.original ? aiPage.original.skillSourceImporting : false)
                        onClicked: ApplicationInfo.preferenceBeginSourceSelection(false)
                    }
                    FieldButton {
                        objectName: "preferences.ai.sources.web"
                        text: (aiPage.original ? aiPage.original.skillSourceImporting : false) ? qsTr("Cancel web import") : qsTr("Add skills from web")
                        fontIcon: (aiPage.original ? aiPage.original.skillSourceImporting : false) ? "times-circle" : "globe"
                        enabled: ApplicationInfo.assistantAvailable && !(aiPage.original ? aiPage.original.canCancel : false)
                        onClicked: ApplicationInfo.preferenceBeginSourceSelection(true)
                    }
                }
                EaElements.Label {
                    width: parent.width
                    text: (aiPage.original ? aiPage.original.skillSourceError : "")
                    visible: text.length > 0
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: EaStyle.Colors.red
                }
                GroupTitle {
                    first: false
                    icon: "life-ring"
                    text: qsTr("Support and history")
                }
                TabRow {
                    TabColumn {
                        Field {
                            label: qsTr("Technical details in copied steps")
                            FieldBox {
                                objectName: "preferences.ai.copyTechnicalDetails"
                                model: [qsTr("Leave out"), qsTr("Include")]
                                currentIndex: Preferences.assistantCopyTechnicalDetails ? 1 : 0
                                onActivated: index => Preferences.assistantCopyTechnicalDetails = index === 1
                            }
                        }
                        Field {
                            label: qsTr("Connection details")
                            EaElements.SideBarButton {
                                id: copyConnection
                                objectName: "preferences.ai.copyConnection"
                                width: dialog.columnWidth
                                height: dialog.rowHeight
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
                    }
                    TabColumn {
                        Field {
                            label: qsTr("Work report")
                            EaElements.SideBarButton {
                                id: copyWorkReport
                                objectName: "preferences.ai.workReport"
                                width: dialog.columnWidth
                                height: dialog.rowHeight
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
                        }
                        Field {
                            label: qsTr("Cached chat history")
                            FieldButton {
                                objectName: "preferences.ai.clearCachedHistory"
                                text: (aiPage.original ? aiPage.original.cachedHistoryClearing : false) ? qsTr("Clearing cached chat history…") : qsTr("Clear cached chat history")
                                fontIcon: "eraser"
                                enabled: !(aiPage.original ? aiPage.original.canCancel : false) && !(aiPage.original ? aiPage.original.cachedHistoryClearing : false)
                                ToolTip.text: qsTr("Clears only the saved chat display. Projects and sign-in are kept")
                                onClicked: if (aiPage.original)
                                    aiPage.original.clearCachedHistory()
                            }
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
                    width: parent.width
                    text: (aiPage.original ? aiPage.original.cachedHistoryError : "")
                    visible: text.length > 0
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: EaStyle.Colors.red
                }
            }
        }

        // Advanced: troubleshooting, and the settings file (ADR-0031 §5). The run log goes to the terminal and to a
        // file of each run (edi ADR-0062). The feedback address stays in the settings file only (edi ADR-0063).
        TabRow {
            TabColumn {
                GroupTitle {
                    icon: "bug"
                    text: qsTr("Troubleshooting")
                }
                Field {
                    label: qsTr("Message level")
                    FieldBox {
                        objectName: "preferences.loggingLevel"
                        model: ["Debug", "Info", "Warning", "Error"]
                        ToolTip.text: qsTr("The messages to show and log: those at this level and above. Errors always show")
                        currentIndex: model.indexOf(Preferences.loggingLevel)
                        onActivated: Preferences.loggingLevel = currentValue
                    }
                }
                // What the app runs on and with, to read and to copy.
                Field {
                    label: qsTr("Diagnostics")
                    FieldButton {
                        objectName: "preferences.diagnostics"
                        fontIcon: "info-circle"
                        text: qsTr("Show diagnostics")
                        onClicked: diagnostics.open()
                    }
                }
            }
            TabColumn {
                GroupTitle {
                    icon: "file-alt"
                    text: qsTr("Settings file")
                }
                // A long path is cut in its middle, and the whole of it is the tooltip.
                Field {
                    label: qsTr("Stored in")
                    ReadOnlyField {
                        id: settingsPath

                        objectName: "preferences.settingsPath"
                        // A path keeps its start and its file name: cut in the middle.
                        elide: Text.ElideMiddle
                        text: WebFiles.available ? qsTr("Stored in this browser") : ApplicationInfo.shownPath(EaGlobals.Vars.settingsFile)
                        toolTipText: WebFiles.available ? text : ApplicationInfo.localPath(EaGlobals.Vars.settingsFile)
                    }
                }
                Field {
                    label: " "
                    TabRow {
                        spacing: dialog.rowSpacing
                        EaElements.SideBarButton {
                            objectName: "preferences.openSettingsFolder"
                            visible: !WebFiles.available
                            width: (dialog.columnWidth - parent.spacing) / 2
                            height: dialog.rowHeight
                            fontIcon: "folder-open"
                            text: qsTr("Open folder")
                            onClicked: Qt.openUrlExternally(ApplicationInfo.folderOf(EaGlobals.Vars.settingsFile))
                        }
                        EaElements.SideBarButton {
                            objectName: "preferences.resetSettings"
                            width: WebFiles.available ? dialog.columnWidth : (dialog.columnWidth - parent.spacing) / 2
                            height: dialog.rowHeight
                            fontIcon: "undo"
                            text: qsTr("Reset to defaults")
                            onClicked: resetConfirm.open()
                        }
                    }
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
            implicitWidth: dialog.columnWidth
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

    DiagnosticsDialog {
        id: diagnostics
        parent: Overlay.overlay
    }
}
