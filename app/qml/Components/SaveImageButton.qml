// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle

import edi.app

// Save image, the last button of a chart's or the structure view's toolbar, in its own group (the owner,
// 2026-11-08): a PNG of `target` as shown. The desktop asks where to save it; the browser downloads it.
Row {
    id: save

    property Item target: null
    property string fileName: "image"

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
        onClicked: save.target.grabToImage(result => {
            if (WebFiles.available) {
                ApplicationInfo.downloadImage(result.image, save.fileName + ".png");
            } else {
                dialog.grabbed = result;
                dialog.open();
            }
        })
    }
    FileDialog {
        id: dialog

        property var grabbed: null

        title: qsTr("Save image")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "png"
        currentFile: "file:///" + save.fileName + ".png"
        nameFilters: [qsTr("PNG images (*.png)")]
        onAccepted: {
            ApplicationInfo.saveImage(grabbed.image, selectedFile);
            grabbed = null;
        }
        onRejected: grabbed = null
    }
}
