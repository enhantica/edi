// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Examples list's filters (ADR-0031), as the website's catalogue has them: five selectors, two to a line, each
// listing its values with how many entries the other filters leave, then the search and a square button clearing them
// all. The Tutorials list uses the same filters on its own list (ADR-0064).
Grid {
    id: filters

    // The list filtered.
    required property ExampleListModel catalogue
    // The start of the controls' names: `<prefix>.filter.<key>`, `<prefix>.search` and `<prefix>.clearFilters`.
    property string namePrefix: "examples"
    property string searchHint: qsTr("Search examples")
    // The width of the whole block; each selector takes half of it.
    property real rowWidth: EaStyle.Sizes.sideBarContentWidth

    readonly property real fieldWidth: (rowWidth - spacing) / 2
    readonly property var facets: ["purpose", "fittingMode", "sampleForm", "probe", "beamMode"]

    columns: 2
    spacing: AppSizes.inputSpacing

    Repeater {
        model: filters.facets

        SearchableComboBox {
            id: selector

            required property string modelData
            readonly property var options: filters.catalogue.facetRevision >= 0 ? filters.catalogue.facetOptions(modelData) : []

            objectName: `${filters.namePrefix}.filter.${modelData}`
            width: filters.fieldWidth
            horizontalAlignment: Text.AlignLeft
            model: selector.options
            textRole: "title"
            searchThreshold: 1000
            popup.width: Math.max(width, optionWidth)
            currentIndex: Math.max(0, selector.options.findIndex(option => option.value === filters.catalogue.facetFilter(selector.modelData)))
            onActivated: index => filters.catalogue.setFacetFilter(selector.modelData, selector.options[index].value)
        }
    }
    Row {
        spacing: filters.spacing

        EaElements.TextField {
            id: searchField

            objectName: `${filters.namePrefix}.search`
            width: filters.fieldWidth - filters.spacing - height
            placeholderText: filters.searchHint
            horizontalAlignment: TextInput.AlignLeft
            text: filters.catalogue.searchText
            onTextEdited: filters.catalogue.searchText = text
        }
        // Clears every filter, the search and the five selectors (the owner, 2026-11-04).
        EaElements.SideBarButton {
            objectName: `${filters.namePrefix}.clearFilters`
            width: height
            height: searchField.height
            fontIcon: "eraser"
            text: ""
            ToolTip.text: qsTr("Clear all filters")
            onClicked: {
                filters.catalogue.searchText = "";
                filters.catalogue.clearFacets();
            }
        }
    }
}
