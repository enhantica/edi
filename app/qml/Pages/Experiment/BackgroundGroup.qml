// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `background`: one line with the type selector over the core's supported types, the manual/auto choice of the
// estimate and, for `polynomial`, its origin or, for `chebyshev`, its domain; then that type's table — for
// `line-segment` the point list (id, position, intensity), for the others the term list (id, order, coefficient),
// each with append and remove. Every type has Estimate, from the measured pattern with the settings in Extras
// (BackgroundExtrasGroup, ADR-0040).
// Another type replaces the background, as diffraction-lib's does: the new type starts empty, so a background that
// holds rows asks first.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property BackgroundListModel points: experiment ? experiment.background : null
    readonly property BackgroundTermListModel terms: experiment ? experiment.backgroundTerms : null
    // In auto estimation mode the estimate owns the points or terms: the table stays scrollable but reads only,
    // and the buttons below it are disabled until the mode is manual (the owner, 2026-10-20).
    readonly property bool automatic: experiment !== null && experiment.backgroundEstimateMode === "auto"
    // A background type's content by token: a new type needs only its layout here.
    readonly property var layouts: ({
            "line-segment": lineSegmentLayout,
            "polynomial": termsTable,
            "chebyshev": termsTable
        })

    // The type a choice names, applied now when nothing would be removed, else after the question.
    function chooseType(token: string) {
        const rows = experiment.backgroundType === "line-segment" ? (points ? points.count : 0) : (terms ? terms.count : 0);
        if (rows === 0) {
            experiment.backgroundType = token;
            return;
        }
        typeQuestion.token = token;
        typeQuestion.rows = rows;
        typeQuestion.open();
    }

    spacing: AppSizes.groupContentSpacing

    // One line above the table (the owner, 2026-10-20): the type and the estimation mode, then a polynomial's origin
    // or a Chebyshev series' domain, all of one width.
    EaElements.GroupRow {
        id: settingsRow

        readonly property string kind: group.experiment ? group.experiment.backgroundType : ""
        readonly property int fields: kind === "chebyshev" ? 4 : kind === "polynomial" ? 3 : 2
        readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - (fields - 1) * spacing) / fields

        spacing: AppSizes.inputSpacing
        SelectorField {
            id: typeSelector
            width: settingsRow.fieldWidth
            objectName: "background.type"
            label: qsTr("type")
            options: group.experiment ? group.experiment.backgroundTypeOptions : null
            token: group.experiment ? group.experiment.backgroundType : ""
            onSelected: token => group.chooseType(token)
        }
        // Manual keeps the points or terms as they are and lets them be edited; auto re-estimates them when the data
        // or the estimate settings change, and keeps them from hand edits (ADR-0040).
        SelectorField {
            objectName: "background_estimate.mode"
            width: settingsRow.fieldWidth
            label: qsTr("estimation mode")
            options: group.experiment ? group.experiment.backgroundEstimateModes : null
            token: group.experiment ? group.experiment.backgroundEstimateMode : ""
            onSelected: token => group.experiment.backgroundEstimateMode = token
            ToolTip.visible: hovered && EaGlobals.Vars.showToolTips && refusal === ""
            ToolTip.text: qsTr("Manual: the background is yours to edit, and Estimate replaces it when you ask. Auto: the background is estimated again whenever the measured data or the settings in Extra change, so the table only shows it; choose manual to edit it.")
        }
        ValueField {
            objectName: "background.origin"
            visible: settingsRow.kind === "polynomial"
            width: settingsRow.fieldWidth
            label: qsTr("origin")
            accepts: "number"
            fieldValue: group.experiment ? group.experiment.backgroundOrigin : ""
            onCommitted: text => group.experiment.backgroundOrigin = Number(text)
        }
        ValueField {
            objectName: "background.xMin"
            visible: settingsRow.kind === "chebyshev"
            width: settingsRow.fieldWidth
            label: qsTr("x min")
            accepts: "number"
            fieldValue: group.experiment ? group.experiment.backgroundXMin : ""
            onCommitted: text => group.experiment.backgroundXMin = Number(text)
        }
        ValueField {
            objectName: "background.xMax"
            visible: settingsRow.kind === "chebyshev"
            width: settingsRow.fieldWidth
            label: qsTr("x max")
            accepts: "number"
            fieldValue: group.experiment ? group.experiment.backgroundXMax : ""
            onCommitted: text => group.experiment.backgroundXMax = Number(text)
        }
    }

    AppDialog {
        id: typeQuestion

        property string token: ""
        property int rows: 0

        objectName: "background.typeQuestion"
        parent: Overlay.overlay
        title: qsTr("Change the background type?")
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentWidth: AppSizes.messagesDialogContentWidth
        contentHeight: typeQuestionText.implicitHeight

        EaElements.Label {
            id: typeQuestionText
            width: typeQuestion.contentWidth
            wrapMode: Text.Wrap
            text: !group.experiment ? "" : group.experiment.backgroundType === "line-segment" ? qsTr("A %1 background starts empty: the %2 background points are removed.").arg(typeQuestion.token).arg(typeQuestion.rows) : qsTr("A %1 background starts empty: the %2 %3 terms and their constants are removed.").arg(typeQuestion.token).arg(typeQuestion.rows).arg(group.experiment.backgroundType)
        }
        onAccepted: group.experiment.backgroundType = token
    }

    Loader {
        sourceComponent: group.experiment ? group.layouts[group.experiment.backgroundType] ?? null : null
    }

    Component {
        id: lineSegmentLayout

        Column {
            spacing: AppSizes.groupContentSpacing

            DataTable {
                objectName: "background.list"
                // At most four rows, then it scrolls (the owner, 2026-10-04; edi ADR-0017 §3).
                maxRowCountShow: 4
                defaultInfoText: qsTr("No background points")
                sourceModel: group.points

                columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", qsTr("id")), width * 0.25), -1, -1, AppSizes.iconColumnWidth]

                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("id")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("position")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("intensity")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                delegate: TableRow {
                    id: row

                    required property var model
                    required property real position
                    required property ParameterItem intensity

                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: row.index + 1
                    }
                    TextCell {
                        locked: group.automatic
                        horizontalAlignment: Text.AlignLeft
                        objectName: `background.id.${row.index}`
                        value: row.model.id
                        onCommitted: text => group.points.setId(row.index, text)
                    }
                    TextCell {
                        locked: group.automatic
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.position.${row.index}`
                        value: row.position
                        accepts: "number"
                        onCommitted: text => group.points.setPosition(row.index, Number(text))
                    }
                    ParameterCell {
                        locked: group.automatic
                        columnAlignment: Text.AlignHCenter
                        objectName: `background.intensity.${row.index}`
                        item: row.intensity
                    }
                    EaComponents.ListViewButton {
                        enabled: !group.automatic
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.remove.${row.index}`
                        fontIcon: "minus-circle"
                        ToolTip.text: qsTr("Remove this background point")
                        onClicked: group.points.remove(row.index)
                    }
                }
            }

            // Append; name every point by its position, rounded as strongly as keeps the names apart (the owner,
            // 2026-10-11); and Estimate, the points from the measured pattern (edi ADR-0040). Three at equal widths.
            Row {
                id: pointButtons

                readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

                spacing: EaStyle.Sizes.fontPixelSize

                EaElements.SideBarButton {
                    objectName: "background.append"
                    width: pointButtons.buttonWidth
                    fontIcon: "plus-circle"
                    text: qsTr("Add point")
                    ToolTip.text: qsTr("Append new point")
                    enabled: !group.automatic
                    onClicked: group.points.append()
                }
                EaElements.SideBarButton {
                    objectName: "background.namePoints"
                    width: pointButtons.buttonWidth
                    enabled: !group.automatic && Session.project !== null && group.points !== null && group.points.count > 0
                    fontIcon: "tag"
                    text: qsTr("Id from position")
                    ToolTip.text: qsTr("Name points by position: each point takes its position, rounded, as its name")
                    onClicked: Session.project.namePointsByPosition()
                }
                EaElements.SideBarButton {
                    objectName: "background.estimate"
                    width: pointButtons.buttonWidth
                    enabled: group.experiment !== null && !group.automatic
                    fontIcon: "magic"
                    text: qsTr("Estimate")
                    ToolTip.text: qsTr("Estimate the points from the measured pattern, with the settings in Extras")
                    onClicked: Session.project.estimateBackground()
                }
            }
        }
    }
    // A polynomial's or Chebyshev series' terms, as the line-segment points: the order editable, the coefficient
    // a parameter, a row removed by its button, a term appended at the lowest order not held.
    Component {
        id: termsTable

        Column {
            spacing: AppSizes.groupContentSpacing

            DataTable {
                objectName: "background.terms"
                // At most four rows, then it scrolls, as the points (edi ADR-0017 §3).
                maxRowCountShow: 4
                defaultInfoText: qsTr("No background terms")
                sourceModel: group.terms

                columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", qsTr("id")), width * 0.25), Math.min(textColumnWidth("order", qsTr("order")), width * 0.25), -1, AppSizes.iconColumnWidth]

                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("id")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("order")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("coefficient")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                delegate: TableRow {
                    id: termRow

                    required property var model
                    required property int order
                    required property ParameterItem coef

                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: termRow.index + 1
                    }
                    TextCell {
                        locked: group.automatic
                        horizontalAlignment: Text.AlignLeft
                        objectName: `background.termId.${termRow.index}`
                        value: termRow.model.id
                        onCommitted: text => group.terms.setId(termRow.index, text)
                    }
                    TextCell {
                        locked: group.automatic
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.order.${termRow.index}`
                        value: termRow.order
                        accepts: "integer"
                        onCommitted: text => group.terms.setOrder(termRow.index, Number(text))
                    }
                    ParameterCell {
                        locked: group.automatic
                        columnAlignment: Text.AlignHCenter
                        objectName: `background.coef.${termRow.index}`
                        item: termRow.coef
                    }
                    EaComponents.ListViewButton {
                        enabled: !group.automatic
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.removeTerm.${termRow.index}`
                        fontIcon: "minus-circle"
                        ToolTip.text: qsTr("Remove this background term")
                        onClicked: group.terms.remove(termRow.index)
                    }
                }
            }

            // Append; name every term by its order, as the points by their position; and Estimate the terms from the
            // measured pattern (edi ADR-0040). Three at equal widths, together as wide as the table, as the
            // line-segment points' buttons are (owner, 2026-10-11).
            Row {
                id: termButtons

                readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

                spacing: EaStyle.Sizes.fontPixelSize

                EaElements.SideBarButton {
                    objectName: "background.appendTerm"
                    width: termButtons.buttonWidth
                    fontIcon: "plus-circle"
                    text: qsTr("Add term")
                    ToolTip.text: qsTr("Append new term")
                    enabled: !group.automatic
                    onClicked: group.terms.append()
                }
                EaElements.SideBarButton {
                    objectName: "background.nameTerms"
                    width: termButtons.buttonWidth
                    enabled: !group.automatic && Session.project !== null && group.terms !== null && group.terms.count > 0
                    fontIcon: "tag"
                    text: qsTr("Id from order")
                    ToolTip.text: qsTr("Name terms by order: each term takes its order as its name")
                    onClicked: Session.project.nameTermsByOrder()
                }
                EaElements.SideBarButton {
                    objectName: "background.estimate"
                    width: termButtons.buttonWidth
                    enabled: group.experiment !== null && !group.automatic
                    fontIcon: "magic"
                    text: qsTr("Estimate")
                    ToolTip.text: qsTr("Estimate the terms from the measured pattern, with the settings in Extras")
                    onClicked: Session.project.estimateBackground()
                }
            }
        }
    }
}
