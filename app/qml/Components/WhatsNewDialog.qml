// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// What's new (ADR-0067): the changes since the user last looked, newest first, from the bundled changelog that is also
// the docs site's What's new page. Show all changes, in the footer beside Close, lists every day; only the list
// scrolls. The link at its end opens that page. Closing it marks
// everything as seen. Until numbered releases exist the changes are grouped by date, and the last date seen is kept in
// the settings (Preferences.whatsNewSeen).
AppDialog {
    id: dialog

    // Every day of changes, newest first, read as the dialog opens.
    property var days: []
    // The last date the user saw when the dialog opened; the days after it are new.
    property string seen: ""
    property bool showAll: false
    readonly property bool releaseHistory: days.length > 0 && !!days[0].version
    // The new days, or the newest one when nothing is new, so the dialog never opens empty.
    readonly property var newDays: {
        const unseen = days.filter(day => releaseHistory ? (seen === "" || DesktopUpdates.newerVersion(day.version, seen)) : day.date > seen);
        return unseen.length > 0 ? unseen : days.slice(0, 1);
    }
    readonly property var shownDays: showAll ? days : newDays

    // Keeps the newest date as seen, written to the settings file at once.
    function markSeen(date) {
        if (releaseHistory) {
            Preferences.whatsNewReleaseSeen = date;
            Preferences.whatsNewSettings.setValue("releaseSeen", date);
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
        const previous = releaseHistory ? Preferences.whatsNewReleaseSeen : Preferences.whatsNewSeen;
        if (previous === "") {
            if (releaseHistory && Preferences.whatsNewSeen !== "")
                dialog.open();
            else
                dialog.markSeen(latest);
        } else if (releaseHistory ? DesktopUpdates.newerVersion(latest, previous) : latest > previous)
            dialog.open();
    }

    objectName: "whatsNew"
    title: qsTr("What's new")
    standardButtons: Dialog.Close
    // Always in sight, beside Close (the owner, 2026-11-02); off once every day is shown.
    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "whatsNew.showAll"
            enabled: !dialog.showAll && dialog.days.length > dialog.newDays.length
            text: qsTr("Show all changes")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: dialog.showAll = true
        }
    }
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: Math.min(column.implicitHeight, EaStyle.Sizes.fontPixelSize * 30)

    onAboutToShow: {
        days = ApplicationInfo.changes();
        seen = releaseHistory ? Preferences.whatsNewReleaseSeen : Preferences.whatsNewSeen;
        showAll = false;
    }
    // As soon as closing starts, which a close before the opening has finished also does.
    onAboutToHide: {
        if (days.length > 0)
            dialog.markSeen(releaseHistory ? days[0].version : days[0].date);
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
                    spacing: EaStyle.Sizes.fontPixelSize * 0.5

                    EaElements.Label {
                        font.bold: true
                        text: day.modelData.version ? `EasyDiffraction ${day.modelData.version} · ${day.modelData.date}` : day.modelData.date
                    }
                    // A plain Text, so a link opens only when it is a web address.
                    Text {
                        width: parent.width
                        wrapMode: Text.WordWrap
                        textFormat: Text.MarkdownText
                        font.family: EaStyle.Fonts.fontFamily
                        font.pixelSize: EaStyle.Sizes.fontPixelSize
                        color: EaStyle.Colors.themeForeground
                        linkColor: EaStyle.Colors.themeAccent
                        text: day.modelData.text
                        onLinkActivated: link => {
                            if (/^https?:\/\//.test(link))
                                Qt.openUrlExternally(link);
                        }
                    }
                }
            }
            IconLink {
                objectName: "whatsNew.page"
                fontIcon: "book"
                text: qsTr("The full page on the website")
                onClicked: Qt.openUrlExternally(ApplicationInfo.changesUrl)
            }
        }
    }
}
