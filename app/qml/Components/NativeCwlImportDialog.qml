// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// One ordinary manual form; visible actions use its actual controls and Apply;
// no provider is required and no project changes while any field is a draft.
AppDialog {
    id: dialog
    objectName: "nativeImport.dialog"
    required property AssistantViewModel assistant
    signal filesRequested()
    property string requestId: ""
    property string localError: ""
    property bool closeInProgress: false
    property string closingRequestId: ""
    property string pendingRequestId: ""
    readonly property var outcome: assistant.nativeImport.id === requestId ? assistant.nativeImport : ({})
    readonly property bool busy: outcome.state === "preparing"
    readonly property bool created: outcome.state === "created"
    readonly property bool editable: requestId.length > 0 && outcome.retryable === true
        && (outcome.state === "draft" || outcome.state === "refused")
    readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
    title: qsTr("Import a CW neutron experiment")
    width: Math.min(AppSizes.unit * 52, Math.max(0, parent.width - AppSizes.unit * 2))
    contentWidth: Math.max(0, width - leftPadding - rightPadding)
    contentHeight: Math.min(AppSizes.unit * 35, Math.max(0, viewportHeight - topPadding - bottomPadding
        - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
        - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
    standardButtons: Dialog.Close
    function currentIntent(intent) {
        const state = assistant.nativeImport;
        return intent.length > 0 && state.id === intent && state.retryable === true
            && (state.state === "draft" || state.state === "refused");
    }
    function openNew() {
        if (closeInProgress) return;
        const automatic = assistant.showingActions;
        // Actual common form identity is captured before backend publication.
        const intent = assistant.beginNativeImport(dialog);
        if (intent.length) openWithIntent(intent);
        else if (!automatic && !visible && !closeInProgress && requestId.length === 0 && assistant.nativeImport.retryable !== true) {
            localError = qsTr("Finish the active operation and use an empty project Session before importing.");
            open();
        }
    }
    function openWithIntent(intent) {
        if (!currentIntent(intent)) return;
        if (closeInProgress) {
            if (assistant.nativeImport.state === "draft") pendingRequestId = intent;
            return;
        }
        const current = () => requestId === intent && !closeInProgress && currentIntent(intent);
        // Each ordinary view mutation can synchronously notify observers. Stop
        // before touching a newer form if that boundary retires this intent.
        requestId = intent;
        if (!current()) { retireAssistantForm(intent); return; }
        localError = "";
        if (!current()) { retireAssistantForm(intent); return; }
        loadingRow = false;
        if (!current()) { retireAssistantForm(intent); return; }
        projectName.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        description.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        experimentName.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        wavelength.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        zero.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        scale.text = "";
        if (!current()) { retireAssistantForm(intent); return; }
        backgrounds.clear();
        if (!current()) { retireAssistantForm(intent); return; }
        exclusions.clear();
        if (!current()) { retireAssistantForm(intent); return; }
        parameters.clear();
        if (!current()) { retireAssistantForm(intent); return; }
        sections.currentIndex = 0;
        if (!current()) { retireAssistantForm(intent); return; }
        cif.currentIndex = -1;
        if (!current()) { retireAssistantForm(intent); return; }
        measurement.currentIndex = -1;
        if (!current()) { retireAssistantForm(intent); return; }
        profile.model = assistant.nativeImportProfiles();
        if (!current()) { retireAssistantForm(intent); return; }
        profile.currentIndex = -1;
        if (!current()) { retireAssistantForm(intent); return; }
        open();
        // An enter/open notification may itself retire the original. Closing
        // the exact old form cannot consume a nested new request's identity.
        if (!current() && requestId === intent && !closeInProgress) retireAssistantForm(intent);
    }
    function retireAssistantForm(intent) {
        if (requestId !== intent) return;
        if (!visible && !closeInProgress) {
            requestId = ""; // close() cannot emit closed for a never-opened popup.
            if (pendingRequestId === intent) pendingRequestId = "";
            assistant.cancelNativeImport(intent);
            return;
        }
        beginImportClose();
        close();
    }
    function beginImportClose() {
        if (closeInProgress) return;
        closeInProgress = true;
        closingRequestId = requestId;
        const original = closingRequestId;
        requestId = ""; // Consume before cancellation can reenter a newer picker/form.
        if (original.length) assistant.cancelNativeImport(original);
    }
    // Rejection begins before Qt's close; all other actual hide entrances
    // converge on aboutToHide, BEFORE EA's exit animation/late worker delivery.
    onRejected: beginImportClose()
    onAboutToHide: beginImportClose()
    onClosed: {
        const original = closingRequestId;
        const pending = pendingRequestId;
        closingRequestId = "";
        pendingRequestId = "";
        closeInProgress = false;
        if (original.length) assistant.cancelNativeImport(original); // Exact old intent only, idempotent.
        if (pending.length) Qt.callLater(() => {
            if (!dialog.visible && !dialog.closeInProgress && dialog.requestId.length === 0
                && dialog.assistant.nativeImport.id === pending && dialog.assistant.nativeImport.state === "draft") dialog.openWithIntent(pending);
        });
    }
    Component.onDestruction: {
        const original = requestId;
        const pending = pendingRequestId;
        requestId = "";
        pendingRequestId = "";
        if (assistant) {
            if (original.length) assistant.cancelNativeImport(original);
            if (pending.length && pending !== original) assistant.cancelNativeImport(pending);
        }
    }
    function finiteValue(field) {
        if (field.text.trim().length === 0 || !Number.isFinite(Number(field.text)))
            throw new Error(qsTr("Complete every numeric field with a finite value."));
        return Number(field.text);
    }
    function pairs(model, first, second) {
        const result = [];
        for (let i = 0; i < model.count; ++i) {
            const row = model.get(i);
            if (row.firstValue.trim().length === 0 || row.secondValue.trim().length === 0
                || !Number.isFinite(Number(row.firstValue)) || !Number.isFinite(Number(row.secondValue)))
                throw new Error(qsTr("Complete both numbers in every row, or remove that row."));
            const value = {};
            value[first] = Number(row.firstValue);
            value[second] = Number(row.secondValue);
            result.push(value);
        }
        return result;
    }
    function apply() {
        localError = "";
        try {
            if (!editable || cif.currentIndex < 0 || measurement.currentIndex < 0 || profile.currentIndex < 0)
                throw new Error(qsTr("Choose the two input files and a supported peak profile."));
            // Keep the existing raw-draft preprocessing bound. The complete
            // serialized recipe is admitted exactly below, before stringify.
            let encodedBound = 2048;
            const admitText = text => {
                if (text.length > 1048576 || encodedBound > 8388608 - 6 * text.length)
                    throw new Error(qsTr("The complete import recipe exceeds capacity."));
                encodedBound += 6 * text.length;
            };
            for (const field of [projectName, experimentName, description, wavelength, zero, scale]) admitText(field.text);
            for (const model of [backgrounds, exclusions, parameters]) {
                if (model.count > 256) throw new Error(qsTr("Too many import rows."));
                for (let i = 0; i < model.count; ++i) {
                    const row = model.get(i);
                    admitText(model === parameters ? row.parameterPath : row.firstValue);
                    admitText(model === parameters ? row.parameterValue : row.secondValue);
                    if (encodedBound > 8388608 - 128) throw new Error(qsTr("The complete import recipe exceeds capacity."));
                    encodedBound += 128;
                }
            }
            const values = [];
            for (let i = 0; i < parameters.count; ++i) {
                const row = parameters.get(i);
                if (row.parameterPath.trim().length === 0 || row.parameterValue.trim().length === 0 || !Number.isFinite(Number(row.parameterValue)))
                    throw new Error(qsTr("Complete each initial parameter path and numeric value."));
                values.push({path: row.parameterPath, value: Number(row.parameterValue)});
            }
            const recipe = {project_name: projectName.text, description: description.text, experiment_name: experimentName.text,
                sample_form: "powder", beam_mode: "constant wavelength", radiation_probe: "neutron", scattering_type: "bragg",
                peak_profile: profile.currentText, wavelength: finiteValue(wavelength), zero_offset: finiteValue(zero), phase_scale: finiteValue(scale),
                background: pairs(backgrounds, "position", "intensity"), exclusions: pairs(exclusions, "first", "second"), initial_parameters: values};
            // Count the actual JSON spelling of this plain recipe, following
            // the same bounded value walk as the native request-size counter.
            // JSON.stringify remains the only writer; no encoded copy yet exists.
            const recipeLimit = 1048576; // edi::assistant::Limits::context_bytes
            let recipeBytes = 0;
            const admitBytes = count => {
                if (count > recipeLimit - recipeBytes)
                    throw new Error(qsTr("The complete import recipe exceeds capacity."));
                recipeBytes += count;
            };
            const admitString = text => {
                admitBytes(2);
                for (let i = 0; i < text.length; ++i) {
                    const c = text.charCodeAt(i);
                    if (c === 34 || c === 92 || c === 8 || c === 9 || c === 10 || c === 12 || c === 13) admitBytes(2);
                    else if (c < 32) admitBytes(6);
                    else if (c < 128) admitBytes(1);
                    else if (c < 2048) admitBytes(2);
                    else if (c >= 0xd800 && c <= 0xdbff && i + 1 < text.length
                             && text.charCodeAt(i + 1) >= 0xdc00 && text.charCodeAt(i + 1) <= 0xdfff) {
                        admitBytes(4);
                        ++i;
                    } else if (c >= 0xd800 && c <= 0xdfff) admitBytes(0); // Pinned Qt stringify retains it; its stateless UTF8 conversion omits an isolated unit.
                    else admitBytes(3);
                }
            };
            const admitValue = value => {
                if (typeof value === "string") admitString(value);
                else if (typeof value === "number" && Number.isFinite(value)) admitBytes(String(value).length);
                else if (Array.isArray(value)) {
                    admitBytes(2);
                    for (let i = 0; i < value.length; ++i) {
                        if (i) admitBytes(1);
                        admitValue(value[i]);
                    }
                } else if (value !== null && typeof value === "object") {
                    admitBytes(2);
                    const keys = Object.keys(value);
                    for (let i = 0; i < keys.length; ++i) {
                        if (i) admitBytes(1);
                        admitString(keys[i]);
                        admitBytes(1);
                        admitValue(value[keys[i]]);
                    }
                } else throw new Error(qsTr("The import recipe contains an unsupported value."));
            };
            admitValue(recipe);
            const cifId = assistant.selectedFiles.text(cif.currentIndex, "id");
            const dataId = assistant.selectedFiles.text(measurement.currentIndex, "id");
            if (!assistant.applyNativeImport(requestId, cifId, dataId, JSON.stringify(recipe)))
                localError = outcome.message || qsTr("The source selection or empty Session changed; reopen the import form.");
        } catch (error) { localError = String(error.message || error); }
    }
    ListModel { id: backgrounds }
    ListModel { id: exclusions }
    ListModel { id: parameters }
    readonly property var rowModel: modelForSection(sections.currentIndex)
    readonly property int sectionIndex: sections.currentIndex
    readonly property int rowCount: rowModel.count
    readonly property int selectedRow: rowSelector.currentIndex
    property bool loadingRow: false
    property var rowProjection: null
    function modelForSection(section) {
        return section === 2 ? backgrounds : section === 3 ? exclusions : parameters;
    }
    function rowSelectionCurrent(intent, section, model) {
        return requestId === intent && sections.currentIndex === section
            && rowModel === model && model === modelForSection(section);
    }
    function projectionCurrent(projection) {
        return rowProjection === projection
            && rowSelectionCurrent(projection.intent, projection.section, projection.model)
            && selectedRow === projection.index;
    }
    function selectRowSection() {
        if (!rowSelector) return;
        const intent = requestId, section = sections.currentIndex, model = rowModel;
        if (!rowSelectionCurrent(intent, section, model)) return;
        rowSelector.currentIndex = model.count ? 0 : -1;
        if (rowSelectionCurrent(intent, section, model)) loadRow();
    }
    onRowModelChanged: selectRowSection()
    function loadRow() {
        if (!rowSelector || !first || !second) return;
        const intent = requestId, section = sections.currentIndex, model = rowModel, index = selectedRow;
        if (!rowSelectionCurrent(intent, section, model)) return;
        // The captured actual model owns its roles, including when the row
        // editor is hidden on Inputs/Instrument or tab bindings are settling.
        const valid = index >= 0 && index < model.count;
        const row = valid ? model.get(index) : null;
        const parameter = model === parameters;
        const firstValue = row ? (parameter ? row.parameterPath : row.firstValue) : "";
        const secondValue = row ? (parameter ? row.parameterValue : row.secondValue) : "";
        if (typeof firstValue !== "string" || typeof secondValue !== "string") return;
        const projection = {intent: intent, section: section, model: model, index: index};
        rowProjection = projection;
        if (!projectionCurrent(projection)) return;
        loadingRow = true;
        try {
            if (!projectionCurrent(projection)) return;
            first.text = firstValue;
            if (!projectionCurrent(projection)) return;
            second.text = secondValue;
        } finally {
            // A nested row load owns its own loading state. Old cleanup must
            // not release the write fence around a newer request/selection.
            if (rowProjection === projection) loadingRow = false;
        }
    }
    function rowText(firstField, value) {
        const projection = rowProjection;
        if (loadingRow || !projection || !projectionCurrent(projection) || !editable
            || projection.index < 0 || projection.index >= projection.model.count) return;
        const parameter = projection.model === parameters;
        const key = parameter ? (firstField ? "parameterPath" : "parameterValue") : (firstField ? "firstValue" : "secondValue");
        projection.model.setProperty(projection.index, key, value);
    }
    function appendRow() {
        const intent = requestId, section = sections.currentIndex, model = rowModel;
        if (!editable || model.count >= 256 || !rowSelectionCurrent(intent, section, model)) return;
        if (model === parameters) model.append({parameterPath: "", parameterValue: ""});
        else model.append({firstValue: "", secondValue: ""});
        if (!rowSelectionCurrent(intent, section, model)) return;
        rowSelector.currentIndex = model.count - 1;
        if (rowSelectionCurrent(intent, section, model)) loadRow();
    }
    function removeRow() {
        const intent = requestId, section = sections.currentIndex, model = rowModel, index = selectedRow;
        if (!editable || !rowSelectionCurrent(intent, section, model) || index < 0 || index >= model.count) return;
        model.remove(index);
        if (!rowSelectionCurrent(intent, section, model)) return;
        // Respect a selection established synchronously by the removal or a
        // genuine observer; only adjust the still-original selection.
        if (selectedRow === index) rowSelector.currentIndex = Math.min(index, model.count - 1);
        if (rowSelectionCurrent(intent, section, model)) loadRow();
    }
    // Compact multiline editors preserve the same admitted Unicode/control
    // text as the native recipe; final Apply alone interprets numeric fields.
    component DraftField: TextArea {
        property string originalAssistantText: ""
        property bool assistantEditing: false
        readonly property string editText: text
        readonly property bool assistantManualDraft: false // Staged form, never a blur scientific commit.
        selectByMouse: true
        wrapMode: TextEdit.NoWrap
        Layout.preferredHeight: AppSizes.unit * 2
        Keys.onTabPressed: event => { insert(cursorPosition, "\t"); event.accepted = true; }
        Layout.fillWidth: true
        function beginAssistantEdit() { originalAssistantText = text; assistantEditing = true; }
        function allowAssistantCommit() { assistantEditing = false; originalAssistantText = ""; }
        function cancelAssistantEdit() {
            if (!assistantEditing) return;
            text = originalAssistantText;
            assistantEditing = false;
            originalAssistantText = "";
        }
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: AppSizes.unit * 0.5
        EaElements.Label {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: qsTr("Import one powder / CW / neutron / Bragg phase from selected input files. Enter actual scientific choices; Apply creates unsaved data, without fitting. A scientifically empty current project keeps its identity, metadata, settings and location.")
        }
        RowLayout {
            Layout.fillWidth: true
            EaElements.Button {
                objectName: "nativeImport.addFiles"; text: qsTr("Choose input files…")
                enabled: !dialog.busy && !dialog.assistant.showingActions
                onClicked: dialog.filesRequested()
            }
            EaElements.Button {
                objectName: "nativeImport.apply"; text: dialog.busy ? qsTr("Importing…") : qsTr("Apply import")
                enabled: dialog.editable
                onClicked: dialog.apply()
            }
        }
        TabBar {
            id: sections
            Layout.fillWidth: true
            enabled: dialog.editable
            onCurrentIndexChanged: dialog.selectRowSection()
            TabButton { objectName: "nativeImport.tab.inputs"; text: qsTr("Inputs") }
            TabButton { objectName: "nativeImport.tab.instrument"; text: qsTr("Instrument") }
            TabButton { objectName: "nativeImport.tab.background"; text: qsTr("Background") }
            TabButton { objectName: "nativeImport.tab.exclusions"; text: qsTr("Exclusions") }
            TabButton { objectName: "nativeImport.tab.parameters"; text: qsTr("Initial values") }
        }
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: Math.min(sections.currentIndex, 2)
            enabled: dialog.editable
            GridLayout {
                columns: 2
                EaElements.Label { text: qsTr("Structure CIF") }
                EaElements.ComboBox { id: cif; objectName: "nativeImport.cif"; Layout.fillWidth: true; model: dialog.assistant.selectedFiles; textRole: "name"; currentIndex: -1 }
                EaElements.Label { text: qsTr("Measurement XY / XYE") }
                EaElements.ComboBox { id: measurement; objectName: "nativeImport.measurement"; Layout.fillWidth: true; model: dialog.assistant.selectedFiles; textRole: "name"; currentIndex: -1 }
                EaElements.Label { text: qsTr("Project name") }
                DraftField { id: projectName; objectName: "nativeImport.projectName" }
                EaElements.Label { text: qsTr("Experiment name") }
                DraftField { id: experimentName; objectName: "nativeImport.experimentName" }
                EaElements.Label { text: qsTr("Description") }
                TextArea {
                    id: description; objectName: "nativeImport.description"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    wrapMode: TextEdit.Wrap
                    property string originalAssistantText: ""
                    property bool assistantEditing: false
                    readonly property string editText: text
                    readonly property bool assistantManualDraft: false
                    Keys.onTabPressed: event => { insert(cursorPosition, "\t"); event.accepted = true; }
                    function beginAssistantEdit() { originalAssistantText = text; assistantEditing = true; }
                    function allowAssistantCommit() { assistantEditing = false; originalAssistantText = ""; }
                    function cancelAssistantEdit() {
                        if (!assistantEditing) return;
                        text = originalAssistantText;
                        assistantEditing = false;
                        originalAssistantText = "";
                    }
                }
            }
            GridLayout {
                columns: 2
                EaElements.Label { text: qsTr("Peak profile") }
                EaElements.ComboBox { id: profile; objectName: "nativeImport.profile"; Layout.fillWidth: true; currentIndex: -1 }
                EaElements.Label { text: qsTr("Wavelength (Å)") }
                DraftField { id: wavelength; objectName: "nativeImport.wavelength" }
                EaElements.Label { text: qsTr("Two-theta zero offset") }
                DraftField { id: zero; objectName: "nativeImport.zero" }
                EaElements.Label { text: qsTr("Phase scale") }
                DraftField { id: scale; objectName: "nativeImport.scale" }
                Item { Layout.fillHeight: true }
            }
            ColumnLayout {
                RowLayout {
                    Layout.fillWidth: true
                    ComboBox {
                        id: rowSelector; objectName: "nativeImport.row"
                        Layout.fillWidth: true
                        model: dialog.rowModel.count
                        displayText: currentIndex < 0 ? qsTr("No rows") : qsTr("Row %1").arg(currentIndex + 1)
                        onCurrentIndexChanged: dialog.loadRow()
                    }
                    EaElements.Button {
                        objectName: "nativeImport.row.add"; text: qsTr("Add row")
                        enabled: dialog.rowModel.count < 256
                        onClicked: dialog.appendRow()
                    }
                    EaElements.Button {
                        text: qsTr("Remove")
                        enabled: rowSelector.currentIndex >= 0
                        onClicked: dialog.removeRow()
                    }
                }
                EaElements.Label { text: sections.currentIndex === 2 ? qsTr("Position / intensity; at least two increasing background anchors") : sections.currentIndex === 3 ? qsTr("Excluded interval first / second") : qsTr("Exact parameter path / initial value") }
                RowLayout {
                    Layout.fillWidth: true
                    DraftField { id: first; objectName: "nativeImport.row.first"; onTextChanged: dialog.rowText(true, text) }
                    DraftField { id: second; objectName: "nativeImport.row.second"; onTextChanged: dialog.rowText(false, text) }
                }
                Item { Layout.fillHeight: true }
            }
        }
        EaElements.Label {
            objectName: "nativeImport.status"
            Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText
            text: dialog.localError || dialog.outcome.message || ""
        }
    }
}
