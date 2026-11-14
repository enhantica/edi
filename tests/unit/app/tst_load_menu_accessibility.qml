// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app

TestCase {
    name: "LoadMenuAccessibility"
    when: windowShown
    width: 500
    height: 200

    LoadMenuItem {
        id: action
        text: "From file…"
        fontIcon: "file"
        hint: ".cif .edi"
    }
    ListModel {
        id: firstOptions
        ListElement {
            text: "short"
        }
        ListElement {
            text: "label"
        }
    }
    SearchableComboBox {
        id: measuredCombo
        model: firstOptions
        textRole: "text"
    }
    function test_native_metrics_follow_model_data_and_replacement() {
        tryVerify(() => measuredCombo.optionWidth > 0);
        const firstWidth = measuredCombo.optionWidth;
        firstOptions.setProperty(1, "text", "a much longer option for native width observation");
        tryVerify(() => measuredCombo.optionWidth > firstWidth);
        const longWidth = measuredCombo.optionWidth;
        measuredCombo.model = ["a", "b"];
        tryVerify(() => measuredCombo.optionWidth < longWidth);
        const replacementWidth = measuredCombo.optionWidth;
        firstOptions.setProperty(0, "text", "an obsolete model must no longer invalidate or size this control");
        wait(0);
        compare(measuredCombo.optionWidth, replacementWidth);
    }
    function test_action_name_excludes_icon_and_hint() {
        compare(action.Accessible.name, "From file…");
        compare(action.Accessible.description, ".cif .edi");
        verify(action.contentItem.children[0].Accessible.ignored);
        verify(action.contentItem.children[2].Accessible.ignored);
        compare(action.contentItem.children[1].text, "From file…");
        action.fontIcon = "folder";
        action.hint = "Sequential: each from the previous";
        compare(action.Accessible.name, "From file…");
        action.text = "From folder…";
        compare(action.Accessible.name, "From folder…");
    }
    function test_source_kind_chips_have_the_shared_typed_fields() {
        const chips = ApplicationInfo.sourceKindTags(["structure", "data", "unknown", "project"]);
        compare(chips.length, 3);
        compare(chips[0].label, "Structures");
        compare(chips[0].glyph, "layer-group");
        compare(chips[2].label, "Projects");
        compare(chips[2].glyph, "archive");
        for (let index = 0; index < chips.length; ++index) {
            verify(chips[index].light.length > 0);
            verify(chips[index].dark.length > 0);
        }
        compare(ApplicationInfo.sourceKindTags([]).length, 0);
    }
    function test_column_width_comparison_keeps_the_layout_values_native() {
        verify(ApplicationInfo.sameColumnWidths([], []));
        verify(ApplicationInfo.sameColumnWidths([0, 1.25, 80], [-0, 1.25, 80]));
        verify(!ApplicationInfo.sameColumnWidths([0, 1.25], [0, 1.5]));
        verify(!ApplicationInfo.sameColumnWidths([0], [0, 0]));
        verify(ApplicationInfo.sameColumnWidths([NaN, Infinity], [-Infinity, NaN]));
    }
}
