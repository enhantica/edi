// Tests-only window around the actual production component and engine-owned Session.
import QtQuick
import QtQuick.Controls
import edi.app

ApplicationWindow {
    id: window
    width: 1024
    height: 768
    visible: true
    AssistantConnectionDialog {
        id: consent
        objectName: "consent-under-test"
        assistant: Session.assistant
    }
    function openConsent() { consent.open(); }
    function acceptAction() { return consent.standardButton(Dialog.Ok); }
    function cancelAction() { return consent.standardButton(Dialog.Cancel); }
    function consentState() {
        return { opened: consent.opened, visible: consent.visible, title: consent.title,
                 x: consent.x, y: consent.y, width: consent.width, height: consent.height };
    }
}
