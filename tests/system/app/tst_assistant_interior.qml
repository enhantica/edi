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
        const body = Ui.itemsWithProperty(row, "readOnly").find(control => control.visible && control.text === text);
        verify(body !== undefined, "I16/INT1: complete original body remains visible in the actual delegate");
        compare(body.textFormat, TextEdit.PlainText, "I16/INT1: technical markup stays literal PlainText");
        compare(body.readOnly, true, "I16/INT1: transcript body remains read-only");
        compare(body.selectByMouse, true, "I16/INT1: transcript body remains selectable");
        body.select(5, 17);
        compare(body.selectedText, text.slice(5, 17), "I16/INT1: nontrivial selection preserves exact original characters");
        if (data.author) {
            const semantics = accessibleText(row);
            verify(data.author.test(semantics), "I16/INT1: actual accessible names/descriptions distinguish human and assistant authors");
            verify(semantics.includes(text), "I16/INT1: complete body remains in the accessible semantic content");
        } else {
            verify(Ui.text(row).includes("Activity"), "I16/INT1: existing Activity author-label control remains visibly identified");
        }
    }
}
