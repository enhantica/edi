// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

import "../../feedback/Payload.js" as Payload

// Help and feedback (ADR-0063): one form for feedback, a question, a problem or an idea. It posts to the feedback service
// at `endpoint`, the feedback service by default; with the address cleared in Preferences, Send is off and a note says
// why. "Show what will be sent" shows the exact message,
// with the home folder and user name already replaced by "~".
AppDialog {
    id: dialog

    // The feedback service's address; empty until one is set up.
    property string endpoint: Preferences.feedbackEndpoint
    // transport(url, payload, completed): tests inject one; null sends over HTTPS.
    property var transport: null
    // A log to send instead of this run's: the crashed run's, from the crash popup.
    property string attachedLog: ""
    // This run's log as the form opened, so the message does not change while it is shown.
    property string logSnapshot: ""
    property bool sending: false
    // Which showing of the form this is: each opening, a new, replaced or removed attachment and each close start
    // another draft, and a request's answer acts on the form only while its own draft is still the one shown.
    property int draft: 0
    // Starts another draft: an answer still pending belongs to the one before, and the form is free to edit and send.
    function newDraft() {
        draft += 1;
        sending = false;
    }
    onAttachedLogChanged: newDraft()
    // Sent: the form gives way to one confirmation, and the window closes by itself (the owner, 2026-11-02).
    readonly property bool sent: lastStatus === 201
    // The app window's width, set by the window. Read from the popup's own parent, it made a binding loop.
    property real roomWidth: 1000
    property int lastStatus: -1

    readonly property string kind: kindBox.currentValue ?? "feedback"
    readonly property var payload: Payload.buildPayload(kind, textArea.text, includeBox.checked, includeBox.checked ? appDetails() : null, includeBox.checked ? (attachedLog !== "" ? attachedLog : logSnapshot) : "", RunLog.homePath, RunLog.userName, {
        "name": Preferences.feedbackName,
        "email": Preferences.feedbackEmail,
        "affiliation": Preferences.feedbackAffiliation
    }, subjectField.text)
    readonly property string payloadText: Payload.wireText(payload, true)

    // The app's details as a plain object, in the order the form shows them.
    function appDetails() {
        const report = RunLog.reportInfo();
        return {
            "version": report.version,
            "commit": report.commit,
            "crysta": report.crysta,
            "qt": report.qt,
            "os": report.os,
            "graphics": report.graphics
        };
    }

    // Opens the form on `kind`, with `log` attached instead of this run's when it is not empty.
    function openAs(kind, log) {
        newDraft();
        kindBox.currentIndex = Math.max(0, kindBox.indexOfValue(kind));
        attachedLog = log ?? "";
        open();
    }

    // The answer belongs to the request as it was sent: its kind and attachment, and the text and subject it carried.
    // The fields are locked while it is pending; a success clears them only on the draft that sent them.
    function send() {
        const request = {
            "draft": dialog.draft,
            "kind": dialog.kind,
            "attachedLog": dialog.attachedLog,
            "text": textArea.text,
            "subject": subjectField.text
        };
        dialog.sending = true;
        dialog.lastStatus = -1;
        const sent = Payload.submit(dialog.endpoint, dialog.payload, dialog.transport ?? Payload.httpTransport, status => {
            RunLog.note(status === 201 ? `feedback sent: ${request.kind}` : `feedback not sent: status ${status}`);
            if (status === 201 && request.attachedLog !== "" && (dialog.attachedLog === "" || dialog.attachedLog === request.attachedLog))
                RunLog.dismissCrash();
            if (dialog.draft !== request.draft)
                return;
            dialog.sending = false;
            dialog.lastStatus = status;
            if (status === 201) {
                if (textArea.text === request.text)
                    textArea.text = "";
                if (subjectField.text === request.subject)
                    subjectField.text = "";
            }
        });
        if (!sent)
            dialog.sending = false;
    }

    objectName: "feedback.form"
    title: qsTr("Help and feedback")
    // Wide enough for the privacy note to take two lines at the default font size; narrower in a narrower app window.
    contentWidth: Math.min(AppSizes.unit * 40, roomWidth - AppSizes.unit * 6)
    contentHeight: column.implicitHeight
    // The window never grows past the app's: what is left once the title, the status, the buttons and a margin around
    // the window are taken.
    readonly property real bodyRoom: Math.max(EaStyle.Sizes.fontPixelSize * 8, (parent ? parent.height : 600) - actions.height - EaStyle.Sizes.fontPixelSize * 12)
    // The body's height with the preview at its six lines. One scroll bar at most: when this fits, only the preview
    // scrolls; when it does not, the body scrolls and the preview shows all its lines.
    readonly property real compactBodyHeight: form.implicitHeight + (preview.visible ? body.spacing + preview.heightFor(6) : 0) + (unavailable.visible ? body.spacing + unavailable.implicitHeight : 0)
    readonly property bool bodyFits: compactBodyHeight <= bodyRoom + 1

    onAboutToShow: {
        newDraft();
        logSnapshot = RunLog.logText();
        lastStatus = -1;
        previewBox.shown = false;
        bodyView.contentY = 0;
    }
    onOpened: textArea.focusText()
    // Closing starts another draft as it begins (Cancel, Close, Escape or the confirmation's own close), not once the
    // exit transition has run.
    onAboutToHide: newDraft()
    onClosed: attachedLog = ""

    Column {
        id: column

        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        // The form's body, scrolling when the window is too short for it; the status and the buttons stay below it.
        Flickable {
            id: bodyView

            visible: !dialog.sent
            width: parent.width
            height: Math.min(body.implicitHeight, dialog.bodyRoom)
            contentHeight: body.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            interactive: !dialog.bodyFits
            // Shown only once the window has opened and laid out, so it never flashes while the window opens.
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: dialog.bodyFits ? ScrollBar.AlwaysOff : dialog.opened ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            }

            Column {
                id: body

                width: bodyView.width
                spacing: EaStyle.Sizes.fontPixelSize

                Column {
                    id: form

                    width: parent.width
                    spacing: EaStyle.Sizes.fontPixelSize

                    EaElements.Label {
                        objectName: "feedback.intro"
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: qsTr("We'd love to hear from you to make EasyDiffraction better.")
                    }
                    EaElements.ComboBox {
                        id: kindBox

                        objectName: "feedback.kind"
                        width: parent.width
                        enabled: !dialog.sending
                        textRole: "text"
                        valueRole: "value"
                        // A ListModel, whose roles the base's list items read; they show nothing for a list of JavaScript objects.
                        model: ListModel {
                            // General feedback, praise or complaint or both: the first entry and the default.
                            ListElement {
                                value: "feedback"
                                text: qsTr("Share feedback")
                            }
                            ListElement {
                                value: "question"
                                text: qsTr("Ask a question")
                            }
                            ListElement {
                                value: "problem"
                                text: qsTr("Report a problem")
                            }
                            ListElement {
                                value: "idea"
                                text: qsTr("Suggest an idea")
                            }
                        }
                    }
                    // Who wrote, on one row, each optional and kept for the next message; sent only when filled in.
                    Row {
                        id: contactRow

                        readonly property real fieldWidth: (width - 2 * spacing) / 3

                        width: parent.width
                        spacing: EaStyle.Sizes.fontPixelSize

                        EaElements.TextField {
                            objectName: "feedback.name"
                            width: contactRow.fieldWidth
                            horizontalAlignment: TextInput.AlignLeft
                            placeholderText: qsTr("Name (optional)")
                            text: Preferences.feedbackName
                            onTextChanged: Preferences.feedbackName = text
                        }
                        EaElements.TextField {
                            objectName: "feedback.email"
                            width: contactRow.fieldWidth
                            horizontalAlignment: TextInput.AlignLeft
                            placeholderText: qsTr("E-mail (optional)")
                            text: Preferences.feedbackEmail
                            onTextChanged: Preferences.feedbackEmail = text
                        }
                        EaElements.TextField {
                            objectName: "feedback.affiliation"
                            width: contactRow.fieldWidth
                            horizontalAlignment: TextInput.AlignLeft
                            placeholderText: qsTr("Affiliation (optional)")
                            text: Preferences.feedbackAffiliation
                            onTextChanged: Preferences.feedbackAffiliation = text
                        }
                    }
                    EaElements.TextField {
                        id: subjectField

                        objectName: "feedback.subject"
                        width: parent.width
                        enabled: !dialog.sending
                        horizontalAlignment: TextInput.AlignLeft
                        placeholderText: ({
                                "question": qsTr("Your question in a few words (optional)"),
                                "problem": qsTr("What went wrong, in a few words (optional)"),
                                "idea": qsTr("Your idea in a few words (optional)"),
                                "feedback": qsTr("Your feedback in a few words (optional)")
                            })[dialog.kind] ?? qsTr("Subject (optional)")
                    }
                    // The app's text field of several lines, five lines tall and scrolling beyond.
                    MultiLineField {
                        id: textArea

                        areaObjectName: "feedback.text"
                        width: parent.width
                        enabled: !dialog.sending
                        minimumLines: 5
                        maximumLines: 5
                        placeholderText: ({
                                "question": qsTr("What would you like to know, and what have you tried?"),
                                "problem": qsTr("What did you do, what happened, and what did you expect?"),
                                "idea": qsTr("What would you like the app to do, and how would it help?"),
                                "feedback": qsTr("What works well for you, and what could be better?")
                            })[dialog.kind] ?? ""
                    }
                    EaElements.CheckBox {
                        id: includeBox

                        objectName: "feedback.include"
                        enabled: !dialog.sending
                        // Its box in line with the fields' left edges.
                        leftPadding: 0
                        checked: true
                        text: qsTr("Include app version, system and log")
                    }
                    EaElements.Label {
                        objectName: "feedback.note"
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: EaStyle.Colors.themeForegroundMinor
                        text: (includeBox.checked ? qsTr("Your text, the app version, your system and the log of this run are sent. Your home folder and user name are replaced by ~.") : qsTr("Only your text is sent.")) + " " + qsTr("Your name, e-mail and affiliation are sent only if you fill them in.")
                    }
                    IconLink {
                        id: previewBox

                        property bool shown: false

                        objectName: "feedback.preview"
                        fontIcon: shown ? "eye-slash" : "eye"
                        text: shown ? qsTr("Hide what will be sent") : qsTr("Show what will be sent")
                        onClicked: shown = !shown
                    }
                }
                // The message as it will be sent, in the message box's field: six lines scrolling, or all of them when
                // the body scrolls instead.
                MultiLineField {
                    id: preview

                    areaObjectName: "feedback.payload"
                    width: parent.width
                    visible: previewBox.shown
                    readOnly: true
                    dimsWhenReadOnly: false
                    fontFamily: EaStyle.Fonts.monoFontFamily
                    minimumLines: 6
                    maximumLines: dialog.bodyFits ? 6 : 100000
                    text: dialog.payloadText

                    // Delayed until the form has laid out: a passing state while the preview opens left its bar
                    // fully shown for seconds.
                    Binding on scrollBarShown {
                        value: dialog.opened && dialog.bodyFits && previewBox.shown
                        delayed: true
                    }
                }
                EaElements.Label {
                    id: unavailable

                    objectName: "feedback.unavailable"
                    visible: dialog.endpoint === ""
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: qsTr("Sending is off: the feedback address in Preferences is empty.")
                }
            }
        }
        EaElements.Label {
            objectName: "feedback.status"
            visible: dialog.sending || dialog.lastStatus >= 0
            width: parent.width
            wrapMode: Text.WordWrap
            // A failed message keeps its text, to send again.
            text: dialog.sending ? qsTr("Sending...") : dialog.sent ? qsTr("Your message was sent. Thank you!") : dialog.lastStatus === 429 ? qsTr("Too many messages were sent from here recently. Please try again later.") : dialog.lastStatus === 0 ? qsTr("No connection to the feedback service. Check your connection and try again.") : qsTr("Sending failed (%1). Please try again later.").arg(dialog.lastStatus)
        }
        Row {
            id: actions

            anchors.right: parent.right
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.Button {
                objectName: "feedback.cancel"
                fontIcon: "times"
                text: dialog.sent ? qsTr("Close") : qsTr("Cancel")
                onClicked: dialog.close()
            }
            EaElements.Button {
                objectName: "feedback.send"
                fontIcon: "paper-plane"
                visible: !dialog.sent
                enabled: dialog.endpoint !== "" && textArea.text.trim() !== "" && !dialog.sending
                text: qsTr("Send")
                ToolTip.text: enabled ? "" : dialog.sending ? qsTr("Sending...") : dialog.endpoint === "" ? qsTr("No feedback address is set: add one in Preferences, Develop") : qsTr("Write your message first")
                onClicked: dialog.send()
            }
        }
    }
    // A sent message's confirmation stays about two seconds; Close closes it at once. Reopened, the form is fresh, the
    // contact fields kept.
    Timer {
        interval: 1800
        running: dialog.sent && dialog.visible
        onTriggered: dialog.close()
    }
}
