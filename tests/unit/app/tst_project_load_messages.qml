import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import LoadArchiveTests 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ProjectLoadMessages"
    when: windowShown
    LoadArchiveProof { id: archives }
    property var previousPaths
    property var appWindow
    Component { id: application; Main {} }
    function init() {
        previousPaths = RecentProjects.settings.projectPaths.slice();
        Session.examples.searchText = "";
        Session.examples.filterProperty = "purpose";
        Session.examples.filterValue = "";
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Load refusal checks must use the actual production window");
        verify(waitForRendering(appWindow.contentItem), "The production load window must render");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment")), "The retained project must open before a refused replacement");
        Ui.click(test, Probe, appWindow, "appBar.tab.project");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
        RecentProjects.settings.projectPaths = previousPaths;
    }
    function test_all_routes_data() {
        return [ {tag: "open"}, {tag: "recent"}, {tag: "example"}, {tag: "zip"} ];
    }
    function request(route) {
        const bad = Probe.repoUrl("tests/fixtures/legacy_project_load/invalid");
        if (route.tag === "open") {
            Ui.expandGroup(test, Probe, appWindow, "group.getStarted");
            const dialogs = Probe.objectsWithProperty(appWindow, "selectedFolder").filter(item => item.title === "Open an edi project directory");
            compare(dialogs.length, 1, "The open route must use its actual production folder dialog");
            dialogs[0].selectedFolder = bad;
            dialogs[0].accepted();
        } else if (route.tag === "recent") {
            const path = String(bad).replace(/^file:\/\//, "");
            RecentProjects.remember(path);
            Ui.expandGroup(test, Probe, appWindow, "group.recentProjects");
            Ui.click(test, Probe, appWindow, "recentProjects.path.0");
        } else if (route.tag === "example") {
            Ui.expandGroup(test, Probe, appWindow, "group.examples");
            const id = Probe.rows(Session.examples)[0].exampleId;
            const row = Ui.control(Probe, appWindow, "examples.open." + id) || Ui.control(Probe, appWindow, "examples.open.no-such-example-load-witness");
            verify(row !== null, "The example route must use an actual mounted example row");
            row.exampleId = "no-such-example-load-witness";
            mouseClick(row);
        } else {
            Ui.expandGroup(test, Probe, appWindow, "group.getStarted");
            const group = Ui.control(Probe, appWindow, "group.getStarted");
            group.webRequest = 742;
            group.webRequestProject = Session.project;
            const extracted = archives.unpack("tests/fixtures/legacy_project_load/invalid");
            verify(String(extracted).length > 0, "The zip route must execute the production archive pack/unpack boundary");
            WebFiles.projectOpened(742, extracted);
        }
    }
    function test_all_routes(route) {
        const retained = Session.project;
        for (let attempt = 0; attempt < 2; ++attempt) {
            request(route);
            verify(Session.lastError.length > 0, "Each refused load must retain its actual reason");
            const dialogs = Probe.objectsWithProperty(appWindow, "message").filter(item => item.visible && item.message === Session.lastError);
            compare(dialogs.length, 1, "Each load path and repeated identical failure must show exactly one actual error dialog");
            compare(Session.project, retained, "A refused load must keep the previously opened project");
            dialogs[0].close();
        }
    }
    function test_failed_archive_decoder_shows_each_real_message() {
        const retained = Session.project;
        const message = archives.malformedArchiveError();
        verify(message.length > 0, "The actual archive decoder must produce a reason for the minimal invalid archive");
        for (let attempt = 0; attempt < 2; ++attempt) {
            Ui.expandGroup(test, Probe, appWindow, "group.getStarted");
            const group = Ui.control(Probe, appWindow, "group.getStarted");
            group.webRequest = 743;
            group.webRequestProject = retained;
            WebFiles.failed(743, message);
            const dialogs = Probe.objectsWithProperty(appWindow, "message").filter(item => item.visible && item.message === message);
            compare(dialogs.length, 1, "Every archive failure must show the actual decoder message, including an identical repeat");
            compare(Session.project, retained, "A failed archive must retain the open project");
            dialogs[0].close();
        }
    }
    function test_legacy_save_data() {
        return [{tag: "line-segment"}, {tag: "polynomial"}, {tag: "chebyshev"}];
    }
    function test_legacy_save(row) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/legacy_project_load/" + row.tag)), "A minimal previous-writer project must open through the production Session");
        compare(Session.lastError, "", "A successful legacy load must clear stale refusal text");
        verify(Session.hasProject, "A successful legacy load must install its project");
    }
}
