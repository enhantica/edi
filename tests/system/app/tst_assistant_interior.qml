import QtQuick
import QtQuick.Controls
import QtTest
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
