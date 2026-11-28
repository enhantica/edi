// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `linked_structure` (easydiffractionbeta's Associated phases): the structures (phases) this experiment's
// pattern sums, each with its scale. A loop in `.edi`, so a table. As easydiffractionbeta's Associated phases,
// each row shows the structure's icon in that structure's colour before its name (edi ADR-0017 §8). The name
// is picked from the project's structures; a row can be added for a structure not yet linked, removed while
// another remains, and switched off: a disabled row is kept and saved but neither calculated nor fitted.
// The weight fraction beside the scale is derived from the scales (Hill-Howard) and cannot be edited; a single
// enabled structure shows 1. A Le Bail or Pawley structure (edi ADR-0109) has no fitted scale and no amount, so its
// scale cannot be freed and every weight fraction of the experiment shows "—".
Column {
    id: group

    property ExperimentViewModel experiment: null
    property ProjectViewModel project: null
    readonly property LinkedStructureListModel rows: experiment ? experiment.linkedStructures : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        objectName: "linkedStructure.list"
        defaultInfoText: qsTr("No linked structure yet")
        sourceModel: group.rows

        // Widths from column types, not rows (ADR-0103 rule 4): the structure is a short id in a combo box (its arrow
        // beside it), scale and weight fraction numbers; the rest of the row is left empty, so the remove button always
        // shows (the owner, 2026-11-21).
        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "mark", "name", "value", "number", "control", "control"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "linked_structure.structure_id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "linked_structure.scale"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "linked_structure.weight_fraction"
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string structureId
            required property int colorIndex
            // The Hill-Howard weight fraction: `value` and `uncertainty` (0 without one), empty when there is none.
            required property var weightFraction
            // The structure is Le Bail or Pawley: its intensities are extracted, not calculated from its atoms.
            required property bool extracted
            // `scale` and `enabled` are Item properties, so these two roles are read through the model.
            required property var model

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            IconCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.color.${row.index}`
                icon: "layer-group"
                iconColor: AppColors.structure(row.colorIndex)
                toolTip: qsTr("Calculated pattern color")
            }
            // The structure, picked from the project's structures as the aliases table picks a parameter. A link to a
            // structure the project does not hold (an experiment loaded from another project) shows that name in red
            // until another is picked; nothing is calculated for the experiment meanwhile. A structure crysta cannot
            // link here (a Le Bail or Pawley one on a single crystal) is greyed in the list, its reason on hover.
            ComboCell {
                SearchableComboBox {
                    id: structureBox

                    readonly property bool missing: group.rows !== null && group.rows.structureNames.indexOf(row.structureId) < 0

                    inTable: true
                    horizontalAlignment: Text.AlignLeft
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: `linkedStructure.structureId.${row.index}`
                    enabled: row.model.enabled
                    model: group.rows ? group.rows.structureNames : []
                    currentIndex: group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1
                    displayText: row.structureId
                    foregroundColor: missing ? EaStyle.Colors.red : _foregroundColor()
                    ToolTip.text: missing ? qsTr("The project holds no structure '%1'; pick one of its structures").arg(row.structureId) : row.structureId
                    onActivated: index => {
                        const refusal = group.rows ? (group.rows.structureRefusals[index] ?? "") : "";
                        if (refusal !== "") {
                            currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1);
                            Session.reportRefusal(refusal);
                            return;
                        }
                        ApplicationInfo.scientificSelectorChanged(index, 4, () => {
                            currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1);
                        });
                    }

                    delegate: EaElements.MenuItem {
                        id: entry

                        required property int index
                        required property var modelData
                        // By name: a typed search lists the entries in an order of its own.
                        readonly property string refusal: group.rows ? (group.rows.structureRefusals[group.rows.structureNames.indexOf(String(entry.modelData))] ?? "") : ""
                        // Whether the entry passes the search, read from the name alone (the text may carry colour).
                        readonly property bool matching: structureBox.matches(String(entry.modelData))

                        width: entry.parent !== null ? entry.parent.width : 0
                        height: matching ? EaStyle.Sizes.comboBoxHeight : 0
                        opacity: matching ? 1 : 0
                        font.family: structureBox.listFontFamily
                        textFormat: Text.RichText
                        elide: structureBox.elide
                        text: refusal === "" ? String(entry.modelData) : `<font color="${EaStyle.Colors.themeForegroundDisabled}">${entry.modelData}</font>`
                        enabled: refusal === ""
                        highlighted: structureBox.highlightedIndex === entry.index
                        hoverEnabled: structureBox.hoverEnabled

                        // Hover is reported on a disabled entry too, so the reason shows where the entry cannot be picked.
                        // The tooltip is made only while it shows.
                        HoverHandler {
                            id: entryHover
                        }
                        Loader {
                            active: entryHover.hovered && entry.refusal !== ""
                            sourceComponent: EaElements.ToolTip {
                                parent: entry
                                text: entry.refusal
                                requested: entryHover.hovered
                            }
                        }
                    }
                }
            }
            // Numbers right-aligned under their right-aligned headers (ADR-0029; the owner, 2026-11-21). A Le Bail or
            // Pawley structure's scale is kept but not fitted: crysta marks it not fittable, the cell draws it fixed with
            // its Free box disabled, free flag or not, and says why with crysta's reason (edi ADR-0053, ADR-0109).
            ParameterCell {
                columnAlignment: Text.AlignRight
                objectName: `linkedStructure.scale.${row.index}`
                enabled: row.model.enabled && refinable
                item: row.model.scale
                fitBlocked: row.extracted && item !== null && !item.fittable
                helpToolTip: fitBlocked
                ToolTip.text: helpToolTip ? qsTr("Cannot be fitted: %1").arg(item.fitReason) : ""
            }
            // Derived from the scales: the dictionary's weight fraction, rounded by its s.u. under the project's rule, else
            // by its display format; never edited or fitted. "—" for every link while a Le Bail or Pawley structure is
            // linked: its amount is unknown, so crysta gives no fraction.
            DerivedCell {
                readonly property bool known: row.weightFraction !== undefined && row.weightFraction.value !== undefined
                readonly property real fractionValue: known ? row.weightFraction.value : 0
                readonly property real fractionError: known ? row.weightFraction.uncertainty : 0
                readonly property bool extracting: !known && group.rows !== null && group.rows.extracting

                objectName: `linkedStructure.weightFraction.${row.index}`
                enabled: row.model.enabled
                shownValue: known ? Session.valueText("linked_structure.weight_fraction", fractionValue, fractionError) : extracting ? "—" : ""
                fullValue: known ? NumberText.plainFull(fractionValue) : ""
                uncertainty: known ? Session.suText("linked_structure.weight_fraction", fractionValue, fractionError) : ""
                uid: "linked_structure.weight_fraction"
                derivedName: row.model.scale ? row.model.scale.fullName.slice(0, row.model.scale.fullName.lastIndexOf(".") + 1) + "weight_fraction" : ""
                color: EaStyle.Colors.themeForegroundMinor
                ToolTip.text: extracting ? qsTr("No weight fraction: a linked structure's intensities are extracted (Le Bail or Pawley), so its amount is unknown") : Session.tooltip("linked_structure.weight_fraction")
            }
            // Disabled as a constraint is: kept and saved, but neither calculated nor fitted.
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.enabled.${row.index}`
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.enabled ? qsTr("Disable this linked structure") : qsTr("Enable this linked structure")
                onClicked: group.rows.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.remove.${row.index}`
                enabled: group.rows !== null && group.rows.canRemove
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this linked structure")
                onClicked: group.rows.remove(row.index)
            }
        }
    }

    // Add linked structure, and Estimate: the phase scales brought to the measured peak heights again, one undo step
    // (the owner, 2026-11-17), placed and styled as the Background group's. Two at equal widths.
    Row {
        id: linkButtons

        readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - spacing) / 2
        readonly property bool measured: group.experiment !== null && !group.experiment.calculationOnly

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "linkedStructure.append"
            width: linkButtons.buttonWidth
            enabled: group.rows !== null && group.rows.canAppend
            fontIcon: "plus-circle"
            text: qsTr("Add linked structure")
            ToolTip.text: enabled ? "" : qsTr("Every structure of the project is linked already: create or load another on the Structure page")
            onClicked: group.rows.append()
        }
        // A disabled button takes no hover, so its tooltip, which then says why, hangs on the item around it.
        Item {
            width: linkButtons.buttonWidth
            implicitHeight: estimateScale.implicitHeight

            EaElements.SideBarButton {
                id: estimateScale

                objectName: "linkedStructure.estimate"
                width: parent.width
                enabled: group.rows !== null && linkButtons.measured
                fontIcon: "magic"
                text: qsTr("Estimate")
                ToolTip.text: linkButtons.measured ? qsTr("Scale the linked structures to the measured peak heights") : qsTr("Estimate needs measured data: load data into this experiment first")
                onClicked: group.rows.estimateScale()
            }
        }
    }

    // "Phase ratios shared" (edi ADR-0087, #36): the other experiments of this one's set keep their own overall scale
    // and follow its ratios between the phases, through alias and constraint rows. Shown with several experiments and
    // several linked structures; a refusal (every scale zero, members linking other structures) says why.
    EaElements.CheckBox {
        id: phaseRatios

        // Read again whenever the relation rows change.
        readonly property int relations: group.project && group.project.analysis ? group.project.analysis.constraints.count + group.project.analysis.aliases.count : 0
        readonly property int index: group.project ? group.project.currentExperimentIndex : -1

        objectName: "linkedStructure.phaseRatiosShared"
        visible: group.project !== null && group.project.experiments.count > 1 && group.rows !== null && group.rows.count > 1
        text: qsTr("Phase ratios shared")
        checked: relations >= 0 && index >= 0 && group.project.phaseRatiosShared(index)
        ToolTip.text: qsTr("The set's other experiments keep their own overall scale and follow this experiment's ratios between the phases")
        onToggled: {
            const wanted = checked;
            group.project.setPhaseRatiosShared(index, wanted);
            checked = Qt.binding(() => relations >= 0 && index >= 0 && group.project.phaseRatiosShared(index));
        }
    }
}
