// Actual AssistantPanel/Composer/dialog composition, real engine-owned Session.
import QtQuick
import QtQuick.Controls
import edi.app

ApplicationWindow {
    id: window
    width: 600
    height: 1100
    visible: true
    ToolButton { id: toggle; text: "Assistant" }
    Item {
        id: sidebar
        x: 0
        y: 40
        width: 420
        height: window.height - y
        AssistantPanel {
            id: panel
            assistant: Session.assistant
            toggleControl: toggle
            shown: true
        }
    }
    function actualConsent() {
        for (const object of panel.contentItem.data)
            if (object instanceof AssistantConnectionDialog) return object;
        throw new Error("Actual panel consent dialog unavailable");
    }
    function panelState() { return { opened: panel.opened, visible: panel.visible }; }
    function openConsent() { actualConsent().open(); }
    function acceptAction() { return actualConsent().standardButton(Dialog.Ok); }
    function cancelAction() { return actualConsent().standardButton(Dialog.Cancel); }
    function consentState() {
        const dialog = actualConsent();
        return { opened: dialog.opened, visible: dialog.visible, title: dialog.title,
                 x: dialog.x, y: dialog.y, width: dialog.width, height: dialog.height };
    }
}
