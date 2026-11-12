// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle

import edi.app

// Save image, the last button of a chart's or the structure view's toolbar, in its own group (the owner,
// 2026-11-08): a PNG of `target` as shown, without its toolbar. The desktop asks where to save it, starting in the one
// folder every Save image remembers, at first the project's reports folder (the owner, 2026-11-10); the browser
// downloads it.
Row {
    id: save

    property Item target: null
    property string fileName: "image"
    // Whether the band the toolbar takes at the top of `target` is cut off: a chart's toolbar has its own band, the
    // structure view's floats over the scene, which stays whole.
    property bool cropToolbar: true

    // The toolbar line this button is in: its ancestor that `target` holds directly.
    function toolbarLine() {
        for (let item = save; item !== null; item = item.parent) {
            if (item.parent === save.target)
                return item;
        }
        return null;
    }
    // The image as Save image takes it, handed to `done` with the share of its height to cut off at the top: the
    // toolbar is hidden for the grab, and a chart's toolbar band is cut. `scale` renders it larger, sharp.
    function capture(done, scale) {
        const line = toolbarLine();
        const shownOpacity = line ? line.opacity : 1;
        // Below the toolbar's band when it is at the top, as a fraction of the height.
        const cut = line && cropToolbar && line.y + line.height < target.height / 2 ? (line.y + line.height) / target.height : 0;
        if (line)
            line.opacity = 0;
        save.target.grabToImage(result => {
            if (line)
                line.opacity = shownOpacity;
            done(result, cut);
        }, Qt.size(Math.round(target.width * (scale || 1)), Math.round(target.height * (scale || 1))));
    }
    // Saves the image straight to `file` (a URL), as the dialog's choice would, `scale` times as large: the demo
    // renders documentation figures with it.
    function saveTo(file, scale) {
        capture((result, cut) => ApplicationInfo.saveImage(result.image, file, cut), scale);
    }
    function grab() {
        capture((result, cut) => {
            if (WebFiles.available) {
                ApplicationInfo.downloadImage(result.image, save.fileName + ".png", cut);
            } else {
                dialog.grabbed = result;
                dialog.cut = cut;
                dialog.currentFolder = ApplicationInfo.imageFolder(Preferences.imageFolder, Session.project ? Session.project.path : "", Session.project !== null && !Session.needsSaveAs);
                dialog.currentFile = dialog.currentFolder + "/" + save.fileName + ".png";
                dialog.open();
            }
        });
    }

    spacing: AppSizes.toolbarSpacing

    Item {
        width: EaStyle.Sizes.fontPixelSize * 0.5
        height: 1
    }
    ChartToolButton {
        objectName: save.objectName + ".button"
        fontIcon: "camera"
        toolTip: qsTr("Save image")
        enabled: save.target !== null
        onClicked: save.grab()
    }
    NativeFileDialog {
        id: dialog

        property var grabbed: null
        property real cut: 0

        title: qsTr("Save image")
        fileMode: NativeFileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: [qsTr("PNG images (*.png)")]
        onAccepted: {
            ApplicationInfo.saveImage(grabbed.image, selectedFile, cut);
            Preferences.imageFolder = ApplicationInfo.folderOf(selectedFile).toString();
            grabbed = null;
        }
        onRejected: grabbed = null
    }
}
