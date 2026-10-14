// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "ProjectEditCommit"
    when: windowShown
    property var appWindow
    property var page
    property url projectUrl
    Component {
        id: mainFactory
        Main {}
    }
    Component {
        id: descriptionFactory
        DescriptionTab {}
    }
    function init() {
        projectUrl = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(String(projectUrl) !== "" && Session.openProject(projectUrl), "Project edit cases open their own valid saved project");
        tryCompare(Session.project, "calculating", false, 10000, "The project finishes loading before metadata input");
        appWindow = mainFactory.createObject(null, {
            width: 1100,
            height: 800
        });
        verify(appWindow !== null, "The actual Main supplies the Save button and modified window title");
        page = descriptionFactory.createObject(appWindow.contentItem, {
            project: Session.project,
            x: 20,
            y: 70,
            width: 1050,
            height: 680,
            z: 100
        });
        verify(page !== null && waitForPolish(page), "The actual Project description pane lays out its editable fields");
        verify(waitForRendering(appWindow.contentItem), "The actual app window renders before pointer input");
        compare(Session.project.modified, false, "Each focus-leave witness starts from an unmodified saved project");
    }
    function cleanup() {
        if (page)
            page.destroy();
        if (appWindow)
            appWindow.destroy();
        page = null;
        appWindow = null;
        Session.closeProject();
    }
    function test_metadata_commits_on_every_focus_leave_data() {
        const rows = [];
        for (const field of ["name", "title", "description"])
            for (const leave of ["tab", "return", "field", "page"])
                rows.push({
                    tag: field + "-" + leave,
                    field: field,
                    leave: leave
                });
        return rows;
    }
    function test_metadata_commits_on_every_focus_leave(data) {
        const field = findChild(page, "project." + data.field);
        verify(field !== null, "The test reaches the actual named Project metadata field");
        mouseClick(field, field.width / 2, field.height / 2);
        tryCompare(field, "activeFocus", true, 1000, "Real pointer input focuses the metadata editor");
        const wanted = data.field === "name" ? "focus_name" : "Focus " + data.field;
        verify(SettingsProof.type(field, wanted), "Actual window key events replace the focused metadata text");
        if (data.leave === "tab")
            verify(SettingsProof.key(field, Qt.Key_Tab), "Tab goes through the actual app window's focus navigation");
        else if (data.leave === "return")
            verify(SettingsProof.key(field, Qt.Key_Return), "Return goes through the actual editor's accepted handler");
        else if (data.leave === "field") {
            const other = findChild(page, "project." + (data.field === "title" ? "description" : "title"));
            verify(other !== null, "The other-field witness is another real metadata editor");
            mouseClick(other, other.width / 2, other.height / 2);
        } else
            mouseClick(page, page.width - 15, page.height - 15);
        tryCompare(Session.project, "modified", true, 1000, "Leaving a metadata edit by Tab, Return, another field or the page commits and modifies the project");
        compare(Session.project[data.field], wanted, "The committed model holds exactly the user's new metadata text");
        const save = findChild(appWindow, "appBar.button.save");
        verify(save !== null && save.enabled, "Every committed metadata edit enables the actual Save control");
        verify(appWindow.title.startsWith("• "), "A committed metadata edit marks the real app window title");
        mouseMove(page, page.width - 15, page.height - 15);
        if (!field.activeFocus) {
            tryCompare(field.font, "bold", false, 1000, "A metadata field drops the focused bold look when active focus leaves");
        }
        mouseClick(save, save.width / 2, save.height / 2);
        tryCompare(Session.project, "modified", false, 1000, "The real Save button writes and clears the modified state");
        const text = SettingsProof.text(projectUrl, "project.edi");
        const match = text.match(new RegExp("^_metadata\\." + data.field + "\\s+(.*)$", "m"));
        verify(match !== null, "A save contains the edited metadata item in project.edi");
        const value = match[1].trim().replace(/^(['"])(.*)\1$/, "$2");
        compare(value, wanted, "The saved metadata item contains the new user text rather than the old field value");
    }
}
