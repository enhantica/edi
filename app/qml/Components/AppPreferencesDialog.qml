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
    onClosed: {
        Preferences.dialogShown = false;
        const intent=sourcesFolder.selection;
        if(intent) {
            sourcesFolder.selection=null;
            if(Qt.isQtObject(intent.owner))intent.owner.cancelSkillSourceSelection(intent.id);
            if(Qt.isQtObject(sourcesFolder) && sourcesFolder.selection===null)sourcesFolder.reject();
        }
    }
    onOpened: Session.assistant.refreshSkillSources()

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
            objectName: "preferences.tab.aiAssistance"
            fontIcon: "robot"
            text: qsTr("AI assistance")
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

            RowLabel {
                text: qsTr("Colour scheme") + ":"
            }
            RowBox {
                // The schemes' tokens (data/palettes), in the order the box lists them: edi's own, then published
                // palettes for data, then app themes.
                readonly property var schemes: ["coast", "garden", "peaceful", "fogForest", "sage", "okabeIto", "paulTolBright", "paulTolMuted", "tableau", "observable", "carbon", "dark2", "petroff", "vivid", "nord", "solarized", "catppuccin", "apple"]

                objectName: "preferences.colourScheme"
                model: [qsTr("Coast"), qsTr("Garden"), qsTr("Peaceful"), qsTr("Fog forest"), qsTr("Sage"), qsTr("Okabe-Ito"), qsTr("Paul Tol bright"), qsTr("Paul Tol muted"), qsTr("Tableau 10"), qsTr("Observable 10"), qsTr("IBM Carbon"), qsTr("ColorBrewer Dark2"), qsTr("Petroff"), qsTr("Vivid"), qsTr("Nord"), qsTr("Solarized"), qsTr("Catppuccin"), qsTr("Apple")]
                currentIndex: Math.max(0, schemes.indexOf(Preferences.colourScheme))
                onActivated: index => Preferences.colourScheme = schemes[index]
                ToolTip.text: qsTr("The experiments' and structures' colours in every chart and icon")
            }

            RowLabel {
                text: qsTr("Workflow sidebar side") + ":"
            }
            RowBox {
                objectName: "preferences.sideBarSide"
                model: [qsTr("Left"), qsTr("Right")]
                currentIndex: Preferences.sideBarOnLeft ? 0 : 1
                onActivated: index => Preferences.sideBarSide = index === 0 ? "Left" : "Right"
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

        ScrollView {
            id: aiPage
            implicitHeight: Math.min(aiContent.implicitHeight, Math.max(0, dialog.parent.height-bar.implicitHeight-AppSizes.unit*8))
            readonly property var original: Session.assistant
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
                    columnWidths: [numberColumnWidth,-1,AppSizes.iconColumnWidth,AppSizes.iconColumnWidth]
                    header: EaComponents.ListViewHeader {
                        EaComponents.TableViewLabel {}
                        EaComponents.TableViewLabel { text: qsTr("Source"); horizontalAlignment: Text.AlignLeft }
                        EaComponents.TableViewLabel {}
                        EaComponents.TableViewLabel {}
                    }
                    delegate: EaComponents.ListViewDelegate {
                        id: sourceRow
                        required property int index
                        readonly property string sourceId: model.id || ""
                        required property string label
                        required property string path
                        required property bool builtin
                        required property string status
                        required property var model
                        readonly property var original: aiPage.original
                        property int presentation: 0
                        onSourceIdChanged: ++presentation
                        onOriginalChanged: ++presentation
                        EaComponents.TableViewLabel {
                            text: sourceRow.index+1
                            horizontalAlignment: Text.AlignHCenter
                        }
                        EaComponents.TableViewLabel {
                            objectName: "preferences.ai.source.label."+sourceRow.sourceId
                            text: sourceRow.builtin ? qsTr("EasyDiffraction") : sourceRow.path
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            ToolTip.text: text+(sourceRow.status.length ? "\n"+sourceRow.status : "")
                        }
                        EaComponents.TableViewButton {
                            id: sourceEnabled
                            objectName: "preferences.ai.source.enabled."+sourceRow.sourceId
                            fontIcon: sourceRow.model.enabled ? "toggle-on" : "toggle-off"
                            enabled: ApplicationInfo.assistantAvailable && sourceRow.original && !sourceRow.original.canCancel
                            ToolTip.text: sourceRow.model.enabled ? qsTr("Disable this skill source") : qsTr("Enable this skill source")
                            Accessible.name: ToolTip.text
                            Accessible.checkable: true
                            Accessible.checked: sourceRow.model.enabled
                            property var gesture: null
                            onPressed: gesture={owner:sourceRow.original,id:sourceRow.sourceId,revision:sourceRow.original.skillSourceRevision,presentation:sourceRow.presentation,enabled:!sourceRow.model.enabled}
                            onCanceled: gesture=null
                            onClicked: {
                                const original=gesture;gesture=null;
                                if(original && Qt.isQtObject(original.owner) && original.owner===aiPage.original && original.id===sourceRow.sourceId && original.presentation===sourceRow.presentation && original.enabled===!sourceRow.model.enabled)
                                    original.owner.setSkillSourceEnabled(original.id,original.enabled,original.revision);
                            }
                            Connections {
                                target: sourceRow.original
                                function onSkillSourcesChanged() { sourceEnabled.gesture=null; }
                            }
                        }
                        EaComponents.TableViewButton {
                            objectName: "preferences.ai.source.remove."+sourceRow.sourceId
                            fontIcon: "minus-circle"
                            enabled: ApplicationInfo.assistantAvailable && !sourceRow.builtin && sourceRow.original && !sourceRow.original.canCancel
                            ToolTip.text: sourceRow.builtin ? qsTr("The built-in source cannot be removed") : qsTr("Remove this skill source")
                            Accessible.name: ToolTip.text
                            id: sourceRemove
                            property var gesture: null
                            onPressed: gesture={owner:sourceRow.original,id:sourceRow.sourceId,revision:sourceRow.original.skillSourceRevision,presentation:sourceRow.presentation}
                            onCanceled: gesture=null
                            onClicked: {
                                const original=gesture;gesture=null;
                                if(original && Qt.isQtObject(original.owner) && original.owner===aiPage.original && original.id===sourceRow.sourceId && original.presentation===sourceRow.presentation)
                                    original.owner.removeSkillSource(original.id,original.revision);
                            }
                            Connections {
                                target: sourceRow.original
                                function onSkillSourcesChanged() { sourceRemove.gesture=null; }
                            }
                        }
                    }
                }
                EaElements.SideBarButton {
                    objectName: "preferences.ai.sources.add"
                    text: qsTr("Add skill source")
                    fontIcon: "plus-circle"
                    enabled: ApplicationInfo.assistantAvailable && !Session.assistant.canCancel
                    onClicked: {
                        const original=Session.assistant;
                        const token=original.beginSkillSourceSelection();
                        if (!Qt.isQtObject(original) || original!==Session.assistant || !token.length || sourcesFolder.intent.length) {
                            if (Qt.isQtObject(original)) original.cancelSkillSourceSelection(token);
                            return;
                        }
                        const intent={owner:original,id:token};
                        sourcesFolder.selection=intent;
                        if (Qt.isQtObject(sourcesFolder) && sourcesFolder.selection===intent) sourcesFolder.open();
                        else if (Qt.isQtObject(original)) original.cancelSkillSourceSelection(token);
                    }
                }
                EaElements.Label {
                    width: parent.width
                    text: Session.assistant.skillSourceError
                    visible: text.length>0
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: EaStyle.Colors.red
                }
                EaElements.Label {
                    width: parent.width
                    text: qsTr("Enabled sources guide the assistant. They do not grant project writes, network access or new tools.")
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
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

    FolderDialog {
        id: sourcesFolder
        objectName: "preferences.ai.sources.folder"
        property var selection: null
        readonly property string intent: selection ? selection.id : ""
        readonly property var original: selection ? selection.owner : null
        title: qsTr("Choose a skill folder or collection")
        onAccepted: {
            const target=original; const token=intent; const folder=selectedFolder;
            selection=null;
            if (Qt.isQtObject(target)) target.addSkillSource(token,folder);
        }
        onRejected: { const target=original; const token=intent; selection=null; if (Qt.isQtObject(target)) target.cancelSkillSourceSelection(token); }
        Component.onDestruction: { const target=original; const token=intent; selection=null; if (Qt.isQtObject(target)) target.cancelSkillSourceSelection(token); }
        Connections {
            target: sourcesFolder.original
            function onSkillSourceSelectionRetired(token) {
                if (sourcesFolder.intent!==token) return;
                sourcesFolder.selection=null;
                if (Qt.isQtObject(sourcesFolder) && sourcesFolder.selection===null) sourcesFolder.reject();
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
