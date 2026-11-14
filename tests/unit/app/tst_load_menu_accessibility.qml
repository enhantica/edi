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
    function test_action_name_excludes_icon_and_hint() {
        compare(action.Accessible.name, "From file…");
        action.fontIcon = "folder";
        action.hint = "Sequential: each from the previous";
        compare(action.Accessible.name, "From file…");
        action.text = "From folder…";
        compare(action.Accessible.name, "From folder…");
    }
}
