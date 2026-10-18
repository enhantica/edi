// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The status bar of the workflow pages (easydiffractionbeta Components/StatusBar.qml); hidden on Home. The
// first item, always present, counts the messages (warnings and errors) and opens them (edi ADR-0017 §14).
// The fit area on the right follows the running fit and then summarises the last one (§17), as status items like the
// ones on the left: the live values with the progress bar at the far right, then the outcome and the values.
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
            if (item.shown) {
                width += item.labelledWidth;
                shown += 1;
            }
        }
        const spacing = EaStyle.Sizes.fontPixelSize * 1.2;
        const fitWidth = fitArea.visible ? fitArea.labelledWidth + spacing : 0;
        return width + Math.max(0, shown - 1) * spacing + fitWidth <= bar.width - 2 * EaStyle.Sizes.fontPixelSize;
    }
    // How many of the items, in their order, fit beside the fit area with their icons and values only: the
    // rest give way, the last first (owner, 2026-10-05: the items never run into the fit area).
    readonly property int roomFor: {
        const spacing = EaStyle.Sizes.fontPixelSize * 1.2;
        const available = bar.width - 2 * EaStyle.Sizes.fontPixelSize - (fitArea.visible ? fitArea.compactWidth + spacing : 0);
        let width = 0;
        for (let i = 0; i < items.length; ++i) {
            if (!items[i].shown)
                continue;
            width += (width > 0 ? spacing : 0) + items[i].compactWidth;
            if (width > available)
                return i;
        }
        return items.length;
    }

    StatusBarItem {
        id: warningsItem
        objectName: "statusBar.warnings"
        showKey: bar.keysFit
        room: bar.items.indexOf(warningsItem) < bar.roomFor
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
        room: bar.items.indexOf(projectItem) < bar.roomFor
        keyIcon: "archive"
        keyText: qsTr("Project")
        valueText: bar.project ? bar.project.name : qsTr("Undefined")
        ToolTip.text: qsTr("Current project")
    }
    StatusBarItem {
        id: structuresItem
        objectName: "statusBar.structures"
        showKey: bar.keysFit
        room: bar.items.indexOf(structuresItem) < bar.roomFor
        shown: bar.project !== null && valueText !== ""
        keyIcon: "layer-group"
        keyText: qsTr("Structures")
        valueText: bar.project ? bar.project.structures.count : ""
        ToolTip.text: qsTr("Number of structures")
    }
    StatusBarItem {
        id: experimentsItem
        objectName: "statusBar.experiments"
        showKey: bar.keysFit
        room: bar.items.indexOf(experimentsItem) < bar.roomFor
        shown: bar.project !== null && valueText !== ""
        keyIcon: "microscope"
        keyText: qsTr("Experiments")
        valueText: bar.project ? bar.project.experiments.count : ""
        ToolTip.text: bar.project && bar.project.scan ? qsTr("1 template experiment, %1 datasets").arg(bar.project.experiments.count) : qsTr("Number of experiments")
    }
    StatusBarItem {
        id: calculatorItem
        objectName: "statusBar.calculator"
        showKey: bar.keysFit
        room: bar.items.indexOf(calculatorItem) < bar.roomFor
        keyIcon: "calculator"
        keyText: qsTr("Calculator")
        valueText: "crysta"
        ToolTip.text: qsTr("Calculation engine")
    }
    StatusBarItem {
        id: minimizerItem
        objectName: "statusBar.minimizer"
        showKey: bar.keysFit
        room: bar.items.indexOf(minimizerItem) < bar.roomFor
        shown: bar.project !== null && valueText !== ""
        keyIcon: "level-down-alt"
        keyText: qsTr("Minimizer")
        valueText: bar.project ? bar.project.analysis.minimizerType : ""
        ToolTip.text: qsTr("Minimization engine")
    }
    StatusBarItem {
        id: parametersItem
        objectName: "statusBar.parameters"
        showKey: bar.keysFit
        room: bar.items.indexOf(parametersItem) < bar.roomFor
        shown: bar.project !== null && valueText !== ""
        keyIcon: "th-list"
        keyText: qsTr("Parameters")
        valueText: bar.project ? qsTr("%1 (%2 free, %3 fixed)").arg(bar.project.parameters.count).arg(bar.project.parameters.freeCount).arg(bar.project.parameters.fixedCount) : ""
        ToolTip.text: qsTr("Number of parameters: total, free and fixed")
    }
    // The fit area, right-aligned outside the base's row of items: the last fit's status and values as status items like
    // the ones on the left (the owner, 2026-10-13), and while a fit runs its live values with the progress bar at the
    // far right, which stays put while their width changes. The status opens the last fit's results.
    Row {
        id: fitArea

        objectName: "statusBar.fit"
        parent: bar
        anchors.right: parent.right
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        anchors.verticalCenter: parent.verticalCenter
        spacing: EaStyle.Sizes.fontPixelSize * 1.2
        visible: bar.fit !== null && (running || bar.fit.outcome !== "")

        readonly property bool running: bar.fit !== null && bar.fit.running
        readonly property bool scanning: bar.fit !== null && bar.fit.scanning
        readonly property bool summary: bar.fit !== null && !running
        readonly property bool scanSummary: summary && bar.fit.scanSummary
        // The pattern-update mode, the patterns a scan has drawn and the file drawn last (the browser checks read
        // them).
        readonly property int patternUpdates: bar.fit !== null ? bar.fit.patternUpdates : -1
        readonly property int scanPatternUpdates: bar.fit !== null ? bar.fit.scanPatternUpdates : 0
        readonly property string scanShownFile: bar.fit !== null ? bar.fit.scanShownFile : ""
        readonly property list<FitStatusItem> items: [statusItem, filesItem, okItem, failedItem, iterationsItem, timeItem, etaItem, chiItem]
        // The area's width with every key shown and with none: what the bar measures, whatever it shows now.
        readonly property real labelledWidth: widthWith(item => item.labelledWidth)
        readonly property real compactWidth: widthWith(item => item.compactWidth)

        function widthWith(itemWidth) {
            let width = rule.width;
            let shown = 1;
            for (const item of items) {
                if (item.shown) {
                    width += itemWidth(item);
                    shown += 1;
                }
            }
            for (const extra of [outOfDate, progress]) {
                if (extra.visible) {
                    width += extra.width;
                    shown += 1;
                }
            }
            return width + (shown - 1) * spacing;
        }

        Rectangle {
            id: rule
            width: EaStyle.Sizes.borderThickness
            height: EaStyle.Sizes.fontPixelSize * 1.5
            anchors.verticalCenter: parent.verticalCenter
            color: EaStyle.Colors.appBarBorder
        }
        // The last fit's outcome, in its colour.
        FitStatusItem {
            id: statusItem
            objectName: "statusBar.fit.outcome"
            readonly property string outcome: bar.fit ? bar.fit.outcome : ""
            shown: fitArea.summary && outcome !== ""
            showKey: bar.keysFit
            keyIcon: FitOutcomes.icon(outcome)
            keyText: qsTr("Status")
            valueText: FitOutcomes.word(outcome)
            iconColor: FitOutcomes.color(outcome)
            valueColor: FitOutcomes.color(outcome)
            // The last fit's results table, also for a project opened with one.
            clickable: bar.fit !== null && bar.fit.results.count > 0
            ToolTip.text: clickable ? qsTr("%1: click to see the results").arg(FitOutcomes.meaning(outcome)) : FitOutcomes.meaning(outcome)
            onClicked: fitResultsDialog.open()
        }
        Row {
            objectName: "statusBar.fit.values"
            anchors.verticalCenter: parent.verticalCenter
            spacing: fitArea.spacing
            // The values shown, for what reads them.
            readonly property string text: fitArea.items.slice(1).filter(item => item.shown).map(item => item.valueText).join(" ")

            FitStatusItem {
                id: filesItem
                shown: fitArea.scanSummary
                showKey: bar.keysFit
                keyIcon: "copy"
                keyText: qsTr("Files")
                valueText: bar.fit ? bar.fit.scanFiles : ""
                ToolTip.text: qsTr("Files fitted out of the scan's files")
            }
            FitStatusItem {
                id: okItem
                shown: fitArea.scanning || fitArea.scanSummary
                showKey: bar.keysFit
                keyIcon: "check"
                keyText: qsTr("OK")
                valueText: bar.fit ? String(bar.fit.scanOk) : ""
                iconColor: bar.fit && bar.fit.scanOk > 0 ? EaStyle.Colors.green : EaStyle.Colors.statusBarIconForeground
                valueColor: bar.fit && bar.fit.scanOk > 0 ? EaStyle.Colors.green : EaStyle.Colors.themeForeground
                ToolTip.text: qsTr("Files whose fit converged")
            }
            FitStatusItem {
                id: failedItem
                shown: fitArea.scanning || fitArea.scanSummary
                showKey: bar.keysFit
                keyIcon: "times"
                keyText: qsTr("Failed")
                valueText: bar.fit ? String(bar.fit.scanFailed) : ""
                iconColor: bar.fit && bar.fit.scanFailed > 0 ? EaStyle.Colors.red : EaStyle.Colors.statusBarIconForeground
                valueColor: bar.fit && bar.fit.scanFailed > 0 ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
                ToolTip.text: qsTr("Files whose fit did not converge")
            }
            FitStatusItem {
                id: iterationsItem
                shown: fitArea.summary && !fitArea.scanSummary && valueText !== ""
                showKey: bar.keysFit
                keyIcon: "sync-alt"
                keyText: qsTr("Iterations")
                valueText: bar.fit ? bar.fit.iterations : ""
                ToolTip.text: qsTr("Iterations of the last fit")
            }
            FitStatusItem {
                id: timeItem
                shown: bar.fit !== null && valueText !== ""
                showKey: bar.keysFit
                keyIcon: "stopwatch"
                keyText: qsTr("Time")
                valueText: bar.fit ? bar.fit.elapsed : ""
                ToolTip.text: fitArea.running ? qsTr("Time since the fit started") : qsTr("Time the fit took")
            }
            FitStatusItem {
                id: etaItem
                shown: fitArea.scanning && valueText !== ""
                showKey: bar.keysFit
                keyIcon: "hourglass-half"
                keyText: qsTr("ETA")
                valueText: bar.fit ? bar.fit.eta : ""
                ToolTip.text: qsTr("Time the scan's remaining files will take")
            }
            FitStatusItem {
                id: chiItem
                shown: bar.fit !== null && valueText !== ""
                showKey: bar.keysFit
                keyIcon: "thumbs-up"
                keyText: qsTr("χ²")
                // The values before and after the fit with no spaces round the arrow (the owner, 2026-10-13).
                valueText: bar.fit ? bar.fit.goodnessOfFit.replace(/\s*→\s*/g, "→") : ""
                ToolTip.text: fitArea.scanSummary ? qsTr("Reduced χ² over the scan's files, least to greatest") : qsTr("Reduced χ², before and after the fit")
            }
        }
        // Scan results the template has changed since stay, marked out of date until the next run replaces them.
        Text {
            id: outOfDate
            objectName: "statusBar.fit.outOfDate"
            anchors.verticalCenter: parent.verticalCenter
            visible: !fitArea.running && bar.fit !== null && bar.fit.outOfDate
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            color: EaStyle.Colors.orange
            text: qsTr("out of date")
        }
        // Last, at the far right: the live values before it change width, and the bar stays where it is.
        FitProgressBar {
            id: progress
            objectName: "statusBar.fit.progress"
            visible: fitArea.running
            width: EaStyle.Sizes.fontPixelSize * 20
            // As tall as the status item's hover frame (the owner, 2026-10-13).
            height: statusItem.frameHeight
            anchors.verticalCenter: parent.verticalCenter
            // A scan fills the bar by its files (S3); a single fit, whose length is unknown, with stripes.
            indeterminate: bar.fit === null || !bar.fit.scanning
            fraction: bar.fit !== null && bar.fit.scanning && bar.fit.scanTotal > 0 ? bar.fit.scanProcessed / bar.fit.scanTotal : 0
            fontFamily: EaStyle.Fonts.ptMono.name
            text: fitArea.scanning ? bar.fit.scanText : [qsTr("fitting"), bar.fit && bar.fit.iterations !== "" ? qsTr("it %1").arg(bar.fit.iterations) : ""].filter(part => part !== "").join(FitOutcomes.separator)
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
