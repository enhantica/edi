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
// The fit area on the right follows the running fit and then summarises the last one (§17): the live values (time,
// then χ², every item separated by FitOutcomes.separator) with the progress bar at the far right, which stays put while
// their width changes.
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
        const fitWidth = fitArea.visible ? fitArea.width + spacing : 0;
        return width + Math.max(0, shown - 1) * spacing + fitWidth <= bar.width - 2 * EaStyle.Sizes.fontPixelSize;
    }
    // How many of the items, in their order, fit beside the fit area with their icons and values only: the
    // rest give way, the last first (owner, 2026-10-05: the items never run into the fit area).
    readonly property int roomFor: {
        const spacing = EaStyle.Sizes.fontPixelSize * 1.2;
        const available = bar.width - 2 * EaStyle.Sizes.fontPixelSize - (fitArea.visible ? fitArea.width + spacing : 0);
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
    // The fit area, right-aligned outside the base's row of items: the running fit's bar and live values, then
    // the last fit's summary, which opens its results.
    Row {
        id: fitArea

        readonly property bool running: bar.fit !== null && bar.fit.running
        readonly property bool scanning: bar.fit !== null && bar.fit.scanning
        // The pattern-update mode, the patterns a scan has drawn and the file drawn last (the browser checks read
        // them).
        readonly property int patternUpdates: bar.fit !== null ? bar.fit.patternUpdates : -1
        readonly property int scanPatternUpdates: bar.fit !== null ? bar.fit.scanPatternUpdates : 0
        readonly property string scanShownFile: bar.fit !== null ? bar.fit.scanShownFile : ""
        // The ok and fail counts: an ok count above zero in green, a fail count above zero in red.
        function counts() {
            const ok = qsTr("%1 ok").arg(bar.fit.scanOk);
            const fail = qsTr("%1 fail").arg(bar.fit.scanFailed);
            return [bar.fit.scanOk > 0 ? `<font color="${EaStyle.Colors.green}">${ok}</font>` : ok, bar.fit.scanFailed > 0 ? `<font color="${EaStyle.Colors.red}">${fail}</font>` : fail];
        }
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
        Item {
            id: fitValues
            objectName: "statusBar.fit.values"
            anchors.verticalCenter: parent.verticalCenter
            implicitWidth: valuePieces.implicitWidth
            implicitHeight: valuePieces.implicitHeight
            readonly property string text: {
                if (!bar.fit)
                    return "";
                // One order everywhere: progress, the ok and fail counts, time, χ².
                if (fitArea.scanning)
                    return fitArea.joined(fitArea.counts().concat([bar.fit.elapsed, bar.fit.eta !== "" ? qsTr("eta %1").arg(bar.fit.eta) : "", fitArea.chi]));
                if (fitArea.running)
                    return fitArea.joined([bar.fit.elapsed, fitArea.chi]);
                // A scan's summary: files, then the ok and fail counts, time, χ².
                const rest = bar.fit.scanSummary ? fitArea.joined([bar.fit.scanFiles].concat(fitArea.counts(), [bar.fit.elapsed, fitArea.chi])) : fitArea.joined([fitArea.iterations, bar.fit.elapsed, fitArea.chi]);
                return rest === "" ? "" : FitOutcomes.separator.trim() + " " + rest;
            }
            FontMetrics {
                id: fitValueMetrics
                // The left items' font and size (the owner, 2026-10-13).
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
            }
            // The widest digit of the app's font, which has no tabular digits: every digit is drawn centred in a cell
            // that wide, as tabular figures are, so the live counters keep a steady width (the owner, 2026-10-13).
            readonly property real digitWidth: {
                let widest = 0;
                for (let digit = 0; digit <= 9; ++digit)
                    widest = Math.max(widest, fitValueMetrics.advanceWidth(String(digit)));
                return Math.ceil(widest);
            }
            // A piece of the values as runs of text, each with its colour (the counts' <font color> markup) and whether it
            // is a number.
            function runs(text: string): var {
                const out = [];
                const coloured = /<font color="([^"]+)">(.*?)<\/font>/g;
                let at = 0;
                const split = (part, color) => {
                    for (const token of part.split(/([0-9][0-9.:,]*)/)) {
                        if (token !== "")
                            out.push({
                                "text": token,
                                "color": color,
                                "number": /^[0-9]/.test(token)
                            });
                    }
                };
                for (let match = coloured.exec(text); match !== null; match = coloured.exec(text)) {
                    split(text.slice(at, match.index), "");
                    split(match[2], match[1]);
                    at = coloured.lastIndex;
                }
                split(text.slice(at), "");
                return out;
            }
            Row {
                id: valuePieces
                Repeater {
                    model: fitValues.text.split(" → ")
                    delegate: Item {
                        id: valuePart
                        required property string modelData
                        required property int index
                        readonly property bool hasArrow: index < fitValues.text.split(" → ").length - 1
                        readonly property real gap: EaStyle.Sizes.fontPixelSize * 0.5
                        implicitWidth: numberText.implicitWidth + (hasArrow ? changeArrow.width + 2 * gap : 0)
                        implicitHeight: fitValueMetrics.height
                        Row {
                            id: numberText
                            objectName: `statusBar.fit.valuePart.${valuePart.index}`
                            readonly property font font: fitValueMetrics.font
                            readonly property color color: EaStyle.Colors.themeForeground
                            // The piece's plain text, for what reads it.
                            readonly property string text: valuePart.modelData.replace(/<[^>]*>/g, "")
                            Repeater {
                                model: fitValues.runs(valuePart.modelData)
                                delegate: Row {
                                    id: run
                                    required property var modelData
                                    Repeater {
                                        // A number one character at a time, so each digit takes its own cell.
                                        model: run.modelData.number ? run.modelData.text.split("") : [run.modelData.text]
                                        delegate: Text {
                                            required property string modelData
                                            width: /^[0-9]$/.test(modelData) ? fitValues.digitWidth : implicitWidth
                                            y: fitValueMetrics.ascent - baselineOffset
                                            horizontalAlignment: Text.AlignHCenter
                                            font: numberText.font
                                            textFormat: Text.PlainText
                                            color: run.modelData.color !== "" ? run.modelData.color : numberText.color
                                            text: modelData
                                        }
                                    }
                                }
                            }
                        }
                        TextMetrics {
                            id: digitInk
                            font: numberText.font
                            text: "0"
                        }
                        Text {
                            id: changeArrow
                            objectName: "statusBar.fit.changeArrow"
                            x: numberText.implicitWidth + valuePart.gap
                            y: fitValueMetrics.ascent + digitInk.tightBoundingRect.y + digitInk.tightBoundingRect.height / 2 - (baselineOffset + arrowInk.tightBoundingRect.y + arrowInk.tightBoundingRect.height / 2)
                            font.family: EaStyle.Fonts.encodeSansRegular.name
                            font.pixelSize: fitValueMetrics.font.pixelSize
                            color: numberText.color
                            text: "→"
                            visible: valuePart.hasArrow
                        }
                        TextMetrics {
                            id: arrowInk
                            font: changeArrow.font
                            text: changeArrow.text
                        }
                    }
                }
            }
        }
        // Scan results the template has changed since stay, marked out of date until the next run replaces them.
        Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: outOfDate.visible
            font: outOfDate.font
            color: EaStyle.Colors.themeForeground
            text: FitOutcomes.separator.trim()
        }
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
            objectName: "statusBar.fit.progress"
            visible: fitArea.running
            width: EaStyle.Sizes.fontPixelSize * 20
            anchors.verticalCenter: parent.verticalCenter
            // A scan fills the bar by its files (S3); a single fit, whose length is unknown, with stripes.
            indeterminate: bar.fit === null || !bar.fit.scanning
            fraction: bar.fit !== null && bar.fit.scanning && bar.fit.scanTotal > 0 ? bar.fit.scanProcessed / bar.fit.scanTotal : 0
            fontFamily: EaStyle.Fonts.ptMono.name
            text: fitArea.scanning ? bar.fit.scanText : fitArea.joined([qsTr("fitting"), fitArea.iterations])
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
