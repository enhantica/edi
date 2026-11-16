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
// Bank selector inactive). ← and → step the bank.
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
            list.push(project.pointName(i));
        }
        return list;
    }
    readonly property var banks: project ? project.bankLabels : []
    // Each selector's box, beside its previous and next buttons; the two share what the Rows switch leaves.
    readonly property real boxWidth: (width - rowsSwitch.width - 4 * buttonWidth - spacing * (rowsShown ? 7 : 6)) / 2
    readonly property real buttonWidth: EaStyle.Sizes.comboBoxHeight

    spacing: AppSizes.toolbarSpacing

    // ← and → step the bank, as its buttons do, unless a text field has the keys (the owner, 2026-11-16).
    function stepBank(offset) {
        const next = (project ? project.currentBank : 0) + offset;
        if (project !== null && bankBox.enabled && next >= 0 && next < banks.length)
            project.currentBank = next;
    }
    readonly property bool keysFree: Window.activeFocusItem === null || Window.activeFocusItem.cursorPosition === undefined
    Shortcut {
        sequence: "Left"
        enabled: row.visible && row.banks.length > 1 && row.keysFree
        onActivated: row.stepBank(-1)
    }
    Shortcut {
        sequence: "Right"
        enabled: row.visible && row.banks.length > 1 && row.keysFree
        onActivated: row.stepBank(1)
    }

    // Rows: by the variable or by bank, a toolbar drop-down as the charts' other row choices are.
    ToolbarComboBox {
        id: rowsSwitch
        objectName: "mainArea.series.rows"
        visible: row.rowsShown
        width: visible ? implicitWidth : 0
        height: EaStyle.Sizes.comboBoxHeight
        toolTip: qsTr("Rows: one bank across the series, or every bank at one point")
        readonly property var entries: [qsTr("by %1").arg(row.project ? row.project.seriesVariable.toLowerCase() : ""), qsTr("by bank")]
        model: entries
        closedTexts: entries.map(entry => qsTr("Rows: %1").arg(entry))
        shownIndex: row.byBank ? 1 : 0
        onActivated: index => {
            if (row.views)
                row.views.rowsByBank = index === 1;
        }
    }

    // The runs and the banks, as the block selector lists blocks: "Run 6 · p005" and "Bank 5 · wish_5_6", the word,
    // the number and the dot greyed (BlockSelector.numberPrefix; the owner, 2026-11-16).
    ListModel {
        id: runModel
    }
    ListModel {
        id: bankModel
    }
    function fill(model, labels) {
        if (model.count === labels.length && labels.every((label, i) => model.get(i).label === label))
            return;
        model.clear();
        for (const label of labels)
            model.append({
                label: label
            });
    }
    onPointsChanged: fill(runModel, points)
    onBanksChanged: fill(bankModel, banks)
    Component.onCompleted: {
        fill(runModel, points);
        fill(bankModel, banks);
    }

    BlockSelector {
        id: pointBox
        objectName: "mainArea.series.point"
        width: row.boxWidth + 2 * (row.buttonWidth + row.spacing)
        enabled: !(row.rowsShown && !row.byBank)
        backgroundColor: EaStyle.Colors.chartBackground
        blocks: runModel
        blocksTextRole: "label"
        blockKind: "run"
        numberPrefix: row.project ? row.project.seriesVariable : ""
        blockIndex: row.project ? row.project.currentExperimentIndex : -1
        onBlockActivated: index => row.project.currentExperimentIndex = index
    }
    BlockSelector {
        id: bankBox
        objectName: "mainArea.series.bank"
        visible: row.banks.length > 1
        width: row.boxWidth + 2 * (row.buttonWidth + row.spacing)
        enabled: !row.byBank
        backgroundColor: EaStyle.Colors.chartBackground
        blocks: bankModel
        blocksTextRole: "label"
        blockKind: "bank"
        numberPrefix: qsTr("Bank")
        blockIndex: row.project ? row.project.currentBank : -1
        onBlockActivated: index => row.project.currentBank = index
    }
}
