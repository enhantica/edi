// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Examples list's filters (ADR-0031): the property to filter by and its value with how many items have it, a
// search, and a button clearing them all. The Tutorials list uses the same filters on its own list (ADR-0064).
EaElements.GroupRow {
    id: filters

    // The list filtered.
    required property ExampleListModel catalogue
    // The start of the controls' names: `<prefix>.property`, `<prefix>.value`, `<prefix>.search` and
    // `<prefix>.clearFilters`.
    property string namePrefix: "examples"
    property string searchHint: qsTr("Search examples")
    // The width of the whole row; each of the three fields takes a third of what the square clear button leaves.
    property real rowWidth: EaStyle.Sizes.sideBarContentWidth

    readonly property real fieldWidth: (rowWidth - 3 * spacing - searchField.height) / 3

    function choiceIndex(model, value) {
        for (let i = 0; i < model.count; ++i)
            if (model.text(i, "value") === value)
                return i;
        return 0;
    }

    spacing: AppSizes.inputSpacing

    SearchableComboBox {
        objectName: `${filters.namePrefix}.property`
        width: filters.fieldWidth
        horizontalAlignment: Text.AlignLeft
        model: filters.catalogue.filterProperties
        textRole: "title"
        searchThreshold: 1000
        currentIndex: filters.choiceIndex(filters.catalogue.filterProperties, filters.catalogue.filterProperty)
        onActivated: index => filters.catalogue.filterProperty = filters.catalogue.filterProperties.text(index, "value")
    }
    SearchableComboBox {
        objectName: `${filters.namePrefix}.value`
        width: filters.fieldWidth
        horizontalAlignment: Text.AlignLeft
        model: filters.catalogue.filterOptions
        textRole: "title"
        popup.width: Math.max(width, optionWidth)
        currentIndex: filters.choiceIndex(filters.catalogue.filterOptions, filters.catalogue.filterValue)
        onActivated: index => filters.catalogue.filterValue = filters.catalogue.filterOptions.text(index, "value")
    }
    EaElements.TextField {
        id: searchField
        objectName: `${filters.namePrefix}.search`
        width: filters.fieldWidth
        placeholderText: filters.searchHint
        horizontalAlignment: TextInput.AlignLeft
        text: filters.catalogue.searchText
        onTextEdited: filters.catalogue.searchText = text
    }
    // Clears every filter: the search, and the property back to Purpose with all its values (the owner, 2026-11-04);
    // the Analysis parameter filter's button.
    EaElements.SideBarButton {
        objectName: `${filters.namePrefix}.clearFilters`
        width: height
        height: searchField.height
        fontIcon: "eraser"
        text: ""
        ToolTip.text: qsTr("Clear all filters")
        onClicked: {
            filters.catalogue.searchText = "";
            filters.catalogue.filterProperty = "purpose";
            filters.catalogue.filterValue = "";
        }
    }
}
