// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Report page's live preview (edi ADR-0035): the report model's sections, in its order, drawn from the model's
// JSON values only. It is set as the HTML report is, after the owner's reference report (diffraction-lib's style,
// 2026-10-13): PT Sans headings at its sizes and margins, numbered sections and records, each category of a structure
// or an experiment in its own subsection under its figure (the structure view, the pattern chart), bordered tables one
// line per row, in the app's theme colours.
Flickable {
    id: preview

    property ReportViewModel report: null
    readonly property var model: report ? report.model : ({})
    readonly property var sections: model.sections ?? []
    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The reference's sizes and margins are in points over its 10.04 pt body.
    readonly property real pt: em / 10.04
    // The figures (the structure views and the pattern charts), unless Contents leaves the charts out.
    readonly property bool charts: (model.contents ?? []).some(item => item.key === "charts" && item.included)

    function shown(name) {
        return sections.indexOf(name) >= 0;
    }
    // The figures for the PDF as images, each at twice its size and named as the static report names it
    // (structure-0, pattern-1, ...). They are copies of the preview's figures in the light colours, as a PDF is for
    // print, made outside the view, given a few frames to draw, then grabbed and removed. `done` gets the images once
    // every grab has answered; a figure that cannot be grabbed is left out.
    function grabFigures(done) {
        const jobs = [];
        for (const [records, kind, component] of [[structureRecords, "structure", printStructure], [experimentRecords, "pattern", printPattern]]) {
            for (let i = 0; i < records.count; ++i) {
                const record = records.itemAt(i);
                const shown = record ? record.figureItem : null;
                if (!shown || shown.width <= 0 || shown.height <= 0)
                    continue;
                const properties = {
                    "width": shown.width,
                    "height": shown.height,
                    "report": preview.report
                };
                properties[kind === "structure" ? "reportStructure" : "reportExperiment"] = record.modelData.id;
                const copy = component.createObject(printFigures, properties);
                if (copy)
                    jobs.push({
                        "item": copy,
                        "name": `${kind}-${i}`
                    });
            }
        }
        printFigures.start(jobs, done);
    }
    function number(section) {
        return sections.indexOf(section) + 1;
    }
    // A key-value table's rows from the model's rows, each value followed by its units: a degree sign right after the
    // number (90°, 0.24°²), other units after a space (3.88 Å).
    function keyValues(rows) {
        return (rows ?? []).map(row => [row.label, !row.units ? row.text : row.units.startsWith("°") ? row.text + row.units : row.text + " " + row.units]);
    }

    contentHeight: column.implicitHeight + 2 * AppSizes.reportPadding
    clip: true
    ScrollBar.vertical: EaElements.ScrollBar {
        policy: ScrollBar.AsNeeded
    }

    // A heading: PT Sans in its regular weight at the reference's size, with its margins. A heading right under another
    // starts after the larger of the two margins between them, as the reference's margins collapse.
    component Heading: EaElements.Label {
        property int level: 2
        property int under: 0  // the level of a heading right above this one; 0 for none
        readonly property var sizes: ({
                "2": 14.35,
                "3": 11.96,
                "4": 10.91
            })
        readonly property var tops: ({
                "2": 16.8,
                "3": 17.5,
                "4": 13.2
            })
        readonly property var bottoms: ({
                "2": 7,
                "3": 10.8,
                "4": 6.2
            })

        width: parent ? parent.width : implicitWidth
        wrapMode: Text.Wrap
        topPadding: Math.max(0, tops[level] - (under > 0 ? bottoms[under] : 0)) * preview.pt
        bottomPadding: bottoms[level] * preview.pt
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: Math.round(sizes[level] * preview.pt)
        color: EaStyle.Colors.themeForeground
    }

    // One category: its heading, its labelled values, then its table.
    component CategoryBlock: Column {
        id: block

        required property var category
        property int level: 4
        property int under: 0

        width: parent ? parent.width : 0
        Heading {
            level: block.level
            under: block.under
            text: block.category.title
        }
        ReportTable {
            visible: rows.length > 0
            rows: preview.keyValues(block.category.rows)
        }
        Item {
            visible: block.category.rows.length > 0 && block.category.table.rows.length > 0
            width: 1
            height: 6.2 * preview.pt
        }
        ReportTable {
            columns: block.category.table.columns
            rows: block.category.table.rows
        }
    }

    // A structure or an experiment: its numbered heading, then its categories. The records are counted, not listed, so a
    // rebuilt model updates each record and its figure in place rather than making them again.
    component Record: Column {
        id: record

        required property int index
        property string section: ""
        readonly property var modelData: (preview.model[section] ?? [])[index] ?? ({
                "id": "",
                "categories": []
            })

        width: parent ? parent.width : 0
        // The figure, for the PDF's grab; null while the charts are left out.
        readonly property Item figureItem: figure.item as Item
        Heading {
            level: 3
            under: record.index === 0 ? 2 : 0
            text: `${preview.number(record.section)}.${record.index + 1}.  ${record.modelData.id}`
        }
        // Its figure first, as the reference report places it: the structure view, or the pattern chart, framed by a
        // border in the tables' colour and spaced as a table is (the owner, 2026-10-13).
        Item {
            visible: preview.charts
            width: parent.width
            height: visible ? figure.height : 0

            Loader {
                id: figure
                active: preview.charts
                width: parent.width
                height: active ? Math.round(width * 0.7) : 0
                sourceComponent: record.section === "structures" ? structureFigure : patternFigure
            }
            Rectangle {
                width: figure.width
                height: figure.height
                color: "transparent"
                border.width: EaStyle.Sizes.borderThickness
                border.color: EaStyle.Colors.appBorder
            }
        }
        Component {
            id: structureFigure
            StructureView {
                report: preview.report
                reportStructure: record.modelData.id
            }
        }
        Component {
            id: patternFigure
            PatternChart {
                report: preview.report
                reportExperiment: record.modelData.id
            }
        }
        Repeater {
            model: record.modelData.categories
            delegate: CategoryBlock {
                required property var modelData
                required property int index
                category: modelData
                // A heading after the figure is spaced as one after a table.
                under: index === 0 && !preview.charts ? 3 : 0
            }
        }
    }

    Component {
        id: printStructure
        StructureView {
            colors: FigureColors {
                light: true
            }
        }
    }
    Component {
        id: printPattern
        PatternChart {
            colors: FigureColors {
                light: true
            }
        }
    }

    // The PDF's figure copies, left of the preview's content and so out of view, kept until they are grabbed.
    Item {
        id: printFigures

        property var jobs: []
        property var done: null
        property int frames: 0

        function start(jobs, done) {
            if (jobs.length === 0) {
                done({});
                return;
            }
            printFigures.jobs = jobs;
            printFigures.done = done;
            printFigures.frames = 0;
            Window.window.update();
        }
        // Grabs every copy, removes them all once the last grab has answered and hands the images on.
        function grabAll() {
            const jobs = printFigures.jobs;
            const done = printFigures.done;
            printFigures.jobs = [];
            const figures = {};
            let left = jobs.length;
            const finish = () => {
                if (--left > 0)
                    return;
                for (const job of jobs)
                    job.item.destroy();
                done(figures);
            };
            for (const job of jobs) {
                const asked = job.item.grabToImage(result => {
                    figures[job.name] = result.image;
                    finish();
                }, Qt.size(job.item.width * 2, job.item.height * 2));
                if (!asked)
                    finish();
            }
        }

        x: -width - AppSizes.reportPadding
        width: column.width
        height: childrenRect.height

        // Three drawn frames after the copies are made, so the charts and the 3D views have drawn.
        Connections {
            target: printFigures.jobs.length > 0 ? printFigures.Window.window : null
            function onFrameSwapped() {
                if (++printFigures.frames < 3)
                    printFigures.Window.window.update();
                else
                    printFigures.grabAll();
            }
        }
    }

    Column {
        id: column

        x: AppSizes.reportPadding
        y: AppSizes.reportPadding
        width: preview.width - 2 * AppSizes.reportPadding

        // The title block: what it is, then the project's title (its short name without one) and its authors.
        EaElements.Label {
            bottomPadding: 14 * preview.pt
            font.pixelSize: Math.round(14.35 * preview.pt)
            color: EaStyle.Colors.themeForeground
            text: qsTr("%1 Report").arg(Qt.application.name)
        }
        EaElements.Label {
            objectName: "report.preview.title"
            width: parent.width
            wrapMode: Text.Wrap
            font.pixelSize: Math.round(17.22 * preview.pt)
            color: EaStyle.Colors.themeForeground
            text: preview.model.title || preview.model.name || ""
        }
        EaElements.Label {
            visible: text !== ""
            topPadding: 7 * preview.pt
            color: EaStyle.Colors.themeForegroundMinor
            text: preview.model.authors ?? ""
        }
        // The title block's margin, less the first heading's own.
        Item {
            width: 1
            height: (22.8 - 16.8) * preview.pt
        }

        // Project summary
        Column {
            width: parent.width
            visible: preview.shown("summary")
            Heading {
                text: `${preview.number("summary")}.  ` + qsTr("Project summary")
            }
            EaElements.Label {
                visible: text !== ""
                width: parent.width
                topPadding: (11.9 - 7) * preview.pt
                bottomPadding: 20.4 * preview.pt
                wrapMode: Text.Wrap
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(20.4 * preview.pt)
                color: EaStyle.Colors.themeForeground
                text: preview.model.description ?? ""
            }
            ReportTable {
                rows: [[qsTr("Short name"), preview.model.name ?? ""], [qsTr("Structures"), (preview.model.structure_ids ?? []).join(", ")], [qsTr("Experiments"), (preview.model.experiment_ids ?? []).join(", ")], [qsTr("Generated"), preview.model.generated ?? ""]]
            }
        }

        // Analysis: the software, the minimizer, the fitting mode and the fit result
        Column {
            width: parent.width
            visible: preview.shown("analysis")
            Heading {
                text: `${preview.number("analysis")}.  ` + qsTr("Analysis")
            }
            Repeater {
                model: preview.shown("analysis") ? (preview.model.analysis ?? []) : []
                delegate: CategoryBlock {
                    required property var modelData
                    required property int index
                    category: modelData
                    level: 3
                    under: index === 0 ? 2 : 0
                }
            }
        }

        // Structures, one record each
        Column {
            width: parent.width
            visible: preview.shown("structures")
            Heading {
                text: `${preview.number("structures")}.  ` + qsTr("Structures")
            }
            Repeater {
                id: structureRecords
                model: preview.shown("structures") ? (preview.model.structures ?? []).length : 0
                delegate: Record {
                    section: "structures"
                }
            }
        }

        // Experiments, one record each
        Column {
            width: parent.width
            visible: preview.shown("experiments")
            Heading {
                text: `${preview.number("experiments")}.  ` + qsTr("Experiments")
            }
            Repeater {
                id: experimentRecords
                model: preview.shown("experiments") ? (preview.model.experiments ?? []).length : 0
                delegate: Record {
                    section: "experiments"
                }
            }
        }

        // Correlations
        Column {
            width: parent.width
            visible: preview.shown("correlations")
            Heading {
                text: `${preview.number("correlations")}.  ` + qsTr("Correlations")
            }
            ReportCorrelations {
                correlations: preview.model.correlations ?? null
            }
        }

        // Evolution, for a scan
        Column {
            width: parent.width
            visible: preview.shown("evolution")
            Heading {
                text: `${preview.number("evolution")}.  ` + qsTr("Evolution")
            }
            EaElements.Label {
                color: EaStyle.Colors.themeForegroundMinor
                text: qsTr("The fitted parameters across the scan's datasets")
            }
        }
    }
}
