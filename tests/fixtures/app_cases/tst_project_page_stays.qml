// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import EasyApplication.Gui.Globals as EaGlobals

import edi.app

// The Project page stays when one project replaces another (edi ADR-0052): what the old project showed, or had under
// way, goes, and the Load menu stays open.
TestCase {
    id: test

    name: "ProjectPageStays"
    when: windowShown

    property var window: null
    readonly property url lbco: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_lbco-hrpt/project")
    readonly property url y2o3: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_y2o3-spodi/project")

    function find(name) {
        return findChild(window, name);
    }
    function initTestCase() {
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        verify(Session.openProject(lbco), Session.lastError);
        tryVerify(() => find("project.load") !== null && find("project.name") !== null, 20000);
        tryCompare(find("project.name"), "text", Session.project.name);
        AppState.open(AppState.Page.Project);
        wait(500);
    }
    function cleanupTestCase() {
        Session.closeProject();
        window.destroy();
    }
    // Opens the other project of the two; the page's own Load button before and after is the same.
    function replace() {
        const load = find("project.load");
        const other = Session.project.name.indexOf("lbco") >= 0 ? y2o3 : lbco;
        verify(Session.openProject(other), Session.lastError);
        compare(find("project.load"), load, "the Project page is the same");
        compare(find("project.name").text, Session.project.name);
        compare(find("project.title").text, Session.project.title);
        compare(find("project.description").text, Session.project.description);
        return load;
    }

    function test_a_the_page_stays_and_shows_the_next_project() {
        replace();
        replace();
    }
    function tab(name) {
        return findChild(find("workflow.project.sidebarHost") ?? window, name);
    }
    function test_b_extra_and_text_start_over_on_main() {
        const rules = ["iucr_19", "iucr_99"];
        Session.project.suRule = Session.project.suRule === rules[0] ? rules[1] : rules[0];
        for (const name of ["sideBar.tab.extras", "sideBar.tab.text"]) {
            const button = tab(name);
            verify(button !== null, name);
            button.checked = true;
            wait(300);
            replace();
            verify(!button.checked, name + " gives way to Main");
        }
        const edited = Session.project.suRule;
        tab("sideBar.tab.extras").checked = true;
        tryVerify(() => find("project.suRule") !== null, 5000, "Extra is shown again");
        compare(find("project.suRule").currentIndex, rules.indexOf(edited));
        replace();
        tab("sideBar.tab.extras").checked = true;
        tryVerify(() => find("project.suRule") !== null, 5000);
        compare(find("project.suRule").currentIndex, rules.indexOf(Session.project.suRule));
    }
    function test_c_an_edit_in_progress_is_not_committed_to_the_next_project() {
        const name = find("project.name");
        name.forceActiveFocus();
        name.selectAll();
        name.remove(0, name.length);
        name.insert(0, "typed-for-the-old-project");
        const before = Session.project.name;
        replace();
        verify(!name.activeFocus);
        wait(100);
        compare(name.text, Session.project.name);
        verify(Session.project.name !== "typed-for-the-old-project" && Session.project.name !== before);
        verify(!Session.project.modified);
        verify(!Session.project.canUndo);
    }
    function test_d_menus_and_dialogs() {
        const load = find("project.load.menu"), save = find("project.saveAs.menu"), create = find("createProject.dialog");
        load.open();
        tryVerify(() => load.opened, 5000);
        replace();
        verify(load.opened, "the Load menu stays open");
        load.close();
        tryVerify(() => !load.visible, 5000);
        save.open();
        tryVerify(() => save.opened, 5000);
        replace();
        tryVerify(() => !save.visible, 5000);
        EaGlobals.Vars.showProjectDescriptionDialog = true;
        tryVerify(() => create.opened, 5000);
        replace();
        tryVerify(() => !create.visible, 5000);
        verify(!EaGlobals.Vars.showProjectDescriptionDialog);
    }
    function test_e_groups_start_as_on_a_new_page() {
        const examples = find("group.examples"), recent = find("group.recentProjects"), started = find("group.getStarted");
        examples.collapsed = false;
        started.collapsed = true;
        replace();
        verify(examples.collapsed);
        verify(recent.collapsed);
        verify(!started.collapsed);
    }
    function test_f_a_create_under_way_is_dropped() {
        const started = find("group.getStarted"), life = started.createLife;
        started.createIntent = {
            "project": Session.project,
            "assistant": null
        };
        replace();
        tryCompare(started, "createIntent", null);
        verify(!life.alive);
        verify(started.createLife.alive);
    }
    function createField(name) {
        return find("createProject." + name);
    }
    // What the form holds for the old project: its draft fields, and the location typed for it.
    function test_g_the_create_form_starts_empty_for_the_next_project() {
        const dialog = find("createProject.dialog");
        const parent = dialog.projectParentDirectory;
        const names = ["name", "title", "authors", "description"];
        for (const closedByHand of [true, false]) {
            find("group.getStarted").chooseCreate();
            tryVerify(() => dialog.opened, 5000);
            for (const name of names)
                createField(name).text = "draft_" + name;
            if (createField("location") !== null)
                createField("location").text = "/somewhere/else";
            if (closedByHand) {
                dialog.reject();
                tryVerify(() => !dialog.visible, 5000);
                tryCompare(find("group.getStarted"), "createIntent", null);
                compare(createField("title").text, "draft_title", "a draft of the open project is kept");
            }
            replace();
            tryVerify(() => !dialog.visible, 5000);
            tryCompare(createField("name"), "text", "");
            find("group.getStarted").chooseCreate();
            tryVerify(() => dialog.opened, 5000);
            for (const name of names)
                compare(createField(name).text, "", name);
            if (createField("location") !== null)
                verify(createField("location").text !== "/somewhere/else");
            compare(dialog.projectParentDirectory, parent);
            dialog.reject();
            tryVerify(() => !dialog.visible, 5000);
            tryCompare(find("group.getStarted"), "createIntent", null);
        }
    }
    // The form's own OK, as the assistant's shown Create presses it, without its request.
    function test_h_a_create_leaves_no_draft() {
        const dialog = find("createProject.dialog");
        find("group.getStarted").chooseCreate();
        tryVerify(() => dialog.opened, 5000);
        createField("name").text = "made_here";
        createField("title").text = "A title";
        createField("authors").text = "Some Author";
        createField("description").text = "Some words";
        createField("location").text = "";  // not saved by its OK
        const before = Session.project;
        dialog.tryAccept();
        tryVerify(() => Session.project !== null && Session.project !== before, 10000, "the project is made");
        compare(Session.project.title, "A title");
        tryCompare(createField("name"), "text", "");
        find("group.getStarted").chooseCreate();
        tryVerify(() => dialog.opened, 5000);
        for (const name of ["name", "title", "authors", "description"])
            compare(createField(name).text, "", name);
        dialog.reject();
        tryVerify(() => !dialog.visible, 5000);
        verify(Session.openProject(lbco), Session.lastError);
    }
    function test_i_a_closed_project_and_a_new_one() {
        Session.closeProject();
        compare(Session.project, null);
        tryCompare(find("project.name"), "text", "");
        verify(Session.createProject("made-after", "its own description"));
        compare(find("project.name").text, "made-after");
        compare(find("project.description").text, "its own description");
        verify(Session.openProject(lbco), Session.lastError);
        compare(find("project.name").text, Session.project.name);
    }
}
