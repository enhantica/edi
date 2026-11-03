// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "EmptyProjectSidebar"
    when: windowShown
    property var app: null
    Component {
        id: application
        Main {}
    }

    function init() {
        // Same exact offscreen prerequisite/diagnostics as the existing production actors.
        failOnWarning(Probe.softwareOffscreenWithoutGl() ? /\A(?!(?:QRhiGles2: Failed to create (?:temporary context|context)|window doesn\x27t exist\.)\z)[\s\S]*\z/ : /.*/);
        Session.closeProject();
        app = application.createObject(null, {
            width: 1280,
            height: 800,
            visible: true
        });
        verify(app !== null, "Sidebar acceptance creates the genuine production Main window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "Home Start input belongs to the actual active window");
    }

    function cleanup() {
        Probe.clearWatches();
        Session.closeProject();
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
    }

    function unique(root, name) {
        const found = Render.descendants(root).filter(item => item.objectName === name);
        compare(found.length, 1, "The current production visual tree owns exactly one " + name);
        return found[0];
    }

    function shown(item) {
        if (!Ui.rendered(item))
            return false;
        for (let ancestor = item; ancestor; ancestor = ancestor.parent) {
            if (!ancestor.visible || !(ancestor.opacity > 0))
                return false;
        }
        return true;
    }

    function test_home_start_keeps_empty_project_sidebar_usable() {
        compare(Session.hasProject, false, "This is the original no-project workflow");
        Ui.click(test, Probe, app, "appBar.tab.home");
        Ui.click(test, Probe, app, "home.start");
        const loader = app.contentArea[AppState.Page.Project];
        tryVerify(() => AppState.projectPageEnabled && loader.status === Loader.Ready && loader.item !== null,
                  10000, "Real Home Start admits and loads the production Project page");
        Ui.click(test, Probe, app, "appBar.tab.project");
        compare(Ui.page(app), loader, "The real selected viewport is the admitted Project loader");
        compare(loader.item.current, true, "The current production Project page owns the sidebar");
        compare(Session.project, null, "Sidebar admission does not create or substitute a project");

        const sidebar = unique(loader.item, "workflow.project.manualSidebar");
        const main = unique(sidebar, "sideBar.tab.basic");
        const names = ["getStarted", "examples", "recentProjects"];
        const groups = names.map(name => unique(sidebar, "group." + name));
        const children = Array.from(sidebar.children);
        const tabHosts = children.filter(item => Render.descendants(item).includes(main));
        const groupHosts = children.filter(item => {
            const descendants = Render.descendants(item);
            return groups.every(group => descendants.includes(group));
        });
        console.log("EMPTY_PROJECT_SIDEBAR_STATE " + JSON.stringify({
            admitted: AppState.projectPageEnabled,
            projectPresent: Session.hasProject,
            main: {visible: main.visible, opacity: main.opacity, width: main.width, height: main.height},
            groups: groups.map(group => ({name: group.objectName, visible: group.visible, width: group.width, height: group.height})),
            directChildren: children.map(item => ({type: String(item), visible: item.visible, gradientType: typeof item.gradient, children: item.children.length}))
        }));
        compare(tabHosts.length, 1, "The actual sidebar owns the tab strip's real visual ancestor");
        compare(groupHosts.length, 1, "The actual sidebar owns one recursively populated content ancestor");
        // These are real Qt Quick controls, not a JS stand-in or injected property.
        for (const receiver of [tabHosts[0], groupHosts[0]]) {
            compare(typeof receiver.gradient, "undefined", "A missing QObject member remains undefined");
            compare(receiver["gradient"], undefined, "Computed QObject lookup preserves real absence too");
            compare(Boolean(receiver.gradient), false, "An absent QObject member is falsy");
            verify(receiver.children.length > 0, "The actual QObject exposes its genuine visual children");
        }

        tryVerify(() => shown(main) && main.enabled, 2000, "The no-project Main tab is painted and enabled");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        compare(main.checked, true, "Real input selects the original Main sidebar pane");
        for (const receiver of [tabHosts[0], groupHosts[0]])
            verify(shown(receiver), "Missing decorative members cannot hide real sidebar controls");
        compare(Ui.groupNames(sidebar).sort().join("|"), names.slice().sort().join("|"),
                "Recursive current-pane discovery retains Get started, Examples and Recent projects");
        for (const group of groups) {
            verify(group.visible && group.width > 0 && group.height > 0,
                   "The production group is visible before any viewport positioning: " + group.objectName);
            verify(group.titleArea !== null && group.titleArea !== undefined, "Each original group retains its real header");
            verify(typeof group.title === "string" && group.title.length > 0,
                   "Each original group retains its nonempty production title");
            // Existing actor preparation only: expose a vertically clipped header without
            // changing its visibility, opacity, fold state, project or selected pane.
            Ui.scrollIntoView(group.titleArea);
            tryVerify(() => shown(group.titleArea), 2000, "The real group header is exposed: " + group.objectName);
            verify(Render.texts(group.titleArea).some(item => shown(item) && item.text.includes(group.title)),
                   "The original group title is actually painted: " + group.objectName);
        }
        app.update();
        verify(waitForRendering(sidebar), "The usable no-project sidebar reaches an actual rendered frame");
        compare(Session.hasProject, false, "The complete original empty-project workflow stays empty");
    }
}
