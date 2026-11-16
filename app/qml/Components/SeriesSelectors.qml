// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A series of joint fits' two selectors above its charts (the owner, 2026-11-16): the series variable, labelled by
// what the points record ("Temperature 15.9 K", "Run" when nothing is), and Bank, shown only with more than one bank;
// each with a previous and a next button, which repeat while held. On Stacked and Map the Rows switch chooses rows by
// the variable (one bank across the series: the variable selector inactive) or by bank (every bank at one point: the
// Bank selector inactive).
Row {
    id: row

    property ProjectViewModel project: null
    // The shown tab's key: the Rows switch is Stacked's and Map's.
    property string viewKey: ""
    readonly property bool rowsShown: viewKey === "stacked" || viewKey === "map"
    readonly property ScanViewModel views: project ? project.scanViews : null
    readonly property bool byBank: rowsShown && views !== null && views.rowsByBank
    readonly property int revision: project ? project.seriesRevision : 0
    // The points a chart can show: the complete ones, which the grid lists first.
    readonly property var points: {
        const list = [];
        if (project === null || revision < 0)
            return list;
        for (let i = 0; i < project.seriesPointCount; ++i) {
            if (project.pointProblem(i) !== "")
                break;
            list.push(project.pointLabel(i));
        }
        return list;
    }
    readonly property var banks: project ? project.bankLabels : []
    readonly property real boxWidth: (width - rowsSwitch.width - 2 * prefixWidth - 4 * buttonWidth - spacing * (rowsShown ? 9 : 8)) / 2
    readonly property real buttonWidth: EaStyle.Sizes.comboBoxHeight
    readonly property real prefixWidth: EaStyle.Sizes.fontPixelSize * 4.5

    spacing: AppSizes.toolbarSpacing

    // Rows: by the variable or by bank.
    Row {
        id: rowsSwitch
        visible: row.rowsShown
        width: visible ? implicitWidth : 0
        spacing: EaStyle.Sizes.fontPixelSize * 0.5
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            rightPadding: EaStyle.Sizes.fontPixelSize * 0.5
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("Rows")
        }
        EaElements.Button {
            objectName: "mainArea.series.rowsByPoint"
            height: EaStyle.Sizes.comboBoxHeight
            checkable: true
            checked: !row.byBank
            text: qsTr("by %1").arg(row.project ? row.project.seriesVariable.toLowerCase() : "")
            onClicked: if (row.views)
                row.views.rowsByBank = false
        }
        EaElements.Button {
            objectName: "mainArea.series.rowsByBank"
            height: EaStyle.Sizes.comboBoxHeight
            checkable: true
            checked: row.byBank
            text: qsTr("by bank")
            onClicked: if (row.views)
                row.views.rowsByBank = true
        }
    }

    EaElements.Label {
        width: row.prefixWidth
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignRight
        rightPadding: EaStyle.Sizes.fontPixelSize * 0.5
        elide: Text.ElideRight
        color: EaStyle.Colors.themeForegroundMinor
        text: row.project ? row.project.seriesVariable : ""
    }
    SearchableComboBox {
        id: pointBox
        objectName: "mainArea.series.point"
        width: row.boxWidth
        enabled: !(row.rowsShown && !row.byBank)
        model: row.points
        currentIndex: row.project ? row.project.currentExperimentIndex : -1
        onActivated: index => {
            row.project.currentExperimentIndex = index;
            pointBox.currentIndex = Qt.binding(() => row.project ? row.project.currentExperimentIndex : -1);
        }
    }
    EaElements.SideBarButton {
        objectName: "mainArea.series.point.up"
        width: row.buttonWidth
        height: row.buttonWidth
        spacing: 0
        enabled: pointBox.enabled && pointBox.currentIndex > 0
        fontIcon: "arrow-circle-up"
        ToolTip.text: qsTr("Previous point")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.project.currentExperimentIndex = pointBox.currentIndex - 1
    }
    EaElements.SideBarButton {
        objectName: "mainArea.series.point.down"
        width: row.buttonWidth
        height: row.buttonWidth
        spacing: 0
        enabled: pointBox.enabled && pointBox.currentIndex >= 0 && pointBox.currentIndex < row.points.length - 1
        fontIcon: "arrow-circle-down"
        ToolTip.text: qsTr("Next point")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.project.currentExperimentIndex = pointBox.currentIndex + 1
    }

    EaElements.Label {
        visible: row.banks.length > 1
        width: row.prefixWidth
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignRight
        rightPadding: EaStyle.Sizes.fontPixelSize * 0.5
        color: EaStyle.Colors.themeForegroundMinor
        text: qsTr("Bank")
    }
    SearchableComboBox {
        id: bankBox
        objectName: "mainArea.series.bank"
        visible: row.banks.length > 1
        width: row.boxWidth
        enabled: !row.byBank
        model: row.banks.map((name, i) => `${i + 1} · ${name}`)
        currentIndex: row.project ? row.project.currentBank : -1
        onActivated: index => {
            row.project.currentBank = index;
            bankBox.currentIndex = Qt.binding(() => row.project ? row.project.currentBank : -1);
        }
    }
    EaElements.SideBarButton {
        objectName: "mainArea.series.bank.up"
        visible: row.banks.length > 1
        width: row.buttonWidth
        height: row.buttonWidth
        spacing: 0
        enabled: bankBox.enabled && bankBox.currentIndex > 0
        fontIcon: "arrow-circle-up"
        ToolTip.text: qsTr("Previous bank")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.project.currentBank = bankBox.currentIndex - 1
    }
    EaElements.SideBarButton {
        objectName: "mainArea.series.bank.down"
        visible: row.banks.length > 1
        width: row.buttonWidth
        height: row.buttonWidth
        spacing: 0
        enabled: bankBox.enabled && bankBox.currentIndex >= 0 && bankBox.currentIndex < row.banks.length - 1
        fontIcon: "arrow-circle-down"
        ToolTip.text: qsTr("Next bank")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.project.currentBank = bankBox.currentIndex + 1
    }
}
