// SPDX-License-Identifier: BSD-3-Clause
// The disk image window's background (edi ADR-0071): a neutral grey, the website's network in two corners with a few
// blue charges running along its lines, and "Double-click to install" in white above the installer's icon. Finder
// shows one fixed picture in light and dark mode, so it reads the same in both. package.py places the icon under
// the text (DISK_IMAGE_ICON); keep the two in step. Writes DiskImageBackground.png and its @2x copy:
//   QML_XHR_ALLOW_FILE_READ=1 qml -platform offscreen disk_image_background.qml -- <PTSans-Regular.ttf> <folder>
// PT Sans comes with the pinned gui-components (Gui/Resources/Fonts/PT_Sans); the network is the website's
// (website/surfaces/overrides/partials/network.svg).
import QtQuick

Window {
    id: window

    // Points: the window shows the top 400 by 250; the rest keeps a slightly taller window filled.
    readonly property int pointWidth: 400
    readonly property int pointHeight: 300
    readonly property var arguments: Qt.application.arguments.slice(Qt.application.arguments.indexOf("--") + 1)
    // The network at 0.42 of its own size (0.84 at 2x): its triangles about twice as large as the whole network
    // shrunk to the window would draw them (owner, 2026-11-26).
    readonly property real networkScale: 0.42
    // Where each bank's densest part (its lines' middles weighted by their opacity) lands, in points: the upper bank
    // round the top-right corner, the lower one round the bottom-left, the middle left quiet.
    readonly property var corners: ({
            "upper-bank": Qt.point(365, 10),
            "lower-bank": Qt.point(21, 245)
        })
    // The lines, in points: {x1, y1, x2, y2, opacity, bank}.
    property var lines: []
    property int scale: 1

    width: pointWidth * 2
    height: pointHeight * 2
    color: "transparent"
    visible: true

    FontLoader {
        id: ptSans

        source: "file://" + window.arguments[0]
    }

    Rectangle {
        id: canvas

        width: window.pointWidth * window.scale
        height: window.pointHeight * window.scale
        color: "#626264" // a neutral grey, readable under white text in light and dark mode

        Canvas {
            id: network

            anchors.fill: parent
            onPaint: {
                const context = getContext("2d");
                const s = window.scale;
                context.reset();
                context.lineWidth = 0.625 * s; // the website's 1.25 at half its size
                for (const line of window.lines) {
                    context.strokeStyle = Qt.rgba(0.86, 0.86, 0.87, line.opacity);
                    context.beginPath();
                    context.moveTo(line.x1 * s, line.y1 * s);
                    context.lineTo(line.x2 * s, line.y2 * s);
                    context.stroke();
                }
                // The charges: the front part of a line in the website's blue, fading out behind its head.
                context.lineWidth = 1.25 * s;
                for (const line of window.charges()) {
                    const tail = Qt.point(line.x1 + (line.x2 - line.x1) * 0.45, line.y1 + (line.y2 - line.y1) * 0.45);
                    const gradient = context.createLinearGradient(tail.x * s, tail.y * s, line.x2 * s, line.y2 * s);
                    gradient.addColorStop(0, Qt.rgba(0.04, 0.65, 0.87, 0));
                    gradient.addColorStop(1, Qt.rgba(0.04, 0.65, 0.87, 1));
                    context.strokeStyle = gradient;
                    context.beginPath();
                    context.moveTo(tail.x * s, tail.y * s);
                    context.lineTo(line.x2 * s, line.y2 * s);
                    context.stroke();
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            // The text's middle 48 points down, the icon's 130 (DISK_IMAGE_ICON).
            y: 48 * window.scale - height / 2
            text: "Double-click to install"
            color: "white"
            font.family: ptSans.name
            font.pixelSize: 20 * window.scale
        }
    }

    // The website's network, read from its SVG: each bank moved so its densest part sits at its corner.
    function readNetwork() {
        const request = new XMLHttpRequest();
        request.open("GET", Qt.resolvedUrl("../../website/surfaces/overrides/partials/network.svg"), false);
        request.send();
        const svg = request.responseText;
        const result = [];
        for (const bank of ["upper-bank", "lower-bank"]) {
            const start = svg.indexOf('id="' + bank + '"');
            const group = svg.slice(start, svg.indexOf("</g>", start));
            const pattern = /M(-?[\d.]+) (-?[\d.]+)L(-?[\d.]+) (-?[\d.]+)" stroke="#\w+" stroke-opacity="([\d.]+)"/g;
            const raw = [];
            let match;
            while ((match = pattern.exec(group)) !== null)
                raw.push(match.slice(1).map(Number));
            let weight = 0, cx = 0, cy = 0;
            for (const r of raw) {
                weight += r[4];
                cx += (r[0] + r[2]) / 2 * r[4];
                cy += (r[1] + r[3]) / 2 * r[4];
            }
            cx /= weight;
            cy /= weight;
            const k = window.networkScale, target = window.corners[bank];
            for (const r of raw)
                result.push({
                    x1: (r[0] - cx) * k + target.x,
                    y1: (r[1] - cy) * k + target.y,
                    x2: (r[2] - cx) * k + target.x,
                    y2: (r[3] - cy) * k + target.y,
                    opacity: r[4],
                    bank: bank
                });
        }
        if (result.length === 0)
            Qt.exit(3);
        window.lines = result;
    }

    // Three charges, kept away from the text and the icon (owner, 2026-11-26): two in the upper bank, one in the lower,
    // on the longest lines that lie wholly in view and clear of both, each on a line of its own that shares no point
    // with another charge's.
    function charges() {
        function clear(line) {
            const inView = [line.x1, line.x2].every(x => x > 4 && x < 396) && [line.y1, line.y2].every(y => y > 4 && y < 246);
            const midX = (line.x1 + line.x2) / 2, midY = (line.y1 + line.y2) / 2;
            const nearText = midY < 80 && midX > 90 && midX < 310;
            const nearIcon = Math.hypot(midX - 200, midY - 130) < 95;
            return inView && !nearText && !nearIcon;
        }
        const length = line => Math.hypot(line.x2 - line.x1, line.y2 - line.y1);
        const longest = bank => window.lines.filter(line => line.bank === bank && clear(line)).sort((a, b) => length(b) - length(a));
        const ends = line => [line.x1.toFixed(2) + "," + line.y1.toFixed(2), line.x2.toFixed(2) + "," + line.y2.toFixed(2)];
        const chosen = [];
        const take = (bank, count) => {
            for (const line of longest(bank)) {
                if (count === 0)
                    break;
                const shared = chosen.some(other => ends(other).some(end => ends(line).indexOf(end) >= 0));
                if (!shared) {
                    chosen.push(line);
                    count -= 1;
                }
            }
        };
        take("upper-bank", 2);
        take("lower-bank", 1);
        return chosen;
    }

    function save(scale, name, next) {
        window.scale = scale;
        network.requestPaint();
        // A frame after the size change, so the grab sees it.
        Qt.callLater(() => canvas.grabToImage(result => {
                if (!result.saveToFile(window.arguments[1] + "/" + name))
                    Qt.exit(1);
                next();
            }));
    }

    Timer {
        interval: 200
        running: ptSans.status === FontLoader.Ready
        onTriggered: window.save(1, "DiskImageBackground.png", () => window.save(2, "DiskImageBackground@2x.png", () => Qt.quit()))
    }

    Component.onCompleted: {
        if (window.arguments.length !== 2)
            Qt.exit(2);
        readNetwork();
    }
}
