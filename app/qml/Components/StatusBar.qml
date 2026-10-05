// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The status bar of the workflow pages (easydiffractionbeta Components/StatusBar.qml); hidden on Home. The
// first item, always present, counts the messages (warnings and errors) and opens them (edi ADR-0017 §14).
// The fit area on the right follows the running fit and then summarises the last one (§17): progress, then
// time, then χ², every item separated by FitOutcomes.separator.
EaElements.StatusBar {
    id: bar

    readonly property ProjectViewModel project: Session.project

    visible: EaGlobals.Vars.appBarCurrentIndex !== 0

    // The items show their keys only when all of them fit with their keys in the bar's width; otherwise each
    // shows its icon and value (the owner, 2026-10-03). Measured from the items' own widths, so it holds for
    // any window size, font and value; the base's row margins and spacing are its own.
    readonly property list<StatusBarItem> items: [warningsItem, projectItem, structuresItem, experimentsItem, calculatorItem, minimizerItem, parametersItem]
    readonly property FitViewModel fit: project ? project.fit : null
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
        const fitWidth = fitArea.visible ? fitArea.width + spacing : 0;
        return width + Math.max(0, shown - 1) * spacing + fitWidth <= bar.width - 2 * EaStyle.Sizes.fontPixelSize;
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
    // The fit area, right-aligned outside the base's row of items: the running fit's bar and live values, then
    // the last fit's summary, which opens its results.
    Row {
        id: fitArea

        readonly property bool running: bar.fit !== null && bar.fit.running
        readonly property string chi: bar.fit && bar.fit.goodnessOfFit !== "" ? `χ² ${bar.fit.goodnessOfFit}` : ""
        readonly property string iterations: bar.fit && bar.fit.iterations !== "" ? qsTr("it %1").arg(bar.fit.iterations) : ""

        function joined(parts) {
            return parts.filter(part => part !== "").join(FitOutcomes.separator);
        }

        objectName: "statusBar.fit"
        parent: bar
        anchors.right: parent.right
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        anchors.verticalCenter: parent.verticalCenter
        spacing: EaStyle.Sizes.fontPixelSize * 0.75
        visible: bar.fit !== null && (running || bar.fit.outcome !== "")

        Rectangle {
            width: EaStyle.Sizes.borderThickness
            height: EaStyle.Sizes.fontPixelSize * 1.5
            anchors.verticalCenter: parent.verticalCenter
            color: EaStyle.Colors.appBarBorder
        }
        FitProgressBar {
            objectName: "statusBar.fit.progress"
            visible: fitArea.running
            width: EaStyle.Sizes.fontPixelSize * 20
            anchors.verticalCenter: parent.verticalCenter
            indeterminate: true
            fontFamily: EaStyle.Fonts.ptMono.name
            text: fitArea.joined([qsTr("fitting"), fitArea.iterations])
        }
        FitOutcomeLabel {
            objectName: "statusBar.fit.outcome"
            visible: !fitArea.running && bar.fit !== null && bar.fit.outcome !== ""
            anchors.verticalCenter: parent.verticalCenter
            outcome: bar.fit ? bar.fit.outcome : ""
            // The last fit's results table, also for a project opened with one.
            clickable: bar.fit !== null && bar.fit.results.count > 0
            toolTipText: clickable ? qsTr("%1: click to see the results").arg(FitOutcomes.meaning(outcome)) : FitOutcomes.meaning(outcome)
            onClicked: fitResultsDialog.open()
        }
        Text {
            objectName: "statusBar.fit.values"
            anchors.verticalCenter: parent.verticalCenter
            font.family: EaStyle.Fonts.ptMono.name
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
            color: EaStyle.Colors.themeForeground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: {
                if (!bar.fit)
                    return "";
                if (fitArea.running)
                    return fitArea.joined([bar.fit.elapsed, fitArea.chi]);
                const rest = fitArea.joined([fitArea.iterations, bar.fit.elapsed, fitArea.chi]);
                return rest === "" ? "" : FitOutcomes.separator.trimStart() + rest;
            }
        }
    }

    WarningsDialog {
        id: warningsDialog
    }
    FitResultsDialog {
        id: fitResultsDialog
        objectName: "statusBar.fitResults"
    }
}
