// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A selector's line leaves out its values, one after the other, before it cuts the file to fewer than ten characters,
// half a dozen at each end and the ellipsis (T10).
Item {
    id: root

    width: 900
    height: 100

    readonly property string file: "01_213_002p3440.dat"

    BlockSelector {
        id: selector

        width: 700
        blockKind: "experiment"
        blocks: ["experiment_high_temp · " + root.file + " · Rwp 4.69 % · 497.379 K"]
        blockIndex: 0
    }
    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    TestCase {
        name: "BlockSelectorFile"
        when: windowShown

        function piece(item, text) {
            for (const child of item.children) {
                if (child.text === text && child.visible)
                    return child;
                const deeper = piece(child, text);
                if (deeper)
                    return deeper;
            }
            return null;
        }
        function test_the_file_keeps_ten_characters() {
            const least = metrics.advanceWidth(root.file.slice(0, 6) + "…" + root.file.slice(-6));
            for (let width = 480; width <= 700; width += 10) {
                selector.width = width;
                wait(20);
                const shown = piece(selector, root.file);
                verify(shown, `the file shows at ${width} px`);
                verify(shown.width >= Math.min(least, shown.implicitWidth) - 1, `${shown.width} px of the file's least ${least} px at ${width} px`);
            }
        }
    }
}
