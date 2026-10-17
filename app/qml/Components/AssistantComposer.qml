// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import edi.app

Rectangle {
    id: composer
    required property AssistantViewModel assistant
    required property Item toggleControl
    property Item popupBoundary: composer.parent
    property Item previousFocusItem: toggleControl
    readonly property Item firstFocusItem: editor
    readonly property alias actionsControl: showActionsControl
    readonly property real actionSize: EaStyle.Sizes.toolButtonHeight * 0.75
    function closeChoices() { if (Qt.isQtObject(choicePopup)) choicePopup.close(); }
    readonly property bool choicesEnabled: assistant.connected && !assistant.canCancel
    readonly property color lightActionBackground: EaStyle.Colors.themeBackgroundHovered2
    readonly property var effortChoices: [""].concat(assistant.availableEfforts).map(token => ({token: token, label: effortLabel(token)}))
    readonly property int selectedModelRow: {
        for (let i=0;i<assistant.models.count;++i)
            if (assistant.models.text(i,"id")===assistant.selectedModel) return i;
        return -1;
    }
    readonly property string modelLabel: selectedModelRow>=0 ? assistant.models.text(selectedModelRow,"displayName") : qsTr("Model")
    readonly property string selectedEffortLabel: effortChoices.some(row=>row.token===assistant.selectedEffort) ? effortLabel(assistant.selectedEffort) : qsTr("Effort")
    function effortLabel(value) {
        switch (value) {
        case "": return qsTr("Auto");
        case "none": return qsTr("None");
        case "low": return qsTr("Low");
        case "medium": return qsTr("Medium");
        case "high": return qsTr("High");
        case "xhigh": return qsTr("Extra high");
        case "max": return qsTr("Maximum");
        default: return value;
        }
    }
    function openChoices() {
        if(!choicesEnabled || !Qt.isQtObject(choicePopup) || choicePopup.visible)return;
        const original={owner:assistant};
        choicePopup.intent=original;
        if(Qt.isQtObject(choicePopup) && choicePopup.intent===original && Qt.isQtObject(original.owner) && original.owner===composer.assistant && composer.choicesEnabled)choicePopup.open();
    }
    onAssistantChanged: closeChoices()
    onChoicesEnabledChanged: { if (!choicesEnabled) closeChoices(); }
    Connections {
        target: composer.assistant
        function onConversationRetired() { composer.closeChoices(); }
        function onConnectionLabelChanged() { composer.closeChoices(); }
    }
    FontMetrics { id: choiceMetrics; font.family: EaStyle.Fonts.fontFamily; font.pixelSize: EaStyle.Sizes.fontPixelSize }
    ButtonGroup { id: modelSelection; exclusive: true }
    ButtonGroup { id: effortSelection; exclusive: true }
    AppDialog {
        id: choicePopup
        objectName: "assistant.modelEffort.popup"
        title: qsTr("Model and reasoning effort")
        standardButtons: Dialog.NoButton
        property var intent: null
        readonly property real viewportHeight: Math.max(0,parent.height-AppSizes.unit*2)
        readonly property real radioColumnWidth: AppSizes.iconColumnWidth
        readonly property real desiredLabelWidth: {
            let measured=Math.max(choiceMetrics.advanceWidth(qsTr("Model")),choiceMetrics.advanceWidth(qsTr("Reasoning effort")));
            for(let i=0;i<composer.assistant.models.count;++i)measured=Math.max(measured,choiceMetrics.advanceWidth(composer.assistant.models.text(i,"displayName")));
            for(const row of composer.effortChoices)measured=Math.max(measured,choiceMetrics.advanceWidth(row.label));
            return Math.ceil(measured)+AppSizes.fieldSpacing*2;
        }
        readonly property real tableWidth: radioColumnWidth+desiredLabelWidth+EaStyle.Sizes.tableColumnSpacing+modelTable.rowPadding*2+EaStyle.Sizes.borderThickness*2
        bottomPadding: leftPadding
        width: Math.min(choiceContent.implicitWidth+leftPadding+rightPadding,Math.max(0,parent.width-AppSizes.unit*2))
        height: Math.min(implicitHeight,viewportHeight)
        contentWidth: Math.max(0,width-leftPadding-rightPadding)
        contentHeight: Math.min(choiceContent.implicitHeight,Math.max(0,viewportHeight-topPadding-bottomPadding
            -(implicitHeaderHeight > 0 ? implicitHeaderHeight+spacing : 0)-(implicitFooterHeight > 0 ? implicitFooterHeight+spacing : 0)))
        focus: true
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        function current(original) {
            return original && intent===original && visible && Qt.isQtObject(composer) && Qt.isQtObject(original.owner) && original.owner===composer.assistant && composer.choicesEnabled;
        }
        function focusRow(table,index,original) {
            if(!current(original) || index<0 || index>=table.count)return;
            table.positionViewAtIndex(index,ListView.Contain);
            Qt.callLater(function() {
                if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original) || !Qt.isQtObject(table))return;
                const row=table.itemAtIndex(index);
                if(!Qt.isQtObject(row) || !row.selector.enabled)return;
                const flick=choiceScroll.contentItem;
                if(!Qt.isQtObject(flick) || !Qt.isQtObject(flick.contentItem))return;
                const point=row.selector.mapToItem(flick.contentItem,0,0);
                const horizontal=point.x < flick.contentX ? point.x : Math.max(flick.contentX,point.x+row.selector.width-flick.width);
                const vertical=point.y < flick.contentY ? point.y : Math.max(flick.contentY,point.y+row.selector.height-flick.height);
                flick.contentX=Math.max(0,Math.min(horizontal,flick.contentWidth-flick.width));
                if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original) || !Qt.isQtObject(row))return;
                flick.contentY=Math.max(0,Math.min(vertical,flick.contentHeight-flick.height));
                if(Qt.isQtObject(choicePopup) && choicePopup.current(original) && Qt.isQtObject(row) && row.selector.enabled)row.selector.forceActiveFocus();
            });
        }
        function modelAvailable(model,index) { return model.text(index,"available")==="true"; }
        function reconcile(group,original) {
            if(!current(original))return;
            let actual=null;
            for(const button of group.buttons)
                if(Qt.isQtObject(button) && button.selectionCurrent){actual=button;break;}
            group.checkedButton=actual; // Actual selection owns presentation, including a refused/no-op setter.
        }
        function focusModel(start,step,original) {
            if(!current(original))return;
            const model=original.owner.models;
            for(let i=start;i>=0&&i<model.count;i+=step)
                if(modelAvailable(model,i)){focusRow(modelTable,i,original);return;}
            focusEffort(step>0?0:composer.effortChoices.length-1,original);
        }
        function focusEffort(index,original) { focusRow(effortTable,index,original); }
        function chooseModel(id) {
            const original=intent;
            if(!current(original))return;
            let offered=false;
            for(let i=0;i<original.owner.models.count;++i)
                if(original.owner.models.text(i,"id")===id && modelAvailable(original.owner.models,i)){offered=true;break;}
            if(!offered){reconcile(modelSelection,original);return;}
            original.owner.selectedModel=id;
            if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original))return;
            reconcile(modelSelection,original);
            if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original))return;
            const selected=composer.effortChoices.findIndex(row=>row.token===original.owner.selectedEffort);
            focusEffort(Math.max(0,selected),original);
        }
        function chooseEffort(token) {
            const original=intent;
            if(!current(original))return;
            if(!composer.effortChoices.some(row=>row.token===token)){reconcile(effortSelection,original);return;}
            original.owner.selectedEffort=token;
            if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original))return;
            reconcile(effortSelection,original);
            if(Qt.isQtObject(choicePopup) && choicePopup.current(original))close();
        }
        onOpened: {
            const original=intent;
            reconcile(modelSelection,original);
            if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original))return;
            reconcile(effortSelection,original);
            if(!Qt.isQtObject(choicePopup) || !choicePopup.current(original))return;
            focusModel(Math.max(0,composer.selectedModelRow),1,original);
        }
        onClosed: {
            const original=intent;
            intent=null;
            if(Qt.isQtObject(choicePopup) && choicePopup.intent===null && Qt.isQtObject(composer) && original && original.owner===composer.assistant && composer.choicesEnabled && modelEffortButton.visible)modelEffortButton.forceActiveFocus();
        }
        ScrollView {
            id: choiceScroll
            width: choicePopup.contentWidth
            height: choicePopup.contentHeight
            contentWidth: choiceContent.implicitWidth
            contentHeight: choiceContent.implicitHeight
            clip: false
            contentItem.clip: true
            ScrollBar.vertical: EaElements.ScrollBar {
                id: choiceVerticalScrollBar
                parent: choiceScroll
                x: choiceScroll.mirrored ? -(choicePopup.leftPadding+width)/2 : choiceScroll.width+(choicePopup.rightPadding-width)/2
                y: 0
                height: choiceScroll.availableHeight
                visible: choiceScroll.contentHeight > choiceScroll.availableHeight
                policy: ScrollBar.AsNeeded
            }
            ScrollBar.horizontal: EaElements.ScrollBar {
                id: choiceHorizontalScrollBar
                parent: choiceScroll
                x: 0
                y: choiceScroll.height+(choicePopup.bottomPadding-height)/2
                width: choiceScroll.availableWidth
                visible: choiceScroll.contentWidth > choiceScroll.availableWidth
                policy: ScrollBar.AsNeeded
            }
            Row {
                id: choiceContent
                spacing: AppSizes.unit * 1.5
                Column {
                    width: choicePopup.tableWidth
                    spacing: AppSizes.unit * 0.5
                    EaElements.Label { text: qsTr("Model"); font.bold: true; width: parent.width }
                DataTable {
                    id: modelTable
                    objectName: "assistant.choice.models"
                    width: choicePopup.tableWidth
                    sourceModel: composer.assistant.models
                    maxRowCountShow: Math.max(1,count)
                    topMargin: EaStyle.Sizes.borderThickness
                    bottomMargin: EaStyle.Sizes.borderThickness
                    height: (count === 0 ? tableRowHeight*2 : tableRowHeight*visibleRowCount+_headerHeight)+topMargin+bottomMargin
                    interactive: false
                    scrollBarPolicy: ScrollBar.AlwaysOff
                    marksCurrentRow: true
                    currentRow: composer.selectedModelRow
                    columnWidths: [choicePopup.radioColumnWidth,choicePopup.desiredLabelWidth]
                    delegate: EaComponents.ListViewDelegate {
                        id: modelRow
                        required property int index
                        required property var model
                        readonly property string modelId: model.id
                        readonly property alias selector: modelRadio
                        objectName: "assistant.choice.model.row."+modelId
                        Item {
                            property int horizontalAlignment: Text.AlignHCenter
                            height: parent.height
                            EaElements.RadioButton {
                                id: modelRadio
                                objectName: "assistant.choice.model."+modelRow.modelId
                                anchors.centerIn: parent
                                width: parent.width; height: parent.height
                                padding: 0
                                ButtonGroup.group: modelSelection
                                readonly property bool selectionCurrent: composer.assistant.selectedModel===modelRow.modelId
                                checked: selectionCurrent
                                enabled: composer.choicesEnabled && modelRow.model.available
                                Accessible.name: modelRow.model.displayName
                                ToolTip.text: modelRow.model.displayName
                                onClicked: choicePopup.chooseModel(modelRow.modelId)
                                Keys.onReturnPressed: event=>{choicePopup.chooseModel(modelRow.modelId);event.accepted=true;}
                                Keys.onEnterPressed: event=>{choicePopup.chooseModel(modelRow.modelId);event.accepted=true;}
                                Keys.onTabPressed: event=>{choicePopup.focusModel(modelRow.index+1,1,choicePopup.intent);event.accepted=true;}
                                Keys.onBacktabPressed: event=>{choicePopup.focusModel(modelRow.index-1,-1,choicePopup.intent);event.accepted=true;}
                                Keys.onDownPressed: event=>{choicePopup.focusModel(modelRow.index+1,1,choicePopup.intent);event.accepted=true;}
                                Keys.onUpPressed: event=>{choicePopup.focusModel(modelRow.index-1,-1,choicePopup.intent);event.accepted=true;}
                            }
                        }
                        EaComponents.TableViewLabel {
                            objectName: "assistant.choice.model.label."+modelRow.modelId
                            text: modelRow.model.displayName
                            textFormat: Text.PlainText
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideNone
                            color: modelRow.model.available ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                            ToolTip.text: text
                            TapHandler { enabled: composer.choicesEnabled && modelRow.model.available; onTapped: choicePopup.chooseModel(modelRow.modelId) }
                        }
                    }
                }
                }
                Column {
                    width: choicePopup.tableWidth
                    spacing: AppSizes.unit * 0.5
                    EaElements.Label { text: qsTr("Reasoning effort"); font.bold: true; width: parent.width }
                DataTable {
                    id: effortTable
                    objectName: "assistant.choice.efforts"
                    width: choicePopup.tableWidth
                    sourceModel: composer.effortChoices
                    maxRowCountShow: Math.max(1,count)
                    topMargin: EaStyle.Sizes.borderThickness
                    bottomMargin: EaStyle.Sizes.borderThickness
                    height: (count === 0 ? tableRowHeight*2 : tableRowHeight*visibleRowCount+_headerHeight)+topMargin+bottomMargin
                    interactive: false
                    scrollBarPolicy: ScrollBar.AlwaysOff
                    marksCurrentRow: true
                    currentRow: composer.effortChoices.findIndex(row=>row.token===composer.assistant.selectedEffort)
                    columnWidths: [choicePopup.radioColumnWidth,choicePopup.desiredLabelWidth]
                    delegate: EaComponents.ListViewDelegate {
                        id: effortRow
                        required property int index
                        required property var modelData
                        readonly property string choiceId: modelData.token.length ? "assistant.choice.effort.value."+modelData.token : "assistant.choice.effort.default"
                        readonly property alias selector: effortRadio
                        objectName: choiceId+".row"
                        Item {
                            property int horizontalAlignment: Text.AlignHCenter
                            height: parent.height
                            EaElements.RadioButton {
                                id: effortRadio
                                objectName: effortRow.choiceId
                                anchors.centerIn: parent
                                width: parent.width; height: parent.height
                                padding: 0
                                ButtonGroup.group: effortSelection
                                readonly property bool selectionCurrent: composer.assistant.selectedEffort===effortRow.modelData.token
                                checked: selectionCurrent
                                enabled: composer.choicesEnabled
                                Accessible.name: effortRow.modelData.label
                                ToolTip.text: effortRow.modelData.token.length ? effortRow.modelData.label : qsTr("Provider default reasoning effort")
                                onClicked: choicePopup.chooseEffort(effortRow.modelData.token)
                                Keys.onReturnPressed: event=>{choicePopup.chooseEffort(effortRow.modelData.token);event.accepted=true;}
                                Keys.onEnterPressed: event=>{choicePopup.chooseEffort(effortRow.modelData.token);event.accepted=true;}
                                Keys.onTabPressed: event=>{if(effortRow.index+1<effortTable.count)choicePopup.focusEffort(effortRow.index+1,choicePopup.intent);else choicePopup.focusModel(0,1,choicePopup.intent);event.accepted=true;}
                                Keys.onBacktabPressed: event=>{if(effortRow.index>0)choicePopup.focusEffort(effortRow.index-1,choicePopup.intent);else choicePopup.focusModel(modelTable.count-1,-1,choicePopup.intent);event.accepted=true;}
                                Keys.onDownPressed: event=>{if(effortRow.index+1<effortTable.count)choicePopup.focusEffort(effortRow.index+1,choicePopup.intent);event.accepted=true;}
                                Keys.onUpPressed: event=>{if(effortRow.index>0)choicePopup.focusEffort(effortRow.index-1,choicePopup.intent);event.accepted=true;}
                            }
                        }
                        EaComponents.TableViewLabel {
                            objectName: effortRow.choiceId+".label"
                            text: effortRow.modelData.label
                            textFormat: Text.PlainText
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideNone
                            ToolTip.text: text
                            TapHandler { enabled: composer.choicesEnabled; onTapped: choicePopup.chooseEffort(effortRow.modelData.token) }
                        }
                    }
                }
                }
            }
        }
    }
    onWidthChanged: closeChoices()
    Connections {
        target: Preferences
        function onSideBarOnLeftChanged() { composer.closeChoices(); }
    }
    property bool hasPreviousUserMessage: false
    property bool hasNextUserMessage: false
    signal previousUserRequested()
    signal nextUserRequested()
    signal contextApprovalRequested(string draft)
    property int textRevision: 0
    property int selectionRevision: -1
    property int savedSelectionStart: 0
    property int savedSelectionEnd: 0
    property var submittedDrafts: []
    property int draftOwnerRevision: 0
    property int pendingFileCount: 0
    readonly property bool canSteer: assistant.state === "agent_active"
    readonly property bool hasDraft: editor.text.trim().length > 0
    function chooseFiles() {
        if (WebFiles.available || !assistant.connected || assistant.canCancel || nativeFiles.requestId.length) return;
        const original=assistant;
        const request=original.beginFileSelection(true);
        if (!Qt.isQtObject(composer) || !Qt.isQtObject(original) || original!==composer.assistant || !original.connected || !request.length) {
            if (Qt.isQtObject(original)) original.cancelFileSelection(request);
            return;
        }
        const intent={owner:original,id:request};
        nativeFiles.selection=intent;
        if (Qt.isQtObject(nativeFiles) && nativeFiles.selection===intent) nativeFiles.open();
        else if (Qt.isQtObject(original)) original.cancelFileSelection(request);
    }
    FileDialog {
        id: nativeFiles
        objectName: "assistant.files.dialog"
        property var selection: null
        readonly property string requestId: selection ? selection.id : ""
        readonly property var original: selection ? selection.owner : null
        title: qsTr("Add files to the assistant")
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            const target=original; const request=requestId; const files=selectedFiles;
            selection=null;
            if (!Qt.isQtObject(target)) return;
            if (Qt.isQtObject(composer) && target===composer.assistant && target.connected) target.addSelectedFiles(request,files);
            else target.cancelFileSelection(request);
        }
        onRejected: {
            const target=original; const request=requestId;
            selection=null;
            if (Qt.isQtObject(target)) target.cancelFileSelection(request);
        }
        Component.onDestruction: {
            const target=original; const request=requestId;
            selection=null;
            if (Qt.isQtObject(target)) target.cancelFileSelection(request);
        }
    }
    Connections {
        target: nativeFiles.original
        function onFileSelectionRetired(requestId) {
            if (nativeFiles.requestId!==requestId) return;
            nativeFiles.selection=null;
            if (Qt.isQtObject(nativeFiles) && nativeFiles.selection===null) nativeFiles.reject();
        }
    }
    function acknowledgeVisiblePrompt() {
        const original = submittedDrafts;
        const ownerRevision = draftOwnerRevision;
        const pending = [];
        let acknowledged = null;
        for (const draft of original) {
            let status = "";
            for (let i = 0; i < assistant.messages.count; ++i)
                if (assistant.messages.text(i, "id") === draft.id && assistant.messages.text(i, "kind") === "user") {
                    status = assistant.messages.text(i, "status"); break;
                }
            if (status === "completed") {
                if (draft.revision === textRevision && draft.text === editor.text
                    && !editor.inputMethodComposing && editor.preeditText.length === 0) acknowledged = draft;
            } else if (status !== "refused" && status !== "interrupted") pending.push(draft);
        }
        if (submittedDrafts !== original || draftOwnerRevision !== ownerRevision) return;
        submittedDrafts = pending; // Retire old bookkeeping before text notification can admit a new draft.
        if (acknowledged && draftOwnerRevision === ownerRevision && textRevision === acknowledged.revision
            && editor.text === acknowledged.text && !editor.inputMethodComposing
            && editor.preeditText.length === 0) editor.clear();
    }
    function refreshFilePresentation() {
        let pending = 0;
        for (let i = 0; i < assistant.selectedFiles.count; ++i)
            if (assistant.selectedFiles.text(i, "pending") !== "false") ++pending;
        pendingFileCount = pending;
    }
    Connections {
        target: composer.assistant.messages
        function onCountChanged() { composer.acknowledgeVisiblePrompt(); }
        function onDataChanged() { composer.acknowledgeVisiblePrompt(); }
    }
    Connections {
        target: composer.assistant.selectedFiles
        function onCountChanged() { composer.refreshFilePresentation(); }
        function onDataChanged() { composer.refreshFilePresentation(); }
    }
    Connections {
        target: composer.assistant
        function onConversationRetired() { ++composer.draftOwnerRevision; composer.submittedDrafts = []; }
    }
    Component.onCompleted: refreshFilePresentation()
    implicitHeight: composerContent.implicitHeight + AppSizes.unit * 1.5
    color: EaStyle.Colors.contentBackground
    border.color: EaStyle.Colors.appBorder
    radius: AppSizes.unit
    function rememberSelection() {
        if (editor.activeFocus) {
            savedSelectionStart = editor.selectionStart;
            savedSelectionEnd = editor.selectionEnd;
            selectionRevision = textRevision;
        }
    }
    function focusEditor() {
        if (!assistant.connected) return;
        const restore = selectionRevision === textRevision;
        const start = savedSelectionStart;
        const end = savedSelectionEnd;
        editor.forceActiveFocus();
        if (restore)
            editor.select(start, end);
    }
    function submitApprovedDraft(draft) {
        if (editor.text !== draft || !assistant.connected || assistant.contextConsentRequired)
            return;
        submit();
    }
    function submit() {
        if (!assistant.connected || (assistant.canCancel && !canSteer) || !hasDraft)
            return;
        if (assistant.contextConsentRequired) {
            contextApprovalRequested(editor.text);
            return;
        }
        const text = editor.text, revision = textRevision, ownerRevision = draftOwnerRevision;
        const rowId = assistant.submitDraft(text);
        if (rowId.length && draftOwnerRevision === ownerRevision) {
            const pending = submittedDrafts.slice();
            pending.push({id: rowId, text: text, revision: revision});
            submittedDrafts = pending;
            acknowledgeVisiblePrompt();
        }
    }
    Column {
        id: composerContent
        x: AppSizes.unit * 0.75
        y: AppSizes.unit * 0.75
        width: parent.width - AppSizes.unit * 1.5
        spacing: AppSizes.unit * 0.25
        ScrollView {
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            id: selectedFilesScroll
            width: parent.width
            height: visible ? Math.min(selectedChips.implicitHeight, AppSizes.unit * 5) : 0
            visible: composer.pendingFileCount > 0
            clip: true
            Flow {
                id: selectedChips
                x: editor.leftPadding
                width: Math.max(0, selectedFilesScroll.availableWidth - editor.leftPadding - editor.rightPadding)
                spacing: AppSizes.unit * 0.75
            Repeater {
                model: composer.assistant.selectedFiles
                delegate: RowLayout {
                    required property var model
                    objectName: "assistant.file." + model.id
                    visible: model.pending !== false
                    spacing: AppSizes.unit * 0.125
                    EaElements.Label {
                        Layout.maximumWidth: composerContent.width * 0.6
                        text: qsTr("%1 (%2 bytes)%3").arg(model.name).arg(model.bytes)
                            .arg(model.textReadable ? "" : qsTr(" · text export required"))
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        Accessible.name: qsTr("Selected file: %1, %2 bytes. %3").arg(model.name).arg(model.bytes)
                            .arg(model.textReadable ? qsTr("Available for consented text reads") : qsTr("Unsupported binary; text export required"))
                    }
                    EaElements.ToolButton {
                        id: removeFileButton
                        fontIcon: "times"
                        implicitWidth: composer.actionSize
                        implicitHeight: composer.actionSize
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.6
                        showBackground: false
                        contentItem: EaElements.Label {
                            text: removeFileButton.fontIcon
                            font.family: EaStyle.Fonts.iconsFamily
                            font.pixelSize: removeFileButton.font.pixelSize * 1.25
                            color: removeFileButton.foregroundColor()
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                        }
                        enabled: composer.assistant.connected && !composer.assistant.canCancel
                        ToolTip.text: qsTr("Remove %1").arg(model.name)
                        Accessible.name: ToolTip.text
                        onClicked: composer.assistant.removeSelectedFile(model.id)
                    }
                }
            }
            }
        }
        ScrollView {
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            width: parent.width
            height: Math.min(AppSizes.unit * 10, Math.max(editor.font.pixelSize * 2.5 + editor.topPadding + editor.bottomPadding, editor.implicitHeight))
            TextArea {
                id: editor
                objectName: "assistant.composer"
                placeholderText: qsTr("Ask about your project or describe a refinement plan…")
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                persistentSelection: true
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: addFilesButton
                KeyNavigation.backtab: composer.previousFocusItem
                onTextChanged: ++composer.textRevision
                onPreeditTextChanged: ++composer.textRevision
                onInputMethodComposingChanged: ++composer.textRevision
                onSelectionStartChanged: composer.rememberSelection()
                onSelectionEndChanged: composer.rememberSelection()
                color: EaStyle.Colors.themeForeground
                placeholderTextColor: EaStyle.Colors.themeForegroundMinor
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                padding: AppSizes.unit * 0.4
                background: null
                Accessible.name: qsTr("Message to the assistant")
                Keys.onReturnPressed: event => {
                    if (event.modifiers & Qt.ShiftModifier) {
                        event.accepted = false;
                    } else {
                        composer.submit();
                        event.accepted = true;
                    }
                }
            }
        }
        RowLayout {
            id: composerToolbar
            readonly property real choiceWidth: Math.max(0, width - addFilesButton.implicitWidth - showActionsControl.implicitWidth
                - (sendButton.visible ? sendButton.implicitWidth : 0) - (stopButton.visible ? stopButton.implicitWidth : 0)
                - previousUserButton.implicitWidth - nextUserButton.implicitWidth
                - spacing * (5+(sendButton.visible ? 1 : 0)+(stopButton.visible ? 1 : 0)))
            width: parent.width
            spacing: AppSizes.unit * 0.5
            EaElements.ToolButton {
                id: addFilesButton
                objectName: "assistant.files.add"
                fontIcon: "plus"
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                showBackground: false
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    color: addFilesButton.hovered || addFilesButton.activeFocus ? EaStyle.Colors.themeBackgroundHovered1 : composer.lightActionBackground
                    radius: width * 0.5
                }
                enabled: composer.assistant.connected && !WebFiles.available && !composer.assistant.canCancel
                ToolTip.text: WebFiles.available ? qsTr("Browser file selection is not available yet") : qsTr("Add files")
                Accessible.name: qsTr("Add files")
                Accessible.description: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: editor
                KeyNavigation.tab: showActionsControl
                onClicked: composer.chooseFiles()
            }
            EaElements.ToolButton {
                id: showActionsControl
                objectName: "assistant.showActions"
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                fontIcon: "eye"
                checkable: true
                checked: composer.assistant.showActions
                highlighted: checked
                font.pixelSize: EaStyle.Sizes.fontPixelSize*0.75
                contentItem: EaElements.Label {
                    text: showActionsControl.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: showActionsControl.font.pixelSize*1.25
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: !showActionsControl.enabled ? EaStyle.Colors.themeForegroundDisabled : showActionsControl.checked ? EaStyle.Colors.themeAccent : showActionsControl.foregroundColor()
                }
                background: Rectangle {
                    implicitWidth: composer.actionSize; implicitHeight: implicitWidth
                    radius: width*0.5
                    color: showActionsControl.hovered || showActionsControl.activeFocus ? EaStyle.Colors.themeBackgroundHovered1 : composer.lightActionBackground
                }
                enabled: composer.assistant.connected && !composer.assistant.canCancel
                ToolTip.text: qsTr("Show actions")
                Accessible.name: ToolTip.text
                Accessible.description: qsTr("Use real visible controls for supported actions")
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: addFilesButton
                KeyNavigation.tab: modelEffortButton
                onToggled: composer.assistant.showActions = checked
            }
            EaElements.Button {
                id: modelEffortButton
                objectName: "assistant.modelEffort"
                Layout.preferredWidth: choiceMetrics.advanceWidth(composer.modelLabel+" "+composer.selectedEffortLabel)+leftPadding+rightPadding
                Layout.maximumWidth: composerToolbar.choiceWidth
                implicitHeight: composer.actionSize
                leftPadding: AppSizes.unit*0.75
                rightPadding: AppSizes.unit*0.75
                enabled: composer.choicesEnabled
                background: Rectangle {
                    implicitHeight: composer.actionSize
                    radius: height*0.5
                    color: modelEffortButton.hovered || modelEffortButton.activeFocus ? EaStyle.Colors.themeBackgroundHovered1 : composer.lightActionBackground
                }
                contentItem: Row {
                    id: modelEffortText
                    spacing: choiceMetrics.advanceWidth(" ")
                    EaElements.Label {
                        id: modelPillLabel
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        text: composer.modelLabel
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        width: Math.max(0,Math.min(implicitWidth,modelEffortButton.availableWidth-effortPillLabel.width-modelEffortText.spacing))
                    }
                    EaElements.Label {
                        id: effortPillLabel
                        height: parent.height
                        verticalAlignment: Text.AlignVCenter
                        text: composer.selectedEffortLabel
                        textFormat: Text.PlainText
                        color: EaStyle.Colors.themeForegroundMinor
                        elide: Text.ElideRight
                        width: Math.max(0,Math.min(implicitWidth,modelEffortButton.availableWidth*0.45))
                    }
                }
                ToolTip.text: qsTr("Model: %1 · Reasoning effort: %2").arg(composer.modelLabel).arg(composer.selectedEffortLabel)
                Accessible.name: ToolTip.text
                Accessible.description: qsTr("Choose model and reasoning effort")
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: showActionsControl
                KeyNavigation.tab: previousUserButton
                onClicked: composer.openChoices()
                Keys.priority: Keys.BeforeItem
                Keys.onPressed: event=>{
                    if(event.key===Qt.Key_Return || event.key===Qt.Key_Enter){
                        event.accepted=true;
                        if(!event.isAutoRepeat)composer.openChoices();
                    } else event.accepted=false;
                }
                Keys.onReleased: event=>{
                    event.accepted=event.key===Qt.Key_Return || event.key===Qt.Key_Enter;
                }
            }
            Item { Layout.fillWidth: true }
            EaElements.ToolButton {
                id: previousUserButton
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                objectName: "assistant.previousUserMessage"
                fontIcon: "chevron-up"
                enabled: composer.hasPreviousUserMessage
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: previousUserButton.hovered || previousUserButton.activeFocus ? EaStyle.Colors.themeBackgroundHovered1 : composer.lightActionBackground
                }
                ToolTip.text: qsTr("Previous user message")
                Accessible.name: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: modelEffortButton
                KeyNavigation.tab: nextUserButton
                onClicked: composer.previousUserRequested()
            }
            EaElements.ToolButton {
                id: nextUserButton
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                objectName: "assistant.nextUserMessage"
                fontIcon: "chevron-down"
                enabled: composer.hasNextUserMessage
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: nextUserButton.hovered || nextUserButton.activeFocus ? EaStyle.Colors.themeBackgroundHovered1 : composer.lightActionBackground
                }
                ToolTip.text: qsTr("Next user message")
                Accessible.name: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: previousUserButton
                KeyNavigation.tab: stopButton.visible ? stopButton : sendButton
                onClicked: composer.nextUserRequested()
            }
            EaElements.ToolButton {
                id: stopButton
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: composer.canSteer && composer.hasDraft ? stopButton.backgroundColor() : (EaStyle.Colors.isDarkPalette ? "white" : "black")
                }
                contentItem: EaElements.Label {
                    opacity: stopButton.enabled ? 1 : 0.35
                    text: stopButton.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: stopButton.font.pixelSize * 1.25
                    color: composer.canSteer && composer.hasDraft ? stopButton.foregroundColor() : (EaStyle.Colors.isDarkPalette ? "black" : "white")
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: sendButton.visible ? sendButton : composer.toggleControl
                KeyNavigation.backtab: nextUserButton
                objectName: "assistant.stop"
                fontIcon: "stop"
                text: qsTr("Stop")
                ToolTip.text: text
                visible: composer.assistant.canCancel
                enabled: visible
                Accessible.name: text
                onClicked: composer.assistant.cancel()
            }
            EaElements.ToolButton {
                id: sendButton
                Layout.minimumWidth: composer.actionSize
                Layout.maximumWidth: composer.actionSize
                Layout.minimumHeight: composer.actionSize
                Layout.maximumHeight: composer.actionSize
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: sendButton.enabled ? (EaStyle.Colors.isDarkPalette ? "white" : "black") : EaStyle.Colors.themeBackgroundDisabled
                }
                contentItem: EaElements.Label {
                    text: sendButton.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: sendButton.font.pixelSize * 1.25
                    color: sendButton.enabled ? (EaStyle.Colors.isDarkPalette ? "black" : "white") : sendButton.foregroundColor()
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: composer.toggleControl
                KeyNavigation.backtab: nextUserButton
                objectName: "assistant.send"
                fontIcon: "arrow-up"
                text: qsTr("Send")
                ToolTip.text: text
                highlighted: true
                visible: !composer.assistant.canCancel || (composer.canSteer && composer.hasDraft)
                enabled: composer.assistant.connected && (!composer.assistant.canCancel || composer.canSteer) && composer.hasDraft
                Accessible.name: text
                onClicked: composer.submit()
            }
        }
    }
}
