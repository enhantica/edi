// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Show release notes, or dated changes for builds without a release history.
AppDialog {
    id: dialog

    property bool updateMode: false
    signal updateRequested

    // Every day of changes, newest first, read as the dialog opens.
    property var days: []
    // The last date the user saw when the dialog opened; the days after it are new.
    property string seen: ""
    property bool showAll: false
    readonly property bool releaseHistory: days.length > 0 && !!days[0].version
    readonly property bool previewHistory: releaseHistory && !!days[0].preview
    readonly property string lastSeen: previewHistory ? Preferences.whatsNewPreviewSeen : releaseHistory ? Preferences.whatsNewReleaseSeen : Preferences.whatsNewSeen
    // The new days, or the newest one when nothing is new, so the dialog never opens empty.
    readonly property var newDays: {
        const unseen = days.filter(day => releaseHistory ? (seen === "" || DesktopUpdates.newerVersion(day.version, seen)) : day.date > seen);
        return unseen.length > 0 ? unseen : days.slice(0, 1);
    }
    readonly property var shownDays: updateMode || showAll ? days : newDays

    // Keeps the newest date as seen, written to the settings file at once.
    function markSeen(date) {
        if (releaseHistory) {
            if (previewHistory) {
                Preferences.whatsNewPreviewSeen = date;
                Preferences.whatsNewSettings.setValue("previewSeen", date);
            } else {
                Preferences.whatsNewReleaseSeen = date;
                Preferences.whatsNewSettings.setValue("releaseSeen", date);
            }
            Preferences.whatsNewSettings.sync();
            return;
        }
        Preferences.whatsNewSeen = date;
        // The settings store a changed property on a timer; the value goes to the file now.
        Preferences.whatsNewSettings.setValue("seen", date);
        Preferences.whatsNewSettings.sync();
    }

    // At the first start after an update, once; a first start with no date stored yet takes the newest as seen.
    function showIfUpdated() {
        const all = ApplicationInfo.changes();
        if (all.length === 0)
            return;
        days = all;
        const latest = releaseHistory ? all[0].version : all[0].date;
        const previous = lastSeen;
        if (previous === "") {
            if (releaseHistory && (Preferences.whatsNewSeen !== "" || previewHistory && Preferences.whatsNewReleaseSeen !== ""))
                dialog.open();
            else
                dialog.markSeen(latest);
        } else if (releaseHistory ? DesktopUpdates.newerVersion(latest, previous) : latest > previous)
            dialog.open();
    }

    objectName: "whatsNew"
    title: updateMode ? qsTr("EasyDiffraction %1 is available").arg(DesktopUpdates.availableVersion) : qsTr("What's new")
    standardButtons: Dialog.Close
    footer: EaElements.DialogButtonBox {
        buttonLayout: DialogButtonBox.WinLayout

        EaElements.Button {
            objectName: dialog.updateMode ? "whatsNew.update" : "whatsNew.showAll"
            enabled: dialog.updateMode || !dialog.showAll && dialog.days.length > dialog.newDays.length
            text: dialog.updateMode ? qsTr("Update") : qsTr("Show all changes")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: {
                if (dialog.updateMode) {
                    dialog.close();
                    dialog.updateRequested();
                } else {
                    dialog.showAll = true;
                }
            }
        }
    }
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: Math.min(column.implicitHeight, EaStyle.Sizes.fontPixelSize * 30)

    onAboutToShow: {
        days = updateMode ? DesktopUpdates.availableChanges : ApplicationInfo.changes();
        seen = lastSeen;
        showAll = false;
    }
    // As soon as closing starts, which a close before the opening has finished also does.
    onAboutToHide: {
        if (!updateMode && days.length > 0)
            dialog.markSeen(releaseHistory ? days[0].version : days[0].date);
    }

    component NotesText: Text {
        width: parent.width
        wrapMode: Text.WordWrap
        textFormat: Text.MarkdownText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        color: EaStyle.Colors.themeForeground
        linkColor: EaStyle.Colors.themeAccent
        onLinkActivated: link => {
            if (/^https?:\/\//.test(link))
                Qt.openUrlExternally(link);
        }
    }

    Flickable {
        id: changesView

        anchors.fill: parent
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        // The app's scroll bar, as the feedback form's: shown while the list is taller than the window once it has
        // opened, and while scrolling.
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: dialog.opened && changesView.contentHeight > changesView.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
        }

        Column {
            id: column

            width: dialog.contentWidth
            spacing: EaStyle.Sizes.fontPixelSize

            Repeater {
                model: dialog.shownDays

                // The rows stand in their order at once, not only at the next frame.
                onItemAdded: column.forceLayout()
                onItemRemoved: column.forceLayout()

                Column {
                    id: day

                    required property var modelData

                    objectName: `whatsNew.day.${modelData.date}`
                    width: column.width
                    spacing: column.spacing

                    EaElements.Label {
                        readonly property var parts: day.modelData.date.split("-").map(Number)
                        readonly property string displayDate: Qt.formatDate(new Date(parts[0], parts[1] - 1, parts[2]), "d MMM yyyy")

                        font.bold: true
                        text: day.modelData.version ? qsTr("EasyDiffraction %1 (%2)").arg(day.modelData.version).arg(displayDate) : displayDate
                    }

                    NotesText {
                        visible: !day.modelData.version
                        text: visible ? day.modelData.text : ""
                    }

                    Repeater {
                        model: day.modelData.version ? day.modelData.text.split(/^### /m).filter(section => section.length > 0) : []

                        Column {
                            id: section

                            required property string modelData
                            readonly property int titleEnd: modelData.indexOf("\n")

                            width: day.width
                            spacing: EaStyle.Sizes.fontPixelSize * 0.5

                            EaElements.Label {
                                font.bold: true
                                text: section.modelData.slice(0, section.titleEnd)
                            }

                            NotesText {
                                text: section.modelData.slice(section.titleEnd + 1).trim()
                            }
                        }
                    }
                }
            }
            IconLink {
                objectName: "whatsNew.page"
                fontIcon: "external-link-alt"
                text: qsTr("The full page on the website")
                onClicked: Qt.openUrlExternally(ApplicationInfo.changesUrl)
            }
        }
    }
}
