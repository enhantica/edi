import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Style as EaStyle
import edi.app
import "../../unit/app/UiInteraction.js" as Ui

// Actual presentation delegate with independently supplied literal row data.
// This does not stand in for a genuinely admitted Session transcript or fit.
TestCase {
    name: "AssistantInterior"
    when: windowShown
    property var window
    Component {
        id: application
        ApplicationWindow {
            width: 720
            height: 480
            visible: true
        }
    }
    Component {
        id: message
        AssistantMessage {
            width: 600
            height: implicitHeight
        }
    }
    Component { id: textMeasure; TextMetrics {} }
    Component { id: composer; AssistantComposer { height: implicitHeight } }
    Component { id: toggle; ToolButton { text: "Assistant" } }
    function initTestCase() {
        window = application.createObject(null);
        verify(window !== null, "I16/INT1: actual Qt window owns the production message delegate");
    }
    function cleanupTestCase() {
        window.destroy();
    }
    function accessibleText(root) {
        if (!root || !root.visible)
            return "";
        let result = String(root.Accessible.name || "") + " " + String(root.Accessible.description || "");
        for (const child of root.children || [])
            result += " " + accessibleText(child);
        return result;
    }
    function renderedRow(row) {
        verify(waitForPolish(window), "ACT1: the actual command row completes layout");
        window.update();
        verify(waitForRendering(window.contentItem), "ACT1: the actual command row renders before input or observation");
    }
    function commandDisclosure(row) {
        const controls = Ui.itemsWithProperty(row, "checkable").filter(control => control.visible && control.checkable && Ui.exposed(control));
        verify(controls.length > 0, "ACT1: retained commands have a real reachable disclosure control");
        return controls[0];
    }
    function literalCommandDetails(row, original) {
        const editors = Ui.itemsWithProperty(row, "readOnly").filter(control => control.visible && control.text.includes(original.command));
        verify(editors.length > 0, "ACT1: expanded actual command remains a complete selectable literal");
        for (const value of [original.command, original.cwd, original.aggregatedOutput]) {
            const editor = Ui.itemsWithProperty(row, "readOnly").find(control => control.visible && control.text.includes(value));
            verify(editor !== undefined, "ACT1: expansion retains complete original command, working directory and admitted output");
            compare(editor.textFormat, TextEdit.PlainText, "ACT1: command details never interpret untrusted markup");
            compare(editor.readOnly, true, "ACT1: retained command details remain read-only");
            compare(editor.selectByMouse, true, "ACT1: retained command details remain selectable");
            const start = editor.text.indexOf(value);
            editor.select(start, start + value.length);
            compare(editor.selectedText, value, "ACT1: actual selected details preserve every original character");
        }
    }
    function revealTechnicalDetails(row) {
        const controls = Ui.itemsWithProperty(row, "checkable").filter(control => control.visible && control.checkable && /technical|inspect details/i.test(control.text));
        verify(controls.length > 0, "GUI92: original event JSON retains a real secondary disclosure");
        if (!controls[0].checked)
            mouseClick(controls[0]);
        renderedRow(row);
    }
    function commandItem(status, exitCode) {
        return {
            id: "original-command",
            type: "commandExecution",
            command: "python -c 'print(\"<b>literal</b>\")'",
            cwd: "/owned/work copy/測定",
            status: status,
            commandActions: [],
            aggregatedOutput: "original <b>not HTML</b>\ncomplete output — 第二行",
            exitCode: exitCode,
            diagnosticMarker: "SECONDARY_TECHNICAL_ORIGINAL"
        };
    }
    function compareRetainedPayload(actual, expected) {
        // Public payloads are JSON values. QVariantList is an array in that
        // domain even though the Qt proxy is not a JavaScript Array object.
        comparePayloadValue(JSON.parse(JSON.stringify(actual)), expected);
    }
    function comparePayloadValue(actual, expected) {
        compare(typeof actual, typeof expected, "ACT1: retained payload preserves every value type");
        compare(actual === null, expected === null, "ACT1: retained payload preserves null distinctly");
        if (expected === null)
            return;
        compare(Array.isArray(actual), Array.isArray(expected), "ACT1: retained payload preserves object versus array shape");
        if (Array.isArray(expected)) {
            compare(actual.length, expected.length, "ACT1: retained payload preserves every array entry");
            for (let index = 0; index < expected.length; ++index)
                comparePayloadValue(actual[index], expected[index]);
        } else if (typeof expected === "object") {
            const keys = Object.keys(actual).sort();
            const expectedKeys = Object.keys(expected).sort();
            compare(JSON.stringify(keys), JSON.stringify(expectedKeys), "ACT1: retained payload preserves all known and unknown keys independent of map ordering");
            for (const key of expectedKeys)
                comparePayloadValue(actual[key], expected[key]);
        } else {
            compare(actual, expected, "ACT1: retained payload preserves exact scalar and string values");
        }
    }
    function captionGeometry(control) {
        const label = Ui.itemsWithProperty(control, "elide").find(item => item.visible && item.text === control.text);
        verify(label !== undefined, "GEO1 SETUP: a real visible caption text item is measurable");
        verify(typeof label.truncated === "boolean", "GEO1 SETUP: the actual Qt text exposes its truncation state");
        const metrics = createTemporaryObject(textMeasure, window.contentItem, {font: label.font, text: label.text});
        verify(metrics !== null && metrics.advanceWidth > 0, "GEO1 SETUP: independent metrics measure the actual caption font/text");
        const point = label.mapToItem(control, 0, 0);
        const facts = {text: label.text, font: label.font.family, fontPixels: label.font.pixelSize,
            naturalWidth: metrics.advanceWidth, captionWidth: label.width, contentWidth: label.contentWidth,
            truncated: label.truncated, buttonWidth: control.width, captionX: point.x};
        console.info("DISCLOSURE_GEOMETRY", JSON.stringify(facts));
        return facts;
    }
    function test_disclosure_uses_available_caption_width_data() {
        return [{tag: "command", category: "command"}, {tag: "read", category: "read"},
            {tag: "technical", category: "technical"}];
    }
    function test_disclosure_uses_available_caption_width(data) {
        const original = commandItem("completed", 0);
        if (data.category === "read")
            original.commandActions = [{type: "read", path: "/owned/original.dat", name: "original.dat", command: original.command}];
        const row = createTemporaryObject(message, window.contentItem, {
            kind: data.category === "technical" ? "event" : "activity",
            text: "Original literal details", status: "completed", payload: original
        });
        verify(row !== null, "GEO1: the actual retained row is constructed");
        const scale = EaStyle.Sizes.defaultScale;
        try {
            for (const fontScale of [scale, Math.round(scale * 1.25)]) {
                EaStyle.Sizes.defaultScale = fontScale;
                row.width = 600;
                renderedRow(row);
                const control = data.category === "technical"
                    ? Ui.itemsWithProperty(row, "checkable").find(item => item.visible && /technical/i.test(item.text))
                    : commandDisclosure(row);
                verify(control !== undefined && Ui.exposed(control), "GEO1: the real disclosure is reachable");
                let facts = captionGeometry(control);
                verify(row.width > facts.naturalWidth * 2, "GEO1 SETUP: the wide parent genuinely has room for the complete caption");
                verify(!facts.truncated && facts.captionWidth + 1 >= facts.naturalWidth,
                    "GEO1: ample panel space must show the complete activity or technical caption");
                verify(facts.captionX >= 0 && facts.captionX + facts.captionWidth <= facts.buttonWidth + 1,
                    "GEO1: complete caption remains inside its real clickable disclosure");
                row.width = Math.max(32, facts.naturalWidth * 0.65);
                renderedRow(row);
                facts = captionGeometry(control);
                verify(facts.captionWidth < facts.naturalWidth, "GEO1 SETUP: the narrow parent actually constrains the caption");
                verify(facts.truncated, "GEO1: genuine narrow space uses bounded text elision rather than overflow");
                row.width = 600;
                renderedRow(row);
                facts = captionGeometry(control);
                verify(!facts.truncated && facts.captionWidth + 1 >= facts.naturalWidth,
                    "GEO1: widening restores the original complete caption");
                if (data.category === "technical") {
                    mouseClick(control);
                    renderedRow(row);
                    facts = captionGeometry(control);
                    verify(!facts.truncated && facts.captionWidth + 1 >= facts.naturalWidth,
                        "GEO1: expanded technical disclosure also shows its full changed caption");
                    mouseClick(control);
                }
            }
        } finally {
            EaStyle.Sizes.defaultScale = scale;
        }
        compareRetainedPayload(row.payload, original);
    }
    function textInk(item) {
        const metrics = createTemporaryObject(textMeasure, window.contentItem, {font: item.font, text: item.text});
        verify(metrics !== null && metrics.boundingRect.width > 0, "GEO2 SETUP: actual visible text/glyph has measurable ink");
        const point = item.mapToItem(window.contentItem, 0, 0);
        let offset = 0;
        if (item.horizontalAlignment === Text.AlignHCenter)
            offset = (item.width - item.contentWidth) / 2;
        else if (item.horizontalAlignment === Text.AlignRight)
            offset = item.width - item.contentWidth;
        return {left: point.x + offset + metrics.boundingRect.x,
            right: point.x + offset + metrics.boundingRect.x + metrics.boundingRect.width, y: point.y};
    }
    function test_real_selected_file_remove_pairs_with_own_label() {
        const assistant = Session.assistant;
        compare(assistant.selectedFiles.count, 0, "GEO2 SETUP: the owned real Session starts with no selected files");
        const request = assistant.beginFileSelection();
        verify(request.length > 0, "GEO2 SETUP: real native selection authority is admitted without an account action");
        const admitted = assistant.addSelectedFiles(request, [Qt.resolvedUrl("../../fixtures/assistant/README.md"),
            Qt.resolvedUrl("../../fixtures/assistant/provider-contracts.json")]);
        verify(admitted, "GEO2 SETUP: original harmless fixture URLs enter the real selected-file model");
        const ids = [];
        try {
            compare(assistant.selectedFiles.count, 2, "GEO2: both original selections are retained");
            for (let index = 0; index < assistant.selectedFiles.count; ++index)
                ids.push(assistant.selectedFiles.text(index, "id"));
            const opener = createTemporaryObject(toggle, window.contentItem);
            const actual = createTemporaryObject(composer, window.contentItem,
                {assistant: assistant, toggleControl: opener, width: 680, y: 40});
            verify(actual !== null, "GEO2: actual Composer renders the real selected-file model");
            renderedRow(actual);
            const labels = [];
            const removers = [];
            for (let index = 0; index < ids.length; ++index) {
                const group = Ui.find(actual, "assistant.file." + ids[index]);
                verify(group !== null, "GEO2: every real selected ID has its own visible chip group");
                const name = assistant.selectedFiles.text(index, "name");
                const label = Ui.itemsWithProperty(group, "elide").find(item => item.visible && item.text.startsWith(name));
                const remove = Ui.itemsWithProperty(group, "fontIcon").find(item => item.visible && item.fontIcon === "times");
                verify(label !== undefined && remove !== undefined && Ui.exposed(remove), "GEO2: original filename and its real remove action are visible together");
                verify(remove.Accessible.name.includes(name), "GEO2: remove action identifies its own original file");
                verify(!label.truncated, "GEO2 SETUP: both original short names fit before comparing visible group spacing");
                labels.push(label);
                removers.push(remove);
            }
            const glyph = Ui.itemsWithProperty(removers[0].contentItem, "contentWidth").find(item => item.visible && typeof item.text === "string" && item.text.length > 0);
            verify(glyph !== undefined, "GEO2 SETUP: actual remove glyph text bounds are observable");
            const first = textInk(labels[0]);
            const cross = textInk(glyph);
            const next = textInk(labels[1]);
            verify(Math.abs(first.y - next.y) < labels[0].height, "GEO2 SETUP: the two original chip groups genuinely share a rendered line");
            const inside = cross.left - first.right;
            const between = next.left - cross.right;
            console.info("FILE_PAIR_GEOMETRY", JSON.stringify({first: first, cross: cross, next: next, inside: inside, between: between}));
            verify(inside >= 0 && between > inside, "GEO2: visible remove cross is closer to its own label than the next file group");
            mouseClick(removers[0]);
            renderedRow(actual);
            compare(assistant.selectedFiles.count, 1, "GEO2: real pointer removal retires exactly one selection");
            compare(assistant.selectedFiles.text(0, "id"), ids[1], "GEO2: removing the first paired action preserves the other original file");
        } finally {
            for (const id of ids)
                assistant.removeSelectedFile(id);
        }
    }
    function test_command_activity_is_compact_and_discloses_originals_data() {
        return [
            {tag: "running", status: "inProgress", exitCode: null, summary: /running/i},
            {tag: "completed", status: "completed", exitCode: 0, summary: /ran/i},
            {tag: "failed", status: "failed", exitCode: 7, summary: /ran|fail/i}
        ];
    }
    function test_command_activity_is_compact_and_discloses_originals(data) {
        const original = commandItem(data.status, data.exitCode);
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command,
            status: data.status === "inProgress" ? "in_progress" : data.status,
            payload: original
        });
        verify(row !== null, "ACT1: actual production delegate accepts retained command activity");
        renderedRow(row);
        const collapsed = Ui.text(row);
        verify(data.summary.test(collapsed), "ACT1: collapsed command summary truthfully distinguishes running from settled work");
        verify(!collapsed.includes(original.aggregatedOutput) && !collapsed.includes(original.cwd), "ACT1: complete command details start collapsed rather than flooding normal transcript rows");
        verify(!collapsed.includes(original.diagnosticMarker), "ACT1: raw event JSON starts behind secondary technical disclosure");
        if (data.status === "failed")
            verify(/fail|error/i.test(collapsed), "GUI92: compact summaries cannot hide an actual failed command outcome");
        const disclosure = commandDisclosure(row);
        compare(disclosure.checked, false, "ACT1: original command disclosure starts closed");
        mouseClick(disclosure);
        renderedRow(row);
        literalCommandDetails(row, original);
        verify(!Ui.text(row).includes(original.diagnosticMarker), "ACT1: primary disclosure shows human-readable originals before raw technical JSON");
        compareRetainedPayload(row.payload, original);
        // Owner d9ec58479 moves technical metadata out of the default caption.
        // Preserve exact typed exit evidence and exercise its actual disclosure.
        if (data.exitCode !== null) {
            compare(typeof row.payload.exitCode, "number", "GUI92: original exit metadata keeps its numeric type");
            compare(row.payload.exitCode, data.exitCode, "GUI92: original exit code is unchanged");
            revealTechnicalDetails(row);
            verify(new RegExp('"exitCode"\\s*:\\s*' + data.exitCode + '(?:\\s|[,}])').test(Ui.text(row)), "GUI92: actual exit code remains reachable in literal technical details");
        }
        mouseClick(disclosure);
        renderedRow(row);
        compare(disclosure.checked, false, "ACT1: real disclosure can collapse again");
        verify(!Ui.text(row).includes(original.aggregatedOutput), "ACT1: collapsed output no longer occupies the visible command row");
    }
    function test_command_same_identity_updates_and_reused_row_retires_expansion() {
        const original = commandItem("inProgress", null);
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: "in_progress", payload: original
        });
        verify(row !== null, "ACT1: actual command reuse control is constructed");
        renderedRow(row);
        mouseClick(commandDisclosure(row));
        renderedRow(row);
        const completed = Object.assign({}, original, {status: "completed", exitCode: 0, aggregatedOutput: original.aggregatedOutput + "\nfinal original tail"});
        row.payload = completed;
        row.status = "completed";
        renderedRow(row);
        compare(commandDisclosure(row).checked, true, "ACT1: same admitted command updates preserve the reader's explicit expansion");
        literalCommandDetails(row, completed);
        const replacement = Object.assign({}, original, {id: "different-command", command: "python -c 'print(2)'", aggregatedOutput: "new original output"});
        row.payload = replacement;
        row.text = replacement.command;
        row.status = "in_progress";
        renderedRow(row);
        compare(commandDisclosure(row).checked, false, "ACT1: reusing a delegate for a different command retires the old expansion");
        verify(!Ui.text(row).includes(completed.aggregatedOutput), "ACT1: replacement command cannot reveal prior retained output");
    }
    function test_public_command_retirement_overrides_unfinished_original_data() {
        return [
            {tag: "interrupted", status: "interrupted", summary: /interrupt|stopp|cancel/i},
            {tag: "failed", status: "failed", summary: /fail|error/i}
        ];
    }
    function test_public_command_retirement_overrides_unfinished_original(data) {
        const original = commandItem("inProgress", null);
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: "in_progress", payload: original
        });
        verify(row !== null, "ACT1: real unfinished original exists before public retirement");
        renderedRow(row);
        verify(/running/i.test(Ui.text(row)), "ACT1: real live public row supplies the positive running control");
        row.status = data.status;
        renderedRow(row);
        verify(data.summary.test(Ui.text(row)) && !/running/i.test(Ui.text(row)), "ACT1: public interruption/failure cannot remain Running because original command evidence is unfinished");
        compareRetainedPayload(row.payload, original);
        mouseClick(commandDisclosure(row));
        renderedRow(row);
        literalCommandDetails(row, original);
        row.destroy();
        // Reconstructed literal row is a presentation control for the archive
        // shape, not a claim of a real Session archive/reload integration run.
        const restored = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: data.status, payload: original
        });
        verify(restored !== null, "ACT1: retained public status and original payload can be reconstructed");
        renderedRow(restored);
        verify(data.summary.test(Ui.text(restored)) && !/running/i.test(Ui.text(restored)), "ACT1: reload-equivalent presentation keeps actual retirement visible without rewriting original evidence");
        compareRetainedPayload(restored.payload, original);
    }
    function test_supported_activity_kinds_share_compact_literal_disclosure_data() {
        // Independent original shapes: retained public 0.162.1 ThreadItem union.
        return [
            {tag: "files", original: {id: "files-original", type: "fileChange", status: "completed", changes: []}, summary: /chang|file|patch/i},
            {tag: "mcp-failure", original: {id: "mcp-original", type: "mcpToolCall", status: "failed", server: "owned", tool: "original", arguments: {}}, summary: /fail|error/i},
            {tag: "dynamic", original: {id: "dynamic-original", type: "dynamicToolCall", status: "completed", tool: "original", arguments: {}, success: true, contentItems: []}, summary: /tool|call|ran|complet/i},
            {tag: "collaboration", original: {id: "collab-original", type: "collabAgentToolCall", status: "interrupted", senderThreadId: "original-sender", receiverThreadIds: [], agentsStates: {}, tool: "spawnAgent"}, summary: /interrupt|stopp|cancel/i},
            {tag: "web", original: {id: "web-original", type: "webSearch", query: "Original explicit search", action: {type: "search", query: "Original explicit search"}}, summary: /web|search/i},
            {tag: "plan", original: {id: "plan-original", type: "plan", text: "Original proposed steps"}, summary: /plan/i},
            {tag: "unknown", original: {id: "unknown-original", type: "futureOwnedActivity", original: "opaque original data"}, summary: /activity|event|unknown/i}
        ];
    }
    function test_supported_activity_kinds_share_compact_literal_disclosure(data) {
        const original = Object.assign({}, data.original, {diagnosticMarker: "ORIGINAL_SECONDARY_測定"});
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: "Original literal activity body", status: original.status || "completed", payload: original
        });
        verify(row !== null, "GUI92: actual production delegate presents the independently supplied activity kind");
        renderedRow(row);
        const summary = Ui.text(row);
        verify(data.summary.test(summary), "GUI92: human activity summary preserves actual category and failed/interrupted truth");
        verify(!summary.includes(original.diagnosticMarker), "GUI92: every activity kind starts with technical originals collapsed");
        verify(accessibleText(row).trim().length > 0, "GUI92: compact activity keeps a discoverable accessible summary");
        const disclosure = commandDisclosure(row);
        compare(disclosure.checked, false, "GUI92: actual activity disclosure begins closed");
        mouseClick(disclosure);
        renderedRow(row);
        if (!Ui.text(row).includes(original.diagnosticMarker))
            revealTechnicalDetails(row);
        verify(Ui.text(row).includes(original.diagnosticMarker), "GUI92: every supported or unknown activity retains complete inspectable original metadata");
        const details = Ui.itemsWithProperty(row, "readOnly").filter(control => control.visible && control.text.includes(original.diagnosticMarker));
        verify(details.length > 0, "GUI92: actual original metadata remains in a real selectable text field");
        compare(details[0].textFormat, TextEdit.PlainText, "GUI92: technical activity details stay literal rather than executable markup");
        compare(details[0].readOnly, true, "GUI92: retained activity details cannot be edited");
        compare(details[0].selectByMouse, true, "GUI92: retained activity details are selectable");
        compareRetainedPayload(row.payload, original);
    }
    function test_activity_categories_require_structured_evidence_data() {
        return [{tag: "explicit-read", structured: true}, {tag: "shell-words", structured: false}];
    }
    function test_activity_categories_require_structured_evidence(data) {
        const original = commandItem("completed", 0);
        original.command = "printf 'cat read files search web curl'";
        original.commandActions = data.structured ? [{type: "read", command: original.command, name: "original.cif", path: "/owned/original.cif"}] : [];
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: "completed", payload: original
        });
        verify(row !== null, "GUI92: structured-action and shell-word controls use the same actual delegate");
        renderedRow(row);
        const summary = commandDisclosure(row).text;
        if (data.structured)
            verify(/read/i.test(summary), "GUI92: explicit original read action can supply a truthful human category");
        else {
            verify(/command|ran/i.test(summary), "GUI92: a command without structured actions stays a command");
            verify(!/read.*file|search.*web|web.*search/i.test(summary), "GUI92: shell substrings alone cannot invent file-read or web-search actions");
        }
        compareRetainedPayload(row.payload, original);
    }
    function test_activity_description_uses_original_structured_source_data() {
        // Original pinned CommandAction read(name/path), listFiles(path), search(query/path), unknown.
        // These literal UI fixtures do not claim an actual shell execution or admitted Session transcript.
        return [
            {tag: "read-name", action: {type: "read", name: "SKILL.md", path: "/owned/.agents/skills/project-assistance/SKILL.md"},
                command: "sed -n '1,40p' /owned/.agents/skills/project-assistance/SKILL.md", expected: "Read assistant workflow instructions", category: /read/i},
            {tag: "list-path", action: {type: "listFiles", path: "/owned/original-series"}, category: /list/i},
            {tag: "search-query", action: {type: "search", query: "peak position", path: null}, category: /search/i},
            {tag: "opaque-command", action: {type: "unknown"},
                command: "cat /owned/.agents/skills/project-assistance/SKILL.md /owned/input.edi", category: /^(?:run|execute)(?:\s+an?)?\s+(?:(?:shell\s+)?command|operation)$/i},
            {tag: "explicit-purpose", action: {type: "read", name: "original.cif", path: "/owned/original.cif"},
                purpose: "Inspect profile inputs", description: "A lower-priority conflicting description", expected: "Inspect profile inputs", category: /read/i},
            {tag: "explicit-description", action: {type: "search", query: "peak position", path: null},
                description: "Locate lattice setting", expected: "Locate lattice setting", category: /search/i}
        ];
    }
    function test_activity_description_uses_original_structured_source(data) {
        const original = commandItem("completed", 0);
        original.command = data.command !== undefined ? data.command : "printf 'read files search web scientific fit succeeded'";
        original.commandActions = [Object.assign({command: original.command}, data.action)];
        if (data.purpose !== undefined) original.purpose = data.purpose;
        if (data.description !== undefined) original.description = data.description;
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: "completed", payload: original
        });
        verify(row !== null, "DESC1: actual activity presents independent original structured metadata");
        renderedRow(row);
        const control = commandDisclosure(row), summary = control.text;
        verify(typeof summary === "string" && summary.trim().length>0 && !/[\r\n]/.test(summary),
            "GUI477: actual collapsed activity has a nonempty short single-line HUMAN purpose");
        if (data.expected !== undefined) compare(summary,data.expected,
            "GUI477: independent declared purpose wins over description/action; known workflow read has exact human purpose");
        if (data.purpose === undefined && data.description === undefined)
            verify(data.category.test(summary),"GUI477: absent semantic intent keeps truthful structured action/unknown verb category");
        for (const raw of [original.command,"printf", "sed -n", "cat ", "scientific fit succeeded"])
            verify(!summary.includes(raw),"GUI477: collapsed human purpose NEVER exposes raw command prefix or fabricates a scientific outcome");
        if (data.tag === "opaque-command") verify(!/read.*file|search.*web|web.*search/i.test(summary),
            "DESC1: unknown opaque shell words cannot invent file-read or web-search purpose");
        const details478 = Ui.itemsWithProperty(row,"objectName").filter(item => item.objectName === "assistant.command.details");
        compare(details478.length,1,"GUI478: SAME original command owns ONE native details viewport");
        verify(!control.checked && !details478[0].visible && !Ui.rendered(details478[0]),
            "GUI478: collapsed original command details have NO visible native exposure");
        // Text/Label/TextEdit paint; a Rectangle/Column retaining a text role does not.
        const painted478 = Ui.itemsWithProperty(row,"textFormat").filter(item =>
            typeof item.text === "string" && item.font !== undefined && item.visible && Ui.rendered(item));
        verify(painted478.some(item => item.text === summary),
            "GUI478: actual human header is present in a rendered native text control");
        for (const raw of [original.command,original.aggregatedOutput])
            verify(painted478.every(item => !item.text.includes(raw)),
                "GUI478: NO actually painted collapsed header/text control exposes retained literal command/output");
        mouseClick(control);
        renderedRow(row);
        literalCommandDetails(row, original);
        compareRetainedPayload(row.payload, original);
        if (data.tag === "read-name") {
            const unrelated=commandItem("completed",0);
            unrelated.command="cat /owned/unrelated/SKILL.md";
            unrelated.commandActions=[{type:"read",name:"SKILL.md",path:"/owned/unrelated/SKILL.md",command:unrelated.command}];
            const other=createTemporaryObject(message,window.contentItem,{
                kind:"activity",text:unrelated.command,status:"completed",payload:unrelated});
            verify(other!==null,"GUI477: same basename outside known public workflow uses SAME real native delegate");
            renderedRow(other);
            const generic=commandDisclosure(other).text;
            verify(generic!==data.expected && /read/i.test(generic) && !generic.includes("cat "),
                "GUI477: arbitrary SKILL.md basename cannot invent project-assistance workflow identity/purpose");
            compareRetainedPayload(other.payload,unrelated);
        }
    }
    function hasCompleteUnicodeScalars(text) {
        for (let index = 0; index < text.length; ++index) {
            const unit = text.charCodeAt(index);
            if (unit >= 0xD800 && unit <= 0xDBFF) {
                const next = text.charCodeAt(++index);
                if (!(next >= 0xDC00 && next <= 0xDFFF)) return false;
            } else if (unit >= 0xDC00 && unit <= 0xDFFF) return false;
        }
        return true;
    }
    function selectOriginalTechnicalPayload(row, original) {
        revealTechnicalDetails(row);
        const editor = Ui.itemsWithProperty(row, "readOnly").find(item => item.visible && item.text.includes(original.diagnosticMarker));
        verify(editor !== undefined, "CAP: complete canonical originals remain in reachable literal technical details");
        compare(editor.textFormat, TextEdit.PlainText, "CAP: original metadata is displayed as literal text");
        compareRetainedPayload(JSON.parse(editor.text), original);
        editor.selectAll();
        compare(editor.selectedText, editor.text, "CAP: complete original metadata remains selectable without excerpt loss");
    }
    function test_activity_excerpt_keeps_complete_unicode_scalars_data() {
        return [{tag: "read-name", kind: "commandExecution"}, {tag: "tool-name", kind: "mcpToolCall"}];
    }
    function test_activity_excerpt_keeps_complete_unicode_scalars(data) {
        const value = "A".repeat(39) + "\uD83E\uDDEA" + " original.cif";
        verify(hasCompleteUnicodeScalars(value), "CAP1 SETUP: the original supplementary scalar is well formed before presentation");
        const original = data.kind === "commandExecution" ? commandItem("completed", 0)
            : {id: "unicode-tool", type: "mcpToolCall", server: "owned", tool: value, arguments: {}, status: "completed"};
        if (data.kind === "commandExecution")
            original.commandActions = [{type: "read", command: original.command, name: value, path: "/owned/" + value}];
        // Explicit purpose keeps this an actual excerpt boundary after owner115
        // removes tool/name/object fallback descriptions.
        original.purpose = value;
        original.diagnosticMarker = "CAP1_COMPLETE_ORIGINAL";
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: "Original Unicode activity", status: "completed", payload: original
        });
        verify(row !== null, "CAP1: actual shared activity presentation accepts the original scalar-boundary metadata");
        renderedRow(row);
        const control = commandDisclosure(row);
        verify(control.text.includes("·"), "CAP1: the actual scalar-boundary input reaches a described activity caption");
        const labels = Ui.itemsWithProperty(control, "elide").filter(item => item.visible && item.text === control.text);
        verify(labels.length > 0, "CAP1: actual excerpt is present in a rendered caption text item");
        for (const text of [control.text, labels[0].text]) {
            verify(hasCompleteUnicodeScalars(text), "CAP1: visible excerpts never split a supplementary Unicode scalar");
            verify(!text.includes("\uFFFD"), "CAP1: clipping valid originals must not introduce a replacement glyph");
        }
        mouseClick(control);
        renderedRow(row);
        selectOriginalTechnicalPayload(row, original);
        compareRetainedPayload(row.payload, original);
    }
    function test_malformed_action_arrays_remain_opaque_data() {
        return [{tag: "nulls", actions: [null, null]},
            {tag: "missing-types", actions: [{name: "original.cif"}, {path: "/owned/original"}]},
            {tag: "primitives", actions: [7, "read"]}];
    }
    function test_malformed_action_arrays_remain_opaque(data) {
        const original = commandItem("completed", 0);
        original.commandActions = data.actions;
        original.diagnosticMarker = "CAP2_COMPLETE_ORIGINAL";
        const row = createTemporaryObject(message, window.contentItem, {
            kind: "activity", text: original.command, status: "completed", payload: original
        });
        verify(row !== null, "CAP2: actual delegate accepts retained opaque JSON action metadata");
        renderedRow(row);
        const control = commandDisclosure(row);
        verify(typeof control.text === "string" && control.text.length > 0,
            "CAP2: malformed action entries keep a usable caption rather than a script failure");
        verify(/command|ran/i.test(control.text.split("·")[0]),
            "CAP2: untyped entries retain the conservative command category");
        verify(!/combined|multiple|several|\b[2-9]\s+(?:actions?|commands?|steps?)\b/i.test(control.text),
            "CAP2: raw invalid array length cannot invent a combined-action description");
        mouseClick(control);
        renderedRow(row);
        literalCommandDetails(row, original);
        selectOriginalTechnicalPayload(row, original);
        compareRetainedPayload(row.payload, original);
    }
    function test_literal_rows_keep_author_information_data() {
        return [
            {
                tag: "human",
                kind: "user",
                author: /\b(you|user)\b/i
            },
            {
                tag: "assistant",
                kind: "assistant",
                author: /\bassistant\b/i
            },
            {
                tag: "activity-control",
                kind: "event",
                author: null
            }
        ];
    }
    function test_literal_rows_keep_author_information(data) {
        const text = "cell = 5.43 Å <b>literal</b>\n第二行 — selectable technical text\n" + "long line 1234567890 ".repeat(12);
        const row = createTemporaryObject(message, window.contentItem, {
            kind: data.kind,
            text: text
        });
        verify(row !== null, "I16/INT1: each real production delegate accepts its independently supplied kind/body");
        verify(waitForPolish(window), "I16/INT1: the actual row completes layout");
        window.update();
        verify(waitForRendering(window.contentItem), "I16/INT1: the actual literal row renders");
        const body = Ui.itemsWithProperty(row, "readOnly").find(control => control.visible && (data.kind === "assistant" || control.text === text));
        verify(body !== undefined, "I16/INT1: complete original body remains visible in the actual delegate");
        compare(row.text, text, "I16/MD: original backing row retains exact source bytes");
        if (data.kind !== "assistant")
            compare(body.textFormat, TextEdit.PlainText, "I16/INT1: user/activity technical markup stays literal PlainText");
        compare(body.readOnly, true, "I16/INT1: transcript body remains read-only");
        compare(body.selectByMouse, true, "I16/INT1: transcript body remains selectable");
        if (data.kind === "assistant") {
            const rendered = body.getText(0, body.length);
            verify(rendered.includes("cell = 5.43 Å <b>literal</b>"), "MD/INT1: actual assistant document retains original scientific literal and does not parse HTML");
            verify(rendered.includes("第二行 — selectable technical text"), "MD/INT1: actual rendered Unicode body remains complete");
            const start = rendered.indexOf("5.43");
            verify(start >= 0, "MD/INT1: original nontrivial value is present before selecting");
            body.select(start, start + 4);
            compare(body.selectedText, "5.43", "MD/INT1: rendered assistant selection preserves independently planted characters");
        } else {
            body.select(5, 17);
            compare(body.selectedText, text.slice(5, 17), "I16/INT1: nontrivial selection preserves exact original characters");
        }
        if (data.author) {
            const semantics = accessibleText(row);
            verify(data.author.test(semantics), "I16/INT1: actual accessible names/descriptions distinguish human and assistant authors");
            if (data.kind === "assistant") {
                for (const line of text.split("\n"))
                    verify(semantics.includes(line.trim()), "MD/INT1: complete original assistant content remains accessible");
            } else
                verify(semantics.includes(text), "I16/INT1: complete body remains in the accessible semantic content");
        } else {
            verify(/activity|event/i.test(accessibleText(row)), "I16/INT1: a meaningful accessible activity identity survives human-summary captions");
        }
    }
}
