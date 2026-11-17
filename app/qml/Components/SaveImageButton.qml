// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Dialogs

import edi.app

// Save image, one button in the main view's bottom-left corner for the shown tab (the owner, 2026-11-16): a PNG of
// `target` as shown, without its `toolbar`. The desktop asks where to save it, starting in the one folder every Save
// image remembers, at first the project's reports folder (the owner, 2026-11-10); the browser downloads it.
Row {
    id: save

    property Item target: null
    // The target's toolbar, hidden while the image is taken.
    property Item toolbar: null
    property string fileName: "image"
    // Whether the band the toolbar takes at the top of `target` is cut off: a chart's toolbar has its own band, the
    // structure view's floats over the scene, which stays whole.
    property bool cropToolbar: true

    function toolbarLine() {
        return save.target !== null ? save.toolbar : null;
    }
    // The image as Save image takes it, handed to `done` with the share of its height to cut off at the top: the
    // toolbar is hidden for the grab, and a chart's toolbar band is cut. `scale` renders it larger, sharp.
    // A target with a `transparentImage` property drops its background while it is grabbed, as Preferences asks.
    function capture(done, scale) {
        const line = toolbarLine();
        const shownOpacity = line ? line.opacity : 1;
        const clears = save.target !== null && save.target.transparentImage !== undefined;
        if (clears)
            save.target.transparentImage = Preferences.imageBackground !== "chart";
        // Below the toolbar's band when it is at the top, as a fraction of the height.
        const cut = line && cropToolbar && line.y + line.height < target.height / 2 ? (line.y + line.height) / target.height : 0;
        if (line)
            line.opacity = 0;
        save.target.grabToImage(result => {
            if (line)
                line.opacity = shownOpacity;
            if (clears)
                save.target.transparentImage = false;
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
                // The folder image export last chose (DialogFolders; an earlier version kept it in Preferences), else the
                // project's reports folder or Pictures.
                dialog.currentFolder = ApplicationInfo.imageFolder(String(DialogFolders.store.value("saveImage", Preferences.imageFolder)), Session.project ? Session.project.path : "", Session.project !== null && !Session.needsSaveAs);
                dialog.currentFile = dialog.currentFolder + "/" + save.fileName + ".png";
                dialog.open();
            }
        });
    }

    ChartToolButton {
        objectName: save.objectName + ".button"
        fontIcon: "camera"
        toolTip: qsTr("Save image")
        enabled: save.target !== null
        onClicked: save.grab()
    }
    FileDialog {
        id: dialog

        property var grabbed: null
        property real cut: 0

        title: qsTr("Save image")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        nameFilters: [qsTr("PNG images (*.png)")]
        onAccepted: {
            ApplicationInfo.saveImage(grabbed.image, selectedFile, cut);
            DialogFolders.remember("saveImage", selectedFile);
            grabbed = null;
        }
        onRejected: grabbed = null
    }
}
