// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The project's description (easydiffractionbeta Pages/Project/MainContent/DescriptionTab.qml): the
// `metadata` category — name, title, description — then where the project is and what it holds. The
// loader's warnings are the status bar's (edi ADR-0017 §14).
Rectangle {
    id: tab

    property ProjectViewModel project: null

    color: "transparent"
    onProjectChanged: nameInput.refusal = ""

    Flickable {
        anchors.fill: parent
        contentHeight: column.height + 2 * column.y
        clip: true
        flickableDirection: Flickable.VerticalFlick
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }

        // A click on the page outside a field ends the edit in progress, so it commits as Tab and Return do and Save
        // is offered (the owner, 2026-10-13): the page takes the focus. The fields above take their own clicks.
        MouseArea {
            width: tab.width
            height: Math.max(tab.height, column.height + 2 * column.y)
            onPressed: mouse => {
                tab.forceActiveFocus();
                mouse.accepted = false;
            }
        }

        Column {
            id: column

            visible: tab.project !== null
            x: 1.5 * AppSizes.descriptionOuterSpacing
            y: AppSizes.descriptionOuterSpacing
            width: tab.width - 2 * x
            spacing: AppSizes.descriptionInnerSpacing

            EaElements.TextInput {
                id: nameInput

                // Why the last rename was refused (the library's name rule, or an empty name); empty
                // once a rename takes or the name changes.
                property string refusal: ""

                objectName: "project.name"
                // The large light text is Noto Sans Light, by its own loader's family and its style, never by
                // a weight (ADR-0015 §10).
                font.family: EaStyle.Fonts.notoSansLight.name
                font.pixelSize: AppSizes.descriptionTitleFontPixelSize
                font.styleName: "Light"
                placeholderText: qsTr("Enter project name here")
                text: tab.project ? tab.project.name : ""
                warned: refusal !== ""
                ToolTip.text: refusal
                // In the warning's style, as every refused value's.
                WarningToolTip {
                    text: nameInput.refusal
                    visible: nameInput.warned && (nameInput.hovered || nameInput.activeFocus)
                }
                onAccepted: commit()
                onEditingFinished: commit()

                Connections {
                    target: tab.project
                    function onNameChanged() {
                        nameInput.refusal = "";
                    }
                }

                // Return and leaving the field both commit; the second of the two finds nothing new. A
                // refused name returns the field to the project's name and shows why, as ParameterField does.
                function commit() {
                    if (!tab.project || text === tab.project.name)
                        return;
                    if (text === "") {
                        refusal = qsTr("A project needs a name");
                    } else {
                        tab.project.name = text;
                        refusal = tab.project.lastError;
                    }
                    text = Qt.binding(() => tab.project ? tab.project.name : "");
                }
            }

            Item {
                height: 1
                width: 1
            }

            DescriptionRow {
                label: qsTr("Title")
                EaElements.TextInput {
                    objectName: "project.title"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    placeholderText: qsTr("Enter project title here")
                    text: tab.project ? tab.project.title : ""
                    onAccepted: commit()
                    onEditingFinished: commit()

                    // Return and leaving the field both commit; the second of the two finds nothing new.
                    function commit() {
                        if (tab.project && text !== tab.project.title)
                            tab.project.title = text;
                    }
                }
            }
            // The report's authors (`_metadata.authors`), separated by "; ".
            DescriptionRow {
                label: qsTr("Authors")
                EaElements.TextInput {
                    objectName: "project.authors"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    placeholderText: qsTr("Enter authors here, separated by ;")
                    text: tab.project ? tab.project.authors : ""
                    onAccepted: commit()
                    onEditingFinished: commit()

                    // Return and leaving the field both commit; the second of the two finds nothing new.
                    function commit() {
                        if (tab.project && text !== tab.project.authors)
                            tab.project.authors = text;
                    }
                }
            }
            // Several lines, wrapped, from its start (the owner, 2026-10-27): Return types a line break, and leaving the
            // field commits.
            DescriptionRow {
                label: qsTr("Description")
                EaElements.TextArea {
                    objectName: "project.description"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    padding: 0
                    backgroundOpacity: 0
                    wrapMode: TextEdit.Wrap
                    placeholderText: qsTr("Enter project description here")
                    text: tab.project ? tab.project.description : ""
                    onEditingFinished: {
                        if (tab.project && text !== tab.project.description)
                            tab.project.description = text;
                    }
                }
            }

            Item {
                height: 1
                width: 1
            }

            // Where the project is: for a bundled example the working copy a save writes.
            DescriptionRow {
                label: qsTr("Location")
                EaElements.Label {
                    objectName: "project.location"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    elide: Text.ElideMiddle
                    text: Session.locationText
                }
            }
            // The blocks by name, each with its icon in its colour, the count in the label (as
            // easydiffractionbeta's "Model file: …"; ADR-0017 §9).
            DescriptionRow {
                label: qsTr("Structures (%1)").arg(tab.project ? tab.project.structures.count : 0)
                BlockNames {
                    objectName: "project.structures"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    blocks: tab.project ? tab.project.structures : null
                    blockKind: "structure"
                }
            }
            DescriptionRow {
                label: qsTr("Experiments (%1)").arg(tab.project ? tab.project.experiments.count : 0)
                BlockNames {
                    objectName: "project.experiments"
                    width: column.width - AppSizes.descriptionNameColumnWidth
                    blocks: tab.project ? tab.project.experiments : null
                    blockKind: "experiment"
                }
            }
        }
    }
}
