// SPDX-License-Identifier: BSD-3-Clause
// Draws the installer's small images at 1x, 2x and 3x into tools/installer/icons: the logo from app/web's
// SVGs at the size the pages show it, and the app's Font Awesome icons in the app's colours. The PNGs are
// committed, as the Font Awesome font comes with the app build (gui-components), not with packaging. Run
// from the repository root with the installer environment's Qt:
//   QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software qml6 tools/installer/render_images.qml -- <font>
// where <font> is gui-components' "Font Awesome 5 Free-Solid-900.otf" at the pin in cmake/EdiGuiBase.cmake.

import QtQuick

Window {
    id: root

    readonly property string fontFile: Qt.application.arguments[Qt.application.arguments.length - 1]
    readonly property string out: Qt.resolvedUrl("icons/").toString().replace("file://", "")
    // name, kind (svg or glyph), source (file or Font Awesome name), width, height, colour, and for a glyph whether it
    // stands at the left (its picture then carries the gap to the text after it) instead of in the middle, and the
    // glyph's size where it is smaller than the picture (it then stands at the picture's top)
    readonly property var jobs: jobList()
    property int next: 0

    width: 600
    height: 200
    visible: true
    color: "transparent"

    FontLoader {
        id: awesome
        source: "file://" + root.fontFile
    }

    Item {
        id: canvas

        property var job: root.jobs[0]
        property int scale: 1

        width: job[3] * scale
        height: job[4] * scale

        Image {
            anchors.fill: parent
            visible: canvas.job[1] === "svg"
            source: canvas.job[1] === "svg" ? canvas.job[2] : ""
            sourceSize: Qt.size(canvas.width, canvas.height)
            smooth: true
        }
        Text {
            x: canvas.job[6] ? 0 : (parent.width - width) / 2
            y: ((canvas.job[7] || canvas.job[4]) * canvas.scale - height) / 2
            visible: canvas.job[1] === "glyph"
            font.family: awesome.name
            font.pixelSize: (canvas.job[7] || canvas.job[4]) * canvas.scale
            color: canvas.job[5] || "black"
            text: canvas.job[1] === "glyph" ? canvas.job[2] : ""
        }
    }

    function jobList() {
        const list = [];
        list.push(["logo", "svg", "../../app/web/logo.svg", 140, 44, ""]);
        list.push(["logo-dark", "svg", "../../app/web/logo-dark.svg", 140, 44, ""]);
        // The app's warning: exclamation-triangle in its orange (gui-components Colors.qml), 16 px wide at 14 px
        // (Font Awesome draws it 1.125 em wide). The pop-ups take it alone; a line of text takes it with the 4 px a
        // button leaves between its icon and its text.
        list.push(["warning", "glyph", "exclamation-triangle", 16, 14, "#FF9800"]);
        list.push(["warning-dark", "glyph", "exclamation-triangle", 16, 14, "#FFCC80"]);
        // In a line of text the picture is centred on the line, which leaves the sign about 1 px under the
        // capitals' middle (measured on Linux and macOS captures): it stands at the top of a picture 2 px taller.
        list.push(["warning-line", "glyph", "exclamation-triangle", 20, 16, "#FF9800", true, 14]);
        list.push(["warning-line-dark", "glyph", "exclamation-triangle", 20, 16, "#FFCC80", true, 14]);
        // The wizard buttons' icons. The window around the pages follows the system palette and its stylesheet is
        // one for light and dark (InstallerChrome.qss), so the outlined buttons' icons take the grey that reads on
        // both, and the filled ones (the accent) white.
        list.push(["button-back", "glyph", "arrow-left", 14, 14, "#888888"]);
        list.push(["button-cancel", "glyph", "times", 14, 14, "#888888"]);
        list.push(["button-next", "glyph", "arrow-right", 14, 14, "#ffffff"]);
        list.push(["button-done", "glyph", "check", 14, 14, "#ffffff"]);
        list.push(["button-done-plain", "glyph", "check", 14, 14, "#888888"]);
        return list;
    }

    function step() {
        if (next >= jobs.length * 3) {
            Qt.quit();
            return;
        }
        canvas.job = jobs[Math.floor(next / 3)];
        canvas.scale = next % 3 + 1;
        var file = out + canvas.job[0] + (canvas.scale > 1 ? "@" + canvas.scale + "x" : "") + ".png";
        next += 1;
        Qt.callLater(function () {
            canvas.grabToImage(function (result) {
                result.saveToFile(file);
                step();
            });
        });
    }

    Component.onCompleted: {
        if (awesome.status === FontLoader.Ready)
            step();
        else
            awesome.statusChanged.connect(function () {
                if (awesome.status === FontLoader.Ready)
                    step();
            });
    }
}
