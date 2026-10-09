// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import edi.app

// The app's curated example catalogue (ADR-0030). Filtering never changes an example's identity.
EaElements.GroupBox {
    id: group
    objectName: "group.examples"
    title: qsTr("Examples")
    icon: "database"

    function choiceIndex(model, value) {
        for (let i = 0; i < model.count; ++i)
            if (model.text(i, "value") === value)
                return i;
        return 0;
    }

    Column {
        spacing: AppSizes.groupContentSpacing
        EaElements.GroupRow {
            EaElements.TextField {
                objectName: "examples.search"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                placeholderText: qsTr("Search examples")
                horizontalAlignment: TextInput.AlignLeft
                text: Session.examples.searchText
                onTextEdited: Session.examples.searchText = text
            }
            SearchableComboBox {
                objectName: "examples.property"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                horizontalAlignment: Text.AlignLeft
                model: Session.examples.filterProperties
                textRole: "title"
                searchThreshold: 1000
                currentIndex: group.choiceIndex(Session.examples.filterProperties, Session.examples.filterProperty)
                onActivated: index => Session.examples.filterProperty = Session.examples.filterProperties.text(index, "value")
            }
            SearchableComboBox {
                objectName: "examples.value"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                horizontalAlignment: Text.AlignLeft
                model: Session.examples.filterOptions
                textRole: "title"
                popup.width: Math.max(width, optionWidth)
                currentIndex: group.choiceIndex(Session.examples.filterOptions, Session.examples.filterValue)
                onActivated: index => Session.examples.filterValue = Session.examples.filterOptions.text(index, "value")
            }
        }
        DataTable {
            id: table
            objectName: "examples.list"
            tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * 5.5)
            maxRowCountShow: 6
            defaultInfoText: qsTr("No matching examples")
            sourceModel: Session.examples
            columnWidths: [numberColumnWidth, -1]
            header: EaComponents.ListViewHeader {
                visible: false
                implicitHeight: 0
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name / description")
                }
            }
            delegate: EaComponents.ListViewDelegate {
                id: row
                required property int index
                required property string exampleId
                required property string sample
                required property string origin
                required property string detail
                required property list<string> tagLabels
                required property list<string> tagIcons
                objectName: `examples.open.${exampleId}`
                MouseArea {
                    parent: row
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Session.openExample(row.exampleId)
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                Item {
                    id: descriptionCell
                    height: row.height
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        spacing: EaStyle.Sizes.fontPixelSize * 0.25
                        EaElements.Label {
                            id: identityLabel
                            width: parent.width
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
                            textFormat: Text.PlainText
                            // PT Sans lacks several subscript digits; one bundled face keeps formula weights uniform.
                            font.family: "Noto Sans"
                            font.bold: true
                            text: row.sample + " · " + row.origin
                        }
                        Item {
                            width: parent.width
                            height: EaStyle.Sizes.fontPixelSize * 1.65
                            clip: true
                            Row {
                                id: tagRow
                                spacing: AppSizes.fieldSpacing / 2
                                Repeater {
                                    model: row.tagLabels
                                    delegate: Rectangle {
                                        id: badge
                                        required property string modelData
                                        required property int index
                                        readonly property color ink: index === 0 ? (modelData === qsTr("Simulation") ? (EaStyle.Colors.isDarkPalette ? "#cba1eb" : "#8354a9") : (EaStyle.Colors.isDarkPalette ? "#9ac776" : "#398648")) : index === 1 ? (EaStyle.Colors.isDarkPalette ? "#e3b06d" : "#96601d") : EaStyle.Colors.themeForeground
                                        radius: 3
                                        color: Qt.rgba(ink.r, ink.g, ink.b, 0.13)
                                        width: badgeContent.implicitWidth + AppSizes.fieldSpacing
                                        height: EaStyle.Sizes.fontPixelSize * 1.65
                                        Row {
                                            id: badgeContent
                                            anchors.centerIn: parent
                                            spacing: AppSizes.fieldSpacing / 2
                                            EaElements.Label {
                                                visible: text !== ""
                                                anchors.verticalCenter: parent.verticalCenter
                                                font.family: EaStyle.Fonts.iconsFamily
                                                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.8
                                                color: badge.ink
                                                text: row.tagIcons[badge.index] ?? ""
                                            }
                                            EaElements.Label {
                                                anchors.verticalCenter: parent.verticalCenter
                                                horizontalAlignment: Text.AlignHCenter
                                                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                                                color: badge.ink
                                                text: badge.modelData
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        EaElements.Label {
                            id: detailLabel
                            width: parent.width
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
                            textFormat: Text.PlainText
                            color: EaStyle.Colors.themeForegroundMinor
                            text: row.detail
                        }
                    }
                    HoverHandler {
                        id: hover
                    }
                    EaElements.ToolTip {
                        visible: hover.hovered && EaGlobals.Vars.showToolTips && text !== ""
                        text: [identityLabel.truncated ? identityLabel.text : "", tagRow.width > descriptionCell.width ? row.tagLabels.join(" · ") : "", detailLabel.truncated ? row.detail : ""].filter(line => line !== "").join("\n")
                    }
                }
            }
        }
    }
}
