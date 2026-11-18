// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// After a run that did not quit normally (ADR-0062): the same choices as every error popup (ErrorDialog), Send to
// developers (Help and feedback as a problem with that run's log and what went wrong) or OK. Either way the crashed run
// is not offered again.
AppDialog {
    id: dialog

    objectName: "crash.popup"
    title: qsTr("The last session ended unexpectedly")
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight

    // Shown once the window is up when the run log found a crashed run.
    Component.onCompleted: Qt.callLater(() => {
        if (RunLog.crashedLog !== "")
            dialog.open();
    })

    Column {
        id: column

        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.Label {
            width: parent.width
            wrapMode: Text.WordWrap
            text: qsTr("%1 did not close normally last time. You can send us the log of that session, so we can find the problem.").arg(ApplicationInfo.name)
        }
        Row {
            anchors.right: parent.right
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.Button {
                objectName: "crash.dismiss"
                fontIcon: "check"
                text: qsTr("OK")
                onClicked: {
                    RunLog.dismissCrash();
                    dialog.close();
                }
            }
            EaElements.Button {
                objectName: "crash.report"
                fontIcon: "paper-plane"
                text: qsTr("Send to developers")
                onClicked: {
                    AppState.crashReported(RunLog.crashedLogText(), qsTr("%1 closed unexpectedly.").arg(ApplicationInfo.name) + (RunLog.crashedDiagnostic() !== "" ? "\n" + RunLog.crashedDiagnostic() : ""));
                    dialog.close();
                }
            }
        }
    }
}
