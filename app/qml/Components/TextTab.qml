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
        tab.shownFile = tab.source ? tab.source.file : "";
        tab.shownBlockIndex = tab.blockIndex;
        tab.refusal = "";
        const kept = tab.keptEdits[tab.shownFile];
        delete tab.keptEdits[tab.shownFile];
        tab.showing = true;
        textEdit.text = kept !== undefined ? kept : tab.shownText;
        tab.showing = false;
        tab.edited = kept !== undefined;
    }
    function applyEdit() {
        if (!tab.dirty || !tab.editable)
            return;
        const refusal = Session.project.applyText(tab.source.file, tab.source.withOutputs(textEdit.text));
        tab.refusal = refusal;
        if (refusal === "")
            tab.showBlock();
    }
    // Leaving the edit with it unapplied asks "Discard changes?" (the owner, 2026-10-25): `discard` runs once the
    // user discards it, `keep` if the user keeps it.
    function askDiscard(discard, keep) {
        discardDialog.discard = discard;
        discardDialog.keep = keep;
        discardDialog.open();
    }
    onShownTextChanged: {
        if (!tab.dirty)
            tab.showBlock();
    }
    // Another block: its own text shows, and the edit of the one left is kept while the user is asked; kept, that
    // block is shown again with it.
    onSourceChanged: {
        if (tab.edited && tab.shownFile !== "" && (tab.source === null || tab.source.file !== tab.shownFile)) {
            const file = tab.shownFile;
            const index = tab.shownBlockIndex;
            tab.keptEdits[file] = textEdit.text;
            tab.askDiscard(() => delete tab.keptEdits[file], () => tab.blockRequested(index));
        }
        tab.showBlock();
    }
    onBlockIndexChanged: {
        if (!tab.edited)
            tab.shownBlockIndex = tab.blockIndex;
    }
    // Another page or sidebar tab: kept, the page and this tab are shown again.
    onShownChanged: {
        if (!tab.shown && tab.dirty)
            tab.askDiscard(() => tab.showBlock(), () => tab.stayRequested());
    }
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

        // Show, then ✓, at the tab's top right (the owner, 2026-10-25).
        Row {
            id: controls

            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: AppSizes.textViewPadding
            spacing: AppSizes.toolbarSpacing
            z: 1

            ToolbarComboBox {
                readonly property list<string> choices: ["editable", "everything"]

                objectName: "text.show"
                toolTip: qsTr("What the Text tab shows: the categories you can edit, or also the measured data and results, read-only")
                model: [qsTr("Editable"), qsTr("Everything")]
                shownIndex: Math.max(0, choices.indexOf(Preferences.textShow))
                // Another Show choice with the edit unapplied changes only once the edit is discarded.
                onActivated: index => {
                    const choice = choices[index];
                    if (!tab.dirty) {
                        Preferences.textShow = choice;
                        return;
                    }
                    tab.askDiscard(() => {
                        tab.edited = false;
                        Preferences.textShow = choice;
                        tab.showBlock();
                    }, null);
                }
            }
            // A disabled button takes no hover, so the reason it is disabled comes from here.
            Item {
                width: applyButton.width
                height: applyButton.height

                ChartToolButton {
                    id: applyButton

                    objectName: "text.apply"
                    enabled: tab.editable && tab.dirty
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
        // Why the last apply was refused; the edited text stays as it was.
        EaElements.Label {
            id: refusalLabel

            objectName: "text.refusal"
            anchors.top: controls.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: AppSizes.textViewPadding
            visible: tab.refusal !== "" && tab.dirty
            wrapMode: Text.Wrap
            color: EaStyle.Colors.red
            text: tab.refusal
        }

        Flickable {
            anchors.fill: parent
            anchors.topMargin: (refusalLabel.visible ? refusalLabel.y + refusalLabel.height : controls.y + controls.height) + AppSizes.textViewPadding
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
                onTextChanged: {
                    if (!tab.showing && !readOnly)
                        tab.edited = true;
                }
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

        // What leaving runs once the edit is discarded, or kept.
        property var discard: null
        property var keep: null

        objectName: "text.discard"
        title: qsTr("Discard changes?")
        standardButtons: Dialog.Discard | Dialog.Cancel
        contentWidth: discardText.implicitWidth
        contentHeight: discardText.implicitHeight
        onDiscarded: {
            close();
            const discard = discardDialog.discard;
            discardDialog.discard = discardDialog.keep = null;
            if (discard)
                discard();
        }
        onRejected: {
            const keep = discardDialog.keep;
            discardDialog.discard = discardDialog.keep = null;
            if (keep)
                keep();
        }

        EaElements.Label {
            id: discardText
            text: qsTr("The edited text has not been applied.")
        }
    }
}
