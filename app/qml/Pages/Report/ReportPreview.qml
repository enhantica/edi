// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Report page's live preview (edi ADR-0035): the report model's sections, in its order, drawn from the model's
// JSON values only. Charts and the structure view join as the model carries them.
Flickable {
    id: preview

    property ReportViewModel report: null
    readonly property var model: report ? report.model : ({})
    readonly property var sections: model.sections ?? []
    readonly property real em: EaStyle.Sizes.fontPixelSize

    function shown(name) {
        return sections.indexOf(name) >= 0;
    }

    contentHeight: column.implicitHeight + 2 * AppSizes.reportPadding
    clip: true
    ScrollBar.vertical: EaElements.ScrollBar {
        policy: ScrollBar.AsNeeded
    }

    component Heading: EaElements.Label {
        property int level: 1
        topPadding: level === 1 ? preview.em : preview.em * 0.5
        font.pixelSize: level === 1 ? preview.em * 1.5 : preview.em * 1.15
        font.bold: true
    }

    Column {
        id: column

        x: AppSizes.reportPadding
        y: AppSizes.reportPadding
        width: preview.width - 2 * AppSizes.reportPadding
        spacing: preview.em * 0.6

        EaElements.Label {
            objectName: "report.preview.title"
            width: parent.width
            wrapMode: Text.Wrap
            font.pixelSize: preview.em * 2
            text: preview.model.title ?? ""
        }
        EaElements.Label {
            visible: text !== ""
            color: EaStyle.Colors.themeForegroundMinor
            text: preview.model.authors ?? ""
        }

        // Project summary
        Heading {
            visible: preview.shown("summary")
            text: qsTr("Project summary")
        }
        EaElements.Label {
            visible: preview.shown("summary") && text !== ""
            width: parent.width
            wrapMode: Text.Wrap
            text: preview.model.description ?? ""
        }
        ReportRows {
            visible: preview.shown("summary")
            entries: [
                {
                    "label": qsTr("Short name"),
                    "text": preview.model.name ?? "",
                    "units": ""
                },
                {
                    "label": qsTr("Structures"),
                    "text": (preview.model.structure_ids ?? []).join(", "),
                    "units": ""
                },
                {
                    "label": qsTr("Experiments"),
                    "text": (preview.model.experiment_ids ?? []).join(", "),
                    "units": ""
                },
                {
                    "label": qsTr("Generated"),
                    "text": preview.model.generated ?? "",
                    "units": ""
                }
            ]
        }

        // Analysis
        Heading {
            visible: preview.shown("analysis")
            text: qsTr("Analysis")
        }
        ReportRows {
            visible: preview.shown("analysis")
            entries: (preview.model.software ?? []).concat([
                {
                    "label": qsTr("Fitting mode"),
                    "text": preview.model.fitting_mode ?? "",
                    "units": ""
                }
            ])
        }
        Heading {
            visible: preview.shown("analysis")
            level: 2
            text: qsTr("Fit result")
        }
        EaElements.Label {
            visible: preview.shown("analysis") && !preview.model.fitted
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("Not fitted yet")
        }
        ReportRows {
            visible: preview.shown("analysis") && preview.model.fitted === true
            entries: preview.model.fit_result ?? []
        }

        // Parameters
        Heading {
            visible: preview.shown("parameters")
            level: 2
            text: qsTr("Parameters")
        }
        ReportTable {
            visible: preview.shown("parameters") && rows.length > 0
            content: ({
                    "columns": [qsTr("Parameter"), qsTr("Name"), qsTr("Value"), qsTr("Units"), qsTr("Free")],
                    "rows": (preview.model.parameters ?? []).map(p => [p.name, p.label, p.value.text, p.units, p.free ? "✓" : ""])
                })
        }

        // Correlations
        Heading {
            visible: preview.shown("correlations")
            level: 2
            text: qsTr("Correlations")
        }
        ReportCorrelations {
            visible: preview.shown("correlations")
            correlations: preview.model.correlations ?? null
        }

        // Structures
        Heading {
            visible: preview.shown("structures")
            text: qsTr("Structures")
        }
        Repeater {
            model: preview.shown("structures") ? (preview.model.structures ?? []) : []
            delegate: Column {
                id: structure
                required property var modelData
                spacing: preview.em * 0.6
                Heading {
                    level: 2
                    text: structure.modelData.id
                }
                ReportRows {
                    entries: structure.modelData.space_group.concat(structure.modelData.cell)
                }
                ReportTable {
                    content: structure.modelData.atom_sites
                }
                ReportTable {
                    content: structure.modelData.aniso
                }
            }
        }

        // Experiments
        Heading {
            visible: preview.shown("experiments")
            text: qsTr("Experiments")
        }
        Repeater {
            model: preview.shown("experiments") ? (preview.model.experiments ?? []) : []
            delegate: Column {
                id: experiment
                required property var modelData
                spacing: preview.em * 0.6
                Heading {
                    level: 2
                    text: experiment.modelData.id
                }
                ReportRows {
                    entries: experiment.modelData.type
                }
                Heading {
                    level: 2
                    text: qsTr("Instrument")
                }
                ReportRows {
                    entries: experiment.modelData.instrument
                }
                Heading {
                    level: 2
                    text: qsTr("Peak profile")
                }
                ReportRows {
                    entries: experiment.modelData.peak
                }
                Heading {
                    level: 2
                    text: qsTr("Background")
                }
                ReportTable {
                    content: experiment.modelData.background
                }
                ReportTable {
                    content: experiment.modelData.excluded_regions
                }
                ReportTable {
                    content: experiment.modelData.linked_structures
                }
            }
        }
    }
}
