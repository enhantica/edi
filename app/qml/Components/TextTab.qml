// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A page's Text tab (easydiffractionbeta Pages/*/SideBarText.qml): the block's text view, filling the tab
// (SideBarText/TextView.qml, edi ADR-0017 §7). The text is the `.edi` text a save writes for the block, in PT Mono,
// or the writer's refusal when it cannot be written. Under Show's Editable it can be edited, and ✓ applies the edit
// as opening a file holding it would; Everything is read-only. Show is one setting for every Text tab. The tab has no block selector of its
// own (edi ADR-0017 §7): on Structure and Experiment the sidebar's selector serves every tab, and Project,
// Analysis and Report have one block each — the app opens one project at a time, so there is nothing to choose.
EaComponents.SideBarColumn {
    id: tab

    required property BlockText source
    // False on a page without Continue (Report), or while the Continue area is hidden: nothing is drawn over the
    // text view's bottom.
    property bool underContinue: AppState.continueAreaShown

    readonly property bool everything: Preferences.textShow === "everything"
    // Everything shows the whole file; Editable only the categories the user sets.
    readonly property string shownText: !tab.source ? "" : tab.source.error !== "" ? tab.source.error : tab.everything ? tab.source.text : tab.source.inputText
    // A block whose file an apply can replace, shown under Editable.
    readonly property bool editable: !everything && tab.source !== null && tab.source.error === "" && tab.source.file !== "" && Session.project !== null
    // The text differs from the block's: typed since it was last shown, and not typed back.
    readonly property bool dirty: edited && textEdit.text !== shownText
    property bool edited: false
    // Why the last apply was refused, shown until the text is applied or put back.
    property string refusal: ""
    // The file whose text the view shows, and the unapplied edits of the blocks left with one kept, by file: a block
    // left with its edit kept shows it again when it is shown again.
    property string shownFile: ""
    property var keptEdits: ({})
    // The source shown, and the refusals of kept edits an apply on leaving refused, by file.
    property BlockText shownSource: null
    property var keptRefusals: ({})
    // True while the tab itself puts a block's text in the view, which is no edit.
    property bool showing: false
    // Whether the page and this tab are shown, and the page's block (WorkflowPage sets both): leaving the edit asks
    // first, and a kept edit asks the page to come back to it.
    property bool shown: true
    property int blockIndex: -1
    property int shownBlockIndex: -1
    signal stayRequested
    signal blockRequested(int index)

    function showBlock() {
        ApplicationInfo.textTabShowBlock();
    }
    // Applies `text` as the block `source`'s file: the refusal, with nothing changed, or empty.
    function applyTo(source: BlockText, text: string): string {
        return ApplicationInfo.textTabApplyTo(source, text);
    }
    function applyEdit() {
        ApplicationInfo.textTabApplyEdit();
    }
    // Leaving the edit with it unapplied asks (the owner, 2026-10-27): Apply applies it as ✓ does and leaves, and a
    // refused apply stays on the text with its reason; Don't apply drops it and leaves; Cancel stays. `apply` gives
    // the refusal, `leave` leaves, `drop` drops the edit and leaves, `stay` comes back to the edit.
    function askLeave(apply, leave, drop, stay) {
        ApplicationInfo.textTabAskLeave(apply, leave, drop, stay);
    }
    onShownTextChanged: ApplicationInfo.textTabChanged(0)
    // Another block: its own text shows, and the edit of the one left is kept while the user is asked; kept, that
    // block is shown again with it.
    onSourceChanged: ApplicationInfo.textTabSourceChanged()
    onBlockIndexChanged: ApplicationInfo.textTabChanged(1)
    // Another page or sidebar tab: kept, the page and this tab are shown again.
    onShownChanged: ApplicationInfo.textTabChanged(2)
    Component.onCompleted: tab.showBlock()

    // The text view fills the tab edge to edge (the owner, 2026-09-29; edi ADR-0017 §7): the sidebar's full
    // width, from the top of the tab's view — under the tab bar, or under the shared block selector — down to
    // the sidebar's bottom, with no border of its own. Continue, a pill with its own background, floats over
    // it, and the text scrolls clear of it.
    Rectangle {
        id: container

        width: tab.width
        height: Math.max(AppSizes.textViewMinimumHeight, tab.height)
        color: EaStyle.Colors.textViewBackground
        Behavior on color {
            EaAnimations.ThemeChange {}
        }

        // Show, then ✓, over the text's top right corner (the owner, 2026-10-25 and 2026-10-27).
        Row {
            id: controls

            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: AppSizes.textViewPadding
            spacing: AppSizes.toolbarSpacing
            z: 1

            ToolbarComboBox {
                id: showBox

                readonly property list<string> choices: ["editable", "everything"]

                objectName: "text.show"
                toolTip: qsTr("What the Text tab shows: the categories you can edit, or also the measured data and results, read-only")
                model: [qsTr("Editable"), qsTr("Everything")]
                shownIndex: Math.max(0, choices.indexOf(Preferences.textShow))
                // Another Show choice with the edit unapplied changes only once the edit is discarded.
                onActivated: index => ApplicationInfo.textTabShowChoice(index, () => {
                        showBox.currentIndex = Qt.binding(() => showBox.shownIndex);
                    })
            }
            // A disabled button takes no hover, so the reason it is disabled comes from here.
            Item {
                width: applyButton.width
                height: applyButton.height

                ChartToolButton {
                    id: applyButton

                    objectName: "text.apply"
                    enabled: tab.editable && tab.dirty
                    alert: true
                    fontIcon: "check"
                    toolTip: qsTr("Apply the edited text to the project")
                    onClicked: tab.applyEdit()
                }
                HoverHandler {
                    id: applyHover
                }
                EaElements.ToolTip {
                    text: tab.everything ? qsTr("Switch Show to Editable to edit the text") : qsTr("Edit the text to apply it")
                    visible: !applyButton.enabled && applyHover.hovered && EaGlobals.Vars.showToolTips
                }
            }
        }
        // Why the last apply was refused, over the text under the controls; the edited text stays as it was.
        Rectangle {
            anchors.top: controls.bottom
            anchors.right: parent.right
            anchors.topMargin: AppSizes.textViewPadding / 2
            anchors.rightMargin: AppSizes.textViewPadding
            width: Math.min(parent.width - 2 * AppSizes.textViewPadding, refusalLabel.implicitWidth + 2 * AppSizes.textViewPadding)
            height: refusalLabel.height + AppSizes.textViewPadding
            visible: tab.refusal !== "" && tab.dirty
            color: EaStyle.Colors.contentBackground
            border.color: EaStyle.Colors.red
            border.width: EaStyle.Sizes.borderThickness
            z: 1

            EaElements.Label {
                id: refusalLabel

                objectName: "text.refusal"
                anchors.centerIn: parent
                width: parent.width - 2 * AppSizes.textViewPadding
                wrapMode: Text.Wrap
                color: EaStyle.Colors.red
                text: tab.refusal
            }
        }

        Flickable {
            anchors.fill: parent
            anchors.topMargin: AppSizes.textViewPadding
            anchors.bottomMargin: AppSizes.textViewPadding
            anchors.leftMargin: AppSizes.textViewPadding
            contentWidth: textEdit.contentWidth
            contentHeight: textEdit.contentHeight
            bottomMargin: tab.underContinue ? AppSizes.textViewContinueClearance : 0
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            ScrollBar.horizontal: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }

            TextEdit {
                id: textEdit
                objectName: "text.view"
                readOnly: !tab.editable
                selectByMouse: true
                font.family: tab.source && tab.source.error !== "" ? EaStyle.Fonts.fontFamily : EaStyle.Fonts.monoFontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                color: tab.source && tab.source.error !== "" ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.themeForeground
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                onTextChanged: ApplicationInfo.textTabChanged(3)
            }
            // The `.edi` text in the theme's colours; a writer's refusal stays plain.
            EdiTextHighlighter {
                objectName: "text.highlighter"
                document: tab.source && tab.source.error === "" ? textEdit.textDocument : null
                datablockColor: AppColors.textDatablock
                itemColor: AppColors.textItem
                loopColumnColor: AppColors.textLoopColumn
                loopColor: AppColors.textLoop
            }
        }
    }

    AppDialog {
        id: discardDialog

        // What each answer runs (askLeave).
        property var actions: ({})

        function answer(name: string, argument): void {
            ApplicationInfo.textTabAnswer(name, argument);
        }

        objectName: "text.discard"
        title: qsTr("Discard changes?")
        standardButtons: Dialog.Apply | Dialog.Discard | Dialog.Cancel
        contentWidth: discardText.implicitWidth
        contentHeight: discardText.implicitHeight
        Component.onCompleted: ApplicationInfo.textDiscardCompleted()
        onApplied: ApplicationInfo.textDiscardApplied()
        onDiscarded: ApplicationInfo.textDiscardDiscarded()
        onRejected: discardDialog.answer("stay", "")

        EaElements.Label {
            id: discardText
            text: qsTr("The edited text has not been applied.")
        }
    }
}
