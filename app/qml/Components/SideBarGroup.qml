// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Elements as EaElements

// A sidebar group: the base's GroupBox, whose height animates only when it folds or unfolds where it can be seen. The
// base animates every change of its height, also content arriving and groups folding while a page is built in the
// background, which kept every sidebar laying out for seconds after a project opened.
EaElements.GroupBox {
    id: group

    // The height the base animates towards (its implicitHeight without the animation).
    readonly property real restingHeight: collapsed ? titleArea.height : titleArea.height + spacing + contentHeight + bottomPadding
    property bool folding: false

    height: folding ? implicitHeight : restingHeight
    onCollapsedChanged: {
        if (!onScreen)
            return;
        folding = true;
        foldEnd.restart();
    }
    // On the current item of every SwipeView it is in (its page and its sidebar tab): a SwipeView keeps the others
    // visible.
    readonly property bool onScreen: {
        const chain = [];
        for (let item = group; item !== null; item = item.parent) {
            if (item instanceof SwipeView && !chain.includes((item as SwipeView).currentItem))
                return false;
            chain.push(item);
        }
        return true;
    }

    // The base's fold animation takes 500 ms.
    Timer {
        id: foldEnd
        interval: 550
        onTriggered: group.folding = false
    }
}
