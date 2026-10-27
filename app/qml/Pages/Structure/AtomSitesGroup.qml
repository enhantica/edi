// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSite.qml): label, the type with its atom icon,
// coordinates, Wyckoff position and occupancy; append, duplicate and remove as the library's AtomSites do. The ADP
// columns are the Atomic displacement group's (the owner, 2026-10-06).
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteListModel sites: structure ? structure.atomSites : null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5
    // The WP column fits the widest position name ("48n") and the box's arrow; its list shows the coordinates too (the
    // owner, 2026-10-11).
    readonly property real wyckoffWidth: {
        let widest = 0;
        const names = sites ? sites.wyckoffNames : [];
        for (let i = 0; i < names.length; ++i)
            widest = Math.max(widest, wyckoffMetrics.advanceWidth(names[i]));
        return Math.ceil(Math.max(widest, wyckoffMetrics.advanceWidth("WP"))) + EaStyle.Sizes.fontPixelSize * 2.5;
    }

    FontMetrics {
        id: wyckoffMetrics

        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSites.list"
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.sites

        // Equal-width numeric columns, the one exception to the table rule (the owner, 2026-10-24).

        equalColumns: true

        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), group.typeWidth, -1, -1, -1, group.wyckoffWidth, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.type_symbol"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_x"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_y"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_z"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.wyckoff_letter"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.occupancy"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string label
            required property string typeSymbol
            required property string wyckoffLetter
            required property ParameterItem fractX
            required property ParameterItem fractY
            required property ParameterItem fractZ
            required property ParameterItem occupancy

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                objectName: `atomSite.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.label
                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            // The type picked from the element table or typed into the list's search field (the owner,
            // 2026-10-06); a type outside the table, as a file may declare it ("Co2+", "157Gd"), is shown as it is.
            Item {
                property int horizontalAlignment: Text.AlignLeft
                height: parent.height
                SearchableComboBox {
                    width: Math.min(parent.width, implicitWidth)
                    x: parent.horizontalAlignment === Text.AlignRight ? parent.width - width : parent.horizontalAlignment === Text.AlignLeft ? 0 : (parent.width - width) / 2
                    horizontalAlignment: Text.AlignLeft
                    objectName: `atomSite.typeSymbol.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    searchThreshold: 0
                    model: ApplicationInfo.elementSymbols
                    currentIndex: ApplicationInfo.elementSymbols.indexOf(row.typeSymbol)
                    displayText: row.typeSymbol
                    popup.width: Math.max(width, EaStyle.Sizes.fontPixelSize * 8)
                    // The site's atom icon in its element's colour just before the type, as the Analysis page's parameter
                    // names carry it (the owner, 2026-10-03 and 2026-10-06).
                    contentItem: Item {
                        implicitWidth: typeLine.implicitWidth + EaStyle.Sizes.fontPixelSize * 0.5
                        clip: true

                        IconLine {
                            id: typeLine
                            objectName: `atomSite.icon.${row.index}`
                            x: EaStyle.Sizes.fontPixelSize * 0.5
                            anchors.verticalCenter: parent.verticalCenter
                            segments: [
                                {
                                    "icon": row.fractX ? row.fractX.categoryIcon : "",
                                    "color": AppColors.element(row.typeSymbol)
                                },
                                {
                                    "text": row.typeSymbol
                                }
                            ]
                        }
                    }
                    onActivated: index => {
                        group.sites.setText(row.index, "typeSymbol", textAt(index));
                        currentIndex = Qt.binding(() => ApplicationInfo.elementSymbols.indexOf(row.typeSymbol));
                    }
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractX.${row.index}`
                item: row.fractX
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractY.${row.index}`
                item: row.fractY
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractZ.${row.index}`
                item: row.fractZ
            }
            // The Wyckoff position, chosen among the space group's: its multiplicity, letter and coordinates
            // (the owner, 2026-10-08). A letter the group does not know is shown as it is.
            Item {
                property int horizontalAlignment: Text.AlignHCenter
                height: parent.height
                SearchableComboBox {
                    readonly property int letterIndex: group.sites ? group.sites.wyckoffLetters.indexOf(row.wyckoffLetter) : -1

                    width: parent.width
                    objectName: `atomSite.wyckoffLetter.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: group.sites ? group.sites.wyckoffLabels : []
                    // PT Sans lacks the thirds, sixths and eighths in the coordinates; Noto Sans has them.
                    listFontFamily: "Noto Sans"
                    currentIndex: letterIndex
                    displayText: letterIndex >= 0 ? group.sites.wyckoffNames[letterIndex] : row.wyckoffLetter
                    onActivated: index => {
                        group.sites.setText(row.index, "wyckoffLetter", group.sites.wyckoffLetters[index]);
                        currentIndex = Qt.binding(() => letterIndex);
                    }
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.occupancy.${row.index}`
                item: row.occupancy
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this atom site")
                onClicked: group.sites.remove(row.index)
            }
        }
    }

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "atomSites.append"
            fontIcon: "plus-circle"
            text: qsTr("Append new atom site")
            onClicked: group.sites.append()
        }
        EaElements.SideBarButton {
            objectName: "atomSites.duplicate"
            enabled: table.currentIndex >= 0 || (group.sites && group.sites.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected atom site")
            onClicked: group.sites.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
