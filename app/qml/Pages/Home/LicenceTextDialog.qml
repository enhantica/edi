// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A licence text bundled in the app's resources (the app's licence, the source code's, or the third-party
// notices), opened from About: read-only, in the monospaced font, scrolling within a fixed size. A link in it to
// another bundled text (the app notice links COPYING, LICENSE and THIRD-PARTY-NOTICES) opens that text here;
// ApplicationInfo resolves it against this text's location and admits only the bundled licence texts.
AppDialog {
    id: dialog

    property string url: ""

    function showText(title: string, url: string) {
        dialog.title = title;
        dialog.url = url;
        dialog.open();
    }

    // Opens the bundled text a link in the shown one leads to, under its own title; any other link does nothing.
    function followLink(link: string) {
        const target = ApplicationInfo.licenceLinkTarget(dialog.url, link);
        if (target) {
            dialog.showText(dialog.titleOf(target), target);
        }
    }

    function titleOf(url: string): string {
        if (url === ApplicationInfo.licenseUrl) {
            return qsTr("BSD 3-Clause License");
        }
        if (url === ApplicationInfo.noticesUrl) {
            return qsTr("Dependent Open Source Licenses");
        }
        if (url === ApplicationInfo.appLicenseUrl) {
            return qsTr("Licence");
        }
        return qsTr("GNU General Public License");
    }

    objectName: "licenceText"
    // Over the whole window, not inside About's content, so it centres on the window as every dialog does.
    parent: Overlay.overlay
    standardButtons: Dialog.Ok
    contentWidth: AppSizes.licenceTextWidth
    contentHeight: AppSizes.licenceTextHeight

    Flickable {
        anchors.fill: parent
        contentHeight: licenceText.implicitHeight
        clip: true
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        EaElements.TextArea {
            id: licenceText
            objectName: "licenceText.text"
            width: parent.width
            readOnly: true
            wrapMode: TextEdit.Wrap
            textFormat: (dialog.url.endsWith(".md") || dialog.url === ApplicationInfo.noticesUrl) ? TextEdit.MarkdownText : TextEdit.PlainText
            font.family: textFormat === TextEdit.MarkdownText ? EaStyle.Fonts.fontFamily : EaStyle.Fonts.monoFontFamily
            text: dialog.url ? ApplicationInfo.licenceText(dialog.url) : ""
            onLinkActivated: link => dialog.followLink(link)

            HoverHandler {
                cursorShape: licenceText.hoveredLink ? Qt.PointingHandCursor : Qt.IBeamCursor
            }
            // A click on a link opens it: the read-only text area inside the popup does not activate its links
            // on a click by itself (measured on the offscreen platform the app tests use), so the tap is read
            // here.
            TapHandler {
                onTapped: eventPoint => {
                    const link = licenceText.linkAt(eventPoint.position.x, eventPoint.position.y);
                    if (link) {
                        dialog.followLink(link);
                    }
                }
            }
        }
    }
}
