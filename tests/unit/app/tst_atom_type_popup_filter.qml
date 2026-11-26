// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "AtomTypePopupFilter"
    when: windowShown
    property var app
    property var box
    property var field
    property real fullHeight
    Component { id: windowFactory; Main {} }

    function init() {
        app = windowFactory.createObject(null);
        verify(app !== null, "The Type search needs the actual Structure page");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The Type search receives keyboard input in its own window");
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project")),
               "Open a real neutron project whose Type list contains prefix and substring matches");
        Ui.click(test, Probe, app, "appBar.tab.structure");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.atom_site");
        box = Ui.control(Probe, app, "atomSite.typeSymbol.0");
        verify(box !== null && box.enabled, "The first atom's real Type list is reachable");
        mouseClick(box);
        tryCompare(box.popup, "opened", true, 2000, "Opening the real atom Type list exposes its popup");
        field = Ui.find(box.popup.contentItem.headerItem, "comboBox.search");
        verify(field !== null && field.visible, "The atom Type list contains its search field");
        fullHeight = box.popup.height;
    }

    function cleanup() {
        box = field = null;
        Session.closeProject();
        app.destroy();
    }

    function search(text) {
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 1000, "The real popup search field receives input");
        verify(SettingsProof.type(field, text), "The Type search receives the typed query");
        tryCompare(box, "searchText", text, 1000,
                   "Entering text in the popup's search field updates the actual Type filter");
    }

    function test_unknown_type_has_an_explanation() {
        search("zzzunknownatom");
        tryVerify(() => Render.texts(box.popup.contentItem).some(item =>
            /no .*match|no matching|no .*found/i.test(item.text)),
            1500, "A filtered Type list with no matches visibly explains the empty list");
    }

    function test_narrow_filter_reduces_popup_height() {
        search("Co");
        tryVerify(() => box.popup.height < fullHeight, 1500,
                  "The Type popup shrinks when only a few types match the search");
    }

    function test_prefix_precedes_substrings_and_selects_existing_type() {
        search("D");
        const types = Array.from({length: box.count}, (_, index) => box.textAt(index));
        verify(types.some(text => /^d/i.test(text)) && types.some(text => /^[^d].*d/i.test(text)),
               "The neutron Type fixture contains both prefix and substring matches for D");
        verify(waitForRendering(app.contentItem), "The typed search order appears in a rendered frame");
        const popup = box.popup.contentItem;
        const ranked = Render.descendants(popup).filter(item => item.visible && item.opacity > 0
            && item.height > 0 && typeof item.clicked === "function"
            && typeof item.text === "string" && /d/i.test(item.text) && Ui.rendered(item));
        ranked.sort((left, right) => left.mapToItem(popup, 0, 0).y - right.mapToItem(popup, 0, 0).y);
        verify(ranked.length > 0, "The filtered opening rows render at the top of the Type list");
        verify(/^d/i.test(ranked[0].text),
               "Types starting with D must precede substring matches, but the first match is " + ranked[0].text);
        const wanted = ranked[0].text;
        mouseClick(ranked[0]);
        tryVerify(() => Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol === wanted, 1500,
                  "Selecting a reordered match assigns the type displayed in that row");
    }
}
