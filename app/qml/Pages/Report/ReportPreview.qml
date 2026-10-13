// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Report page's live preview (edi ADR-0035): the report model's sections, in its order, drawn from the model's
// JSON values only. It is set as the HTML report is, after the owner's reference report (diffraction-lib's style,
// 2026-10-13): PT Sans headings at its sizes and margins, numbered sections and records, bordered tables one line per
// row, in the app's theme colours. Charts and the structure view join as the model carries them.
Flickable {
    id: preview

    property ReportViewModel report: null
    readonly property var model: report ? report.model : ({})
    readonly property var sections: model.sections ?? []
    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The reference's sizes and margins are in points over its 10.04 pt body.
    readonly property real pt: em / 10.04
    readonly property bool analysisShown: ["analysis", "parameters", "correlations", "evolution"].some(name => shown(name))
    // The numbered sections shown, in order.
    readonly property var numbered: [shown("summary") ? "summary" : "", analysisShown ? "analysis" : "", shown("structures") ? "structures" : "", shown("experiments") ? "experiments" : ""].filter(name => name !== "")

    function shown(name) {
        return sections.indexOf(name) >= 0;
    }
    function number(section) {
        return numbered.indexOf(section) + 1;
    }
    // A key-value table's rows from the model's rows, each value followed by its units.
    function keyValues(rows) {
        return (rows ?? []).map(row => [row.label, row.units ? row.text + " " + row.units : row.text]);
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

        // 1. Project summary
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

        // 2. Analysis, with the parameters, the correlations and the evolution in it
        Column {
            width: parent.width
            visible: preview.analysisShown
            Heading {
                text: `${preview.number("analysis")}.  ` + qsTr("Analysis")
            }
            Column {
                width: parent.width
                visible: preview.shown("analysis")
                Heading {
                    level: 3
                    under: 2
                    text: qsTr("Software")
                }
                ReportTable {
                    rows: preview.keyValues(preview.model.software)
                }
                Heading {
                    level: 3
                    text: qsTr("Fitting mode")
                }
                ReportTable {
                    rows: [[qsTr("Mode"), preview.model.fitting_mode ?? ""]]
                }
                Heading {
                    level: 3
                    text: qsTr("Fit result")
                }
                EaElements.Label {
                    visible: !preview.model.fitted
                    color: EaStyle.Colors.themeForegroundMinor
                    text: qsTr("Not fitted yet")
                }
                ReportTable {
                    visible: preview.model.fitted === true
                    rows: preview.keyValues(preview.model.fit_result)
                }
            }
            Column {
                width: parent.width
                visible: preview.shown("parameters")
                Heading {
                    level: 3
                    under: preview.shown("analysis") ? 0 : 2
                    text: qsTr("Parameters")
                }
                ReportTable {
                    columns: [qsTr("Parameter"), qsTr("Name"), qsTr("Value"), qsTr("Units"), qsTr("Free")]
                    rows: (preview.model.parameters ?? []).map(p => [p.name, p.label, p.value.text, p.units, p.free ? "✓" : ""])
                }
            }
            Column {
                width: parent.width
                visible: preview.shown("correlations")
                Heading {
                    level: 3
                    under: preview.shown("analysis") || preview.shown("parameters") ? 0 : 2
                    text: qsTr("Correlations")
                }
                ReportCorrelations {
                    correlations: preview.model.correlations ?? null
                }
            }
        }

        // 3. Structures, one record each
        Column {
            width: parent.width
            visible: preview.shown("structures")
            Heading {
                text: `${preview.number("structures")}.  ` + qsTr("Structures")
            }
            Repeater {
                model: preview.shown("structures") ? (preview.model.structures ?? []) : []
                delegate: Column {
                    id: structure
                    required property var modelData
                    required property int index
                    width: parent.width
                    Heading {
                        level: 3
                        under: structure.index === 0 ? 2 : 0
                        text: `${preview.number("structures")}.${structure.index + 1}.  ${structure.modelData.id}`
                    }
                    Heading {
                        level: 4
                        under: 3
                        text: qsTr("Space group")
                    }
                    ReportTable {
                        rows: preview.keyValues(structure.modelData.space_group)
                    }
                    Heading {
                        level: 4
                        text: qsTr("Cell")
                    }
                    ReportTable {
                        rows: preview.keyValues(structure.modelData.cell)
                    }
                    Heading {
                        level: 4
                        text: qsTr("Atom sites")
                    }
                    ReportTable {
                        columns: structure.modelData.atom_sites.columns
                        rows: structure.modelData.atom_sites.rows
                    }
                    Heading {
                        visible: structure.modelData.aniso.rows.length > 0
                        level: 4
                        text: qsTr("Anisotropic displacement")
                    }
                    ReportTable {
                        columns: structure.modelData.aniso.columns
                        rows: structure.modelData.aniso.rows
                    }
                }
            }
        }

        // 4. Experiments, one record each
        Column {
            width: parent.width
            visible: preview.shown("experiments")
            Heading {
                text: `${preview.number("experiments")}.  ` + qsTr("Experiments")
            }
            Repeater {
                model: preview.shown("experiments") ? (preview.model.experiments ?? []) : []
                delegate: Column {
                    id: experiment
                    required property var modelData
                    required property int index
                    width: parent.width
                    Heading {
                        level: 3
                        under: experiment.index === 0 ? 2 : 0
                        text: `${preview.number("experiments")}.${experiment.index + 1}.  ${experiment.modelData.id}`
                    }
                    Heading {
                        level: 4
                        under: 3
                        text: qsTr("Experiment type")
                    }
                    ReportTable {
                        rows: preview.keyValues(experiment.modelData.type)
                    }
                    Heading {
                        level: 4
                        text: qsTr("Instrument")
                    }
                    ReportTable {
                        rows: preview.keyValues(experiment.modelData.instrument)
                    }
                    Heading {
                        level: 4
                        text: qsTr("Peak profile")
                    }
                    ReportTable {
                        rows: preview.keyValues(experiment.modelData.peak)
                    }
                    Heading {
                        level: 4
                        text: qsTr("Background")
                    }
                    ReportTable {
                        columns: experiment.modelData.background.columns
                        rows: experiment.modelData.background.rows
                    }
                    Heading {
                        visible: experiment.modelData.excluded_regions.rows.length > 0
                        level: 4
                        text: qsTr("Excluded regions")
                    }
                    ReportTable {
                        columns: experiment.modelData.excluded_regions.columns
                        rows: experiment.modelData.excluded_regions.rows
                    }
                    Heading {
                        visible: experiment.modelData.linked_structures.rows.length > 0
                        level: 4
                        text: qsTr("Linked structures")
                    }
                    ReportTable {
                        columns: experiment.modelData.linked_structures.columns
                        rows: experiment.modelData.linked_structures.rows
                    }
                }
            }
        }
    }
}
