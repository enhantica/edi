// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `background`: the type selector over the
// core's supported types, then that type's content — for `line-segment` the point list (position,
// intensity), with append and remove, and a reset to the autodetected background (disabled); for `polynomial`
// its origin and for `chebyshev` its domain, then the term list (order, coefficient), with append and remove.
// Another type replaces the background, as diffraction-lib's does: the new type starts empty, so a background that
// holds rows asks first.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property BackgroundListModel points: experiment ? experiment.background : null
    readonly property BackgroundTermListModel terms: experiment ? experiment.backgroundTerms : null
    // A background type's content by token: a new type needs only its layout here.
    readonly property var layouts: ({
            "line-segment": lineSegmentLayout,
            "polynomial": polynomialLayout,
            "chebyshev": chebyshevLayout
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

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        SelectorField {
            id: typeSelector
            objectName: "background.type"
            label: qsTr("type")
            options: group.experiment ? group.experiment.backgroundTypeOptions : null
            token: group.experiment ? group.experiment.backgroundType : ""
            onSelected: token => group.chooseType(token)
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
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("id")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("position")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("intensity")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                delegate: EaComponents.ListViewDelegate {
                    id: row

                    required property int index
                    required property var model
                    required property real position
                    required property ParameterItem intensity

                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        color: EaStyle.Colors.themeForegroundMinor
                        text: row.index + 1
                    }
                    TextCell {
                        horizontalAlignment: Text.AlignLeft
                        objectName: `background.id.${row.index}`
                        value: row.model.id
                        onCommitted: text => group.points.setId(row.index, text)
                    }
                    TextCell {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.position.${row.index}`
                        value: row.position
                        accepts: "number"
                        onCommitted: text => group.points.setPosition(row.index, Number(text))
                    }
                    ParameterCell {
                        columnAlignment: Text.AlignHCenter
                        objectName: `background.intensity.${row.index}`
                        item: row.intensity
                    }
                    EaComponents.TableViewButton {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.remove.${row.index}`
                        fontIcon: "minus-circle"
                        ToolTip.text: qsTr("Remove this background point")
                        onClicked: group.points.remove(row.index)
                    }
                }
            }

            // Append, and reset to the autodetected background — not implemented yet, so disabled (edi
            // ADR-0017 §4).
            Row {
                spacing: EaStyle.Sizes.fontPixelSize

                EaElements.SideBarButton {
                    objectName: "background.append"
                    fontIcon: "plus-circle"
                    text: qsTr("Append new point")
                    onClicked: group.points.append()
                }
                EaElements.SideBarButton {
                    objectName: "background.autodetect"
                    enabled: false
                    fontIcon: "undo-alt"
                    text: qsTr("Reset to autodetected background")
                }
            }
        }
    }
    Component {
        id: polynomialLayout

        Column {
            spacing: AppSizes.groupContentSpacing

            EaElements.GroupRow {
                spacing: AppSizes.inputSpacing
                ValueField {
                    objectName: "background.origin"
                    label: qsTr("origin")
                    accepts: "number"
                    fieldValue: group.experiment ? group.experiment.backgroundOrigin : ""
                    onCommitted: text => group.experiment.backgroundOrigin = Number(text)
                }
            }
            Loader {
                sourceComponent: termsTable
            }
        }
    }

    Component {
        id: chebyshevLayout

        Column {
            spacing: AppSizes.groupContentSpacing

            EaElements.GroupRow {
                spacing: AppSizes.inputSpacing
                ValueField {
                    objectName: "background.xMin"
                    label: qsTr("x min")
                    accepts: "number"
                    fieldValue: group.experiment ? group.experiment.backgroundXMin : ""
                    onCommitted: text => group.experiment.backgroundXMin = Number(text)
                }
                ValueField {
                    objectName: "background.xMax"
                    label: qsTr("x max")
                    accepts: "number"
                    fieldValue: group.experiment ? group.experiment.backgroundXMax : ""
                    onCommitted: text => group.experiment.backgroundXMax = Number(text)
                }
            }
            Loader {
                sourceComponent: termsTable
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

                columnWidths: [numberColumnWidth, Math.min(textColumnWidth("order", qsTr("order")), width * 0.25), -1, AppSizes.iconColumnWidth]

                header: EaComponents.ListViewHeader {
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("order")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("coefficient")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                delegate: EaComponents.ListViewDelegate {
                    id: termRow

                    required property int index
                    required property int order
                    required property ParameterItem coef

                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        color: EaStyle.Colors.themeForegroundMinor
                        text: termRow.index + 1
                    }
                    TextCell {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.order.${termRow.index}`
                        value: termRow.order
                        accepts: "integer"
                        onCommitted: text => group.terms.setOrder(termRow.index, Number(text))
                    }
                    ParameterCell {
                        columnAlignment: Text.AlignHCenter
                        objectName: `background.coef.${termRow.index}`
                        item: termRow.coef
                    }
                    EaComponents.TableViewButton {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.removeTerm.${termRow.index}`
                        fontIcon: "minus-circle"
                        ToolTip.text: qsTr("Remove this background term")
                        onClicked: group.terms.remove(termRow.index)
                    }
                }
            }

            EaElements.SideBarButton {
                objectName: "background.appendTerm"
                fontIcon: "plus-circle"
                text: qsTr("Append new term")
                onClicked: group.terms.append()
            }
        }
    }
}
