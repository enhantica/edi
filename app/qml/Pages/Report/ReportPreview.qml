// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Report page's live preview (edi ADR-0036): the report model's sections, in its order, drawn from the model's
// JSON values only. It is set as the HTML report is, after the owner's reference report (diffraction-lib's style,
// 2026-10-13): PT Sans headings at its sizes and margins, numbered sections and records, each category of a structure
// or an experiment in its own subsection under its figure (the structure view, the pattern chart), bordered tables one
// line per row, in the app's theme colours.
Flickable {
    id: preview
    // Scrolled to whole device pixels: a 1 px border or a hairline falls between two otherwise and is lost.
    pixelAligned: true

    property ReportViewModel report: null
    // Whether the preview is drawn. Reading the model builds the report, so a preview that is not drawn reads
    // nothing and holds no sections: opening a project builds its report only when the Report page is shown.
    property bool drawn: true
    readonly property var model: report && drawn ? report.model : ({})
    readonly property var sections: model.sections ?? []
    // An evolution chart's height to its width: the Evolution tab's at the app's default window size, so a report's
    // chart has the axes' proportions the app shows (the owner, 2026-10-14).
    readonly property real evolutionAspect: 1.05
    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The reference's sizes and margins are in points over its 10.04 pt body.
    readonly property real pt: em / 10.04
    // The figures (the structure views and the pattern charts), unless Contents leaves the charts out.
    readonly property bool charts: ApplicationInfo.reportChartsIncluded()

    // What moves a figure onto whole device pixels, whatever the text heights above it add up to, so the plot areas'
    // borders are drawn whole.
    function pixelShift(item: Item): real {
        let y = 0;
        for (let up = item; up && up !== preview.contentItem; up = up.parent)
            y += up.y;
        const ratio = Screen.devicePixelRatio;
        return Math.round(y * ratio) / ratio - y;
    }
    function shown(name) {
        return ApplicationInfo.reportSection(name, false);
    }

    // The Text tab's background, under the scrolling content (the owner, 2026-10-21).
    Rectangle {
        parent: preview
        anchors.fill: parent
        z: -1
        color: EaStyle.Colors.textViewBackground
    }
    // The figures for the PDF as images, each at twice its size and named as the static report names it
    // (structure-0, pattern-1, ...). They are copies of the preview's figures in the light colours, as a PDF is for
    // print, made outside the view, given a few frames to draw, then grabbed and removed. `done` gets the images once
    // every grab has answered; a figure that cannot be grabbed is left out.
    // A save publishes the model it writes just before this, and a repeater remade for it can hold no record for a
    // moment, or one with no figure while the charts option is read again: the grab then waits a few frames for every
    // record's figure, so a repeat save keeps its figures (a pattern figure went missing from about one save in two).
    // Past the wait it grabs what there is.
    function grabFigures(done) {
        grabWait.done = done;
        grabWait.left = 20;
        grabWait.check();
    }
    function figuresReady(): bool {
        for (const records of [structureRecords, experimentRecords]) {
            for (let i = 0; i < records.count; ++i) {
                const record = records.itemAt(i);
                // Charts left out read no figure here either: the wait then runs out and the grab finds none.
                if (!record || !record.figureItem)
                    return false;
            }
        }
        for (let i = 0; i < evolutionRecords.count; ++i) {
            if (!evolutionRecords.itemAt(i))
                return false;
        }
        return true;
    }
    Timer {
        id: grabWait

        property var done: null
        property int left: 0

        function check() {
            if (left > 0 && !preview.figuresReady()) {
                --left;
                start();
                return;
            }
            const finish = done;
            done = null;
            if (finish)
                ApplicationInfo.reportGrabFigures(finish);
        }

        interval: 50
        onTriggered: check()
    }
    // A line never breaks just after a hyphen or a dash ("Per-" over "bank", "Jorgensen–" over "Von Dreele"): a word
    // joiner after each holds the two sides together (the owner's sweep, 2026-11-22).
    // Nor does a paragraph end on one word alone: its last two words are held together.
    function unbroken(text: string): string {
        return text.replace(/([-\u2013])/g, "$1\u2060").replace(/ (\S+)$/, "\u00a0$1");
    }
    function number(section) {
        return ApplicationInfo.reportSection(section, true);
    }
    // A key-value table's rows from the model's rows, each value followed by its units after a space (90 deg, 3.88 Å).
    function keyValues(rows) {
        return ApplicationInfo.reportKeyValues(rows);
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
            text: preview.unbroken(block.category.title)
        }
        ReportTable {
            visible: rows.length > 0
            rows: preview.keyValues(block.category.rows)
        }
        Item {
            visible: block.category.rows.length > 0 && (block.category.table.row_count ?? block.category.table.rows.length) > 0
            width: 1
            height: 6.2 * preview.pt
        }
        ReportTable {
            columns: block.category.table.columns
            rows: block.category.table.rows
            report: preview.report
            rowsKey: block.category.table.rows_key ?? ""
            storedRows: block.category.table.row_count ?? 0
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
        // The figure, for the PDF's grab, which reads only its size: the loader, sized as the figure will be, until the
        // figure is made; null while the charts are left out.
        readonly property Item figureItem: figure.status === Loader.Ready ? figure.item as Item : figure.active ? figure : null
        Heading {
            level: 3
            under: record.index === 0 ? 2 : 0
            text: `${preview.number(record.section)}.${record.index + 1}.  ${record.modelData.id}`
        }
        // Its figure first, as the reference report places it: the structure view or the pattern chart, framed by a border
        // in the tables' colour (the owner, 2026-11-24; the charts had none, 2026-10-14); spaced as a table is.
        Item {
            id: figureBox

            visible: preview.charts
            width: parent.width
            height: visible ? figure.height : 0
            transform: Translate {
                y: preview.pixelShift(figureBox)
            }

            // Made a slice at a time, as the categories are: a report's charts and structure views, made at once, held
            // the window on the Report page's first show.
            Loader {
                id: figure
                asynchronous: true
                active: preview.charts
                width: parent.width
                height: active ? Math.round(width * 0.7) : 0
                sourceComponent: record.section === "structures" ? structureFigure : record.modelData.single_crystal ? singleCrystalFigure : patternFigure
            }
            // Every figure in the same border (the owner, 2026-11-24), its control buttons inside it.
            Rectangle {
                width: figure.width
                height: figure.height
                color: "transparent"
                border.width: EaStyle.Sizes.borderThickness
                border.color: EaStyle.Colors.appBorder
            }
        }
        // The figures in the light theme's colours whatever the app's, as the HTML and PDF draw them.
        Component {
            id: structureFigure
            StructureView {
                objectName: "report.structure." + record.index
                report: preview.report
                reportStructure: record.modelData.id
                reportToolbar: true
                colors: FigureColors {
                    light: true
                }
            }
        }
        Component {
            id: patternFigure
            PatternChart {
                objectName: "report.pattern." + record.index
                report: preview.report
                reportExperiment: record.modelData.id
                reportToolbar: true
                colors: FigureColors {
                    light: true
                }
            }
        }
        Component {
            id: singleCrystalFigure
            SingleCrystalChart {
                objectName: "report.singleCrystal"
                reportData: record.modelData.single_crystal
                colors: FigureColors {
                    light: true
                }
            }
        }
        // Each category is made a slice at a time (asynchronous), so a long report's first show does not hold the
        // window: made all at once, the 44k scan's report took 1.2 s in one frame.
        Repeater {
            model: record.modelData.categories
            delegate: Loader {
                id: categorySlot
                required property var modelData
                required property int index
                width: parent ? parent.width : 0
                asynchronous: true
                sourceComponent: CategoryBlock {
                    category: categorySlot.modelData
                    // A heading after the figure is spaced as one after a table.
                    under: categorySlot.index === 0 && !preview.charts ? 3 : 0
                }
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
        id: printEvolution
        EvolutionChart {
            colors: FigureColors {
                light: true
            }
        }
    }
    Component {
        id: printSingleCrystal
        SingleCrystalChart {
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
            ApplicationInfo.reportCaptureStart(jobs, done);
        }
        // Grabs every copy, removes them all once the last grab has answered and hands the images on.
        function grabAll() {
            ApplicationInfo.reportCaptureAll();
        }

        x: -width - AppSizes.reportPadding
        width: column.width
        height: childrenRect.height

        // Three drawn frames after the copies are made, so the charts and the 3D views have drawn.
        Connections {
            target: printFigures.jobs.length > 0 ? printFigures.Window.window : null
            function onFrameSwapped() {
                ApplicationInfo.reportCaptureFrame();
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
            text: preview.unbroken(preview.model.title || preview.model.name || "")
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
                // About one and a half lines for the font: 20.4 report points over this smaller font read as double
                // spacing, and the reference's own ratio still as near double (the owner's sweeps, 2026-11-22).
                lineHeightMode: Text.FixedHeight
                lineHeight: Math.round(font.pixelSize * 1.45)
                color: EaStyle.Colors.themeForeground
                text: preview.unbroken(preview.model.description ?? "")
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
                model: preview.shown("analysis") ? (preview.model.analysis_categories ?? []) : []
                delegate: Loader {
                    id: analysisSlot
                    required property var modelData
                    required property int index
                    width: parent ? parent.width : 0
                    asynchronous: true
                    sourceComponent: CategoryBlock {
                        category: analysisSlot.modelData
                        level: 3
                        under: analysisSlot.index === 0 ? 2 : 0
                    }
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
            // One chart per parameter the Evolution tab lists, in its order, as the HTML report draws them: one to a row,
            // the column's width, with the app's proportions, each in the border every figure has (the owner, 2026-11-24).
            // Placed by bindings rather than a Column, so the charts follow a width change at once, not at the next layout
            // pass.
            Item {
                id: evolutionCharts

                readonly property real spacing: EaStyle.Sizes.fontPixelSize
                readonly property real chartWidth: width
                readonly property real chartHeight: Math.round(chartWidth * preview.evolutionAspect)
                readonly property int rows: evolutionRecords.count

                width: parent.width
                height: rows > 0 ? rows * chartHeight + (rows - 1) * spacing : 0
                transform: Translate {
                    y: preview.pixelShift(evolutionCharts)
                }

                Repeater {
                    id: evolutionRecords

                    model: preview.shown("evolution") ? (preview.model.evolution ?? []) : []
                    // Each chart made a slice at a time, as the categories are: a scan's charts made at once held the
                    // Report page's first show for about 0.4 s (the owner, 2026-11-23).
                    delegate: Loader {
                        id: evolutionSlot
                        required property var modelData
                        required property int index
                        // What a PDF's print copy of the chart is made from (reportGrabFigures): read from the record,
                        // so a save never waits for the chart itself to be made.
                        readonly property var reportSeries: modelData

                        y: index * (evolutionCharts.chartHeight + evolutionCharts.spacing)
                        width: evolutionCharts.chartWidth
                        height: evolutionCharts.chartHeight
                        asynchronous: true
                        Rectangle {
                            z: 1
                            anchors.fill: parent
                            color: "transparent"
                            border.width: EaStyle.Sizes.borderThickness
                            border.color: EaStyle.Colors.appBorder
                        }
                        sourceComponent: EvolutionChart {
                            objectName: "report.evolution"
                            width: evolutionSlot.width
                            height: evolutionSlot.height
                            reportSeries: evolutionSlot.reportSeries
                            reportStyles: preview.model.pattern_styles ?? []
                            colors: FigureColors {
                                light: true
                            }
                        }
                    }
                }
            }
        }
    }
}
