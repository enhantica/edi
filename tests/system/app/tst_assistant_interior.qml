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
            verify(Ui.text(row).includes("Activity"), "I16/INT1: existing Activity author-label control remains visibly identified");
        }
    }
}
