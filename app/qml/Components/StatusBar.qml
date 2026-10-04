// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The status bar of the workflow pages (easydiffractionbeta Components/StatusBar.qml); hidden on Home. The
// fit items follow the last fit: its iterations, its reduced χ² before → after, and why it stopped. The last
// item, always present, counts the messages (warnings and errors) and opens them (edi ADR-0017 §14).
EaElements.StatusBar {
    id: bar

    readonly property ProjectViewModel project: Session.project

    visible: EaGlobals.Vars.appBarCurrentIndex !== 0

    // The items show their keys only when all of them fit with their keys in the bar's width; otherwise each
    // shows its icon and value (the owner, 2026-10-03). Measured from the items' own widths, so it holds for
    // any window size, font and value; the base's row margins and spacing are its own.
    readonly property list<StatusBarItem> items: [projectItem, structuresItem, experimentsItem, calculatorItem, minimizerItem, parametersItem, fitIterationsItem, goodnessOfFitItem, fitStatusItem, warningsItem]
    readonly property bool keysFit: {
        let width = 0;
        let shown = 0;
        for (const item of items) {
            if (item.visible) {
                width += item.labelledWidth;
                shown += 1;
            }
        }
        const spacing = EaStyle.Sizes.fontPixelSize * 1.2;
        return width + Math.max(0, shown - 1) * spacing <= bar.width - 2 * EaStyle.Sizes.fontPixelSize;
    }

    StatusBarItem {
        id: projectItem
        objectName: "statusBar.project"
        showKey: bar.keysFit
        keyIcon: "archive"
        keyText: qsTr("Project")
        valueText: bar.project ? bar.project.name : qsTr("Undefined")
        ToolTip.text: qsTr("Current project")
    }
    StatusBarItem {
        id: structuresItem
        objectName: "statusBar.structures"
        showKey: bar.keysFit
        visible: bar.project !== null
        keyIcon: "layer-group"
        keyText: qsTr("Structures")
        valueText: bar.project ? bar.project.structures.count : ""
        ToolTip.text: qsTr("Number of structures")
    }
    StatusBarItem {
        id: experimentsItem
        objectName: "statusBar.experiments"
        showKey: bar.keysFit
        visible: bar.project !== null
        keyIcon: "microscope"
        keyText: qsTr("Experiments")
        valueText: bar.project ? bar.project.experiments.count : ""
        ToolTip.text: qsTr("Number of experiments")
    }
    StatusBarItem {
        id: calculatorItem
        objectName: "statusBar.calculator"
        showKey: bar.keysFit
        keyIcon: "calculator"
        keyText: qsTr("Calculator")
        valueText: "crysta"
        ToolTip.text: qsTr("Calculation engine")
    }
    StatusBarItem {
        id: minimizerItem
        objectName: "statusBar.minimizer"
        showKey: bar.keysFit
        visible: bar.project !== null
        keyIcon: "level-down-alt"
        keyText: qsTr("Minimizer")
        valueText: bar.project ? bar.project.analysis.minimizerType : ""
        ToolTip.text: qsTr("Minimization engine")
    }
    StatusBarItem {
        id: parametersItem
        objectName: "statusBar.parameters"
        showKey: bar.keysFit
        visible: bar.project !== null
        keyIcon: "th-list"
        keyText: qsTr("Parameters")
        valueText: bar.project ? qsTr("%1 (%2 free, %3 fixed)").arg(bar.project.parameters.count).arg(bar.project.parameters.freeCount).arg(bar.project.parameters.fixedCount) : ""
        ToolTip.text: qsTr("Number of parameters: total, free and fixed")
    }
    StatusBarItem {
        id: fitIterationsItem
        objectName: "statusBar.fitIterations"
        showKey: bar.keysFit
        visible: bar.project !== null && valueText !== ""
        keyIcon: "spinner"
        keyText: qsTr("Fit iterations")
        valueText: bar.project ? bar.project.fit.iterations : ""
        ToolTip.text: qsTr("Number of iterations of the last fit")
    }
    StatusBarItem {
        id: goodnessOfFitItem
        objectName: "statusBar.goodnessOfFit"
        showKey: bar.keysFit
        visible: bar.project !== null && valueText !== ""
        keyIcon: "thumbs-up"
        keyText: qsTr("Goodness-of-fit")
        valueText: bar.project ? bar.project.fit.goodnessOfFit : ""
        ToolTip.text: valueText.includes("→") ? qsTr("Reduced χ² goodness-of-fit: before → after") : qsTr("Reduced χ² goodness-of-fit")
    }
    StatusBarItem {
        id: fitStatusItem
        objectName: "statusBar.fitStatus"
        showKey: bar.keysFit
        visible: bar.project !== null && valueText !== ""
        keyIcon: "clipboard"
        keyText: qsTr("Fit status")
        valueText: bar.project ? bar.project.fit.status : ""
        // The last fit's results table, also for a project opened with one.
        clickable: bar.project !== null && bar.project.fit.results.count > 0
        ToolTip.text: clickable ? qsTr("How the last fit ended: click to see its results") : qsTr("How the last fit ended")
        onClicked: fitResultsDialog.open()
    }
    StatusBarItem {
        id: warningsItem
        objectName: "statusBar.warnings"
        showKey: bar.keysFit
        keyIcon: "exclamation-triangle"
        keyText: qsTr("Messages")
        valueText: String(Session.loadWarnings ? Session.loadWarnings.unviewedCount : 0)
        alert: Session.loadWarnings !== null && Session.loadWarnings.unviewedCount > 0
        clickable: true
        ToolTip.text: qsTr("Warnings and errors: click to see them")
        onClicked: warningsDialog.open()
    }

    WarningsDialog {
        id: warningsDialog
    }
    FitResultsDialog {
        id: fitResultsDialog
        objectName: "statusBar.fitResults"
    }
}
