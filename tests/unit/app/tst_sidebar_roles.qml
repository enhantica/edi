// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ProjectTextAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "SidebarRoles"
    when: windowShown

    ProjectTextProof {
        id: dictionary
    }
    Component {
        id: application
        Main {
            width: 1350
            height: 950
        }
    }

    function test_tabs_follow_their_roles() {
        const source = Probe.repoUrl("tests/fixtures/e04_t1/xray-project");
        verify(Session.openProject(SettingsProof.copyProject(source)), "The sidebar witness opens measured data and a Crystal structure");
        const app = application.createObject(null);
        verify(app && waitForRendering(app.contentItem), "The actual workflow window renders before sidebar navigation");
        tryVerify(() => app.pagesWanted > 0 && app.pagesBuilt === app.pagesWanted, 15000, "All workflow pages finish loading");
        const tabs = ["basic", "extras", "text", "tools", "settings"];
        // Custom editors here still write .edi data even though their groups have no dictionary category ID.
        const editors = {
            project: ["su_format"],
            structure: ["structures"],
            experiment: ["experiments"],
            analysis: ["parameters"],
            report: ["reportContents"]
        };
        const tools = {
            project: [],
            structure: ["magnetic_analysis"],
            experiment: ["background_estimate", "k_search"],
            analysis: [],
            report: ["reportExport"]
        };
        const ranks = dictionary.categoryRanks();
        const failures = [];
        try {
            for (const name of Object.keys(tools)) {
                Ui.click(test, Probe, app, "appBar.tab." + name);
                const page = Ui.page(app);
                const sidebar = findChild(page, "workflow." + name + ".manualSidebar");
                verify(sidebar, "The current workflow page has a real sidebar for " + name);
                compare(Array.from(sidebar.tabs).map(tab => tab.objectName), tabs.map(tab => "sideBar.tab." + tab), name + " exposes Main, Extra, Text, Tools and Settings in the approved order");
                for (const role of ["basic", "extras", "tools", "settings"]) {
                    const pane = Ui.selectSidebarTab(test, page, role, sidebar);
                    const groups = Ui.groupNames(pane);
                    if (role === "tools") {
                        for (const group of tools[name])
                            if (!groups.includes(group))
                                failures.push(name + " Tools is missing " + group);
                    } else if (role === "settings") {
                        for (const group of tools[name])
                            if (groups.includes(group))
                                failures.push(name + " Settings contains the tool " + group);
                        if (name === "structure" && !["appearance", "polyhedra"].every(group => groups.includes(group)))
                            failures.push("Structure Settings is missing Appearance or Polyhedra");
                    } else {
                        for (const group of groups)
                            if (tools[name].includes(group) || (!Object.prototype.hasOwnProperty.call(ranks, group) && !editors[name].includes(group)))
                                failures.push(name + " " + role + " contains a group without an .edi category: " + group);
                        if (name === "structure" && role === "basic" && Render.descendants(pane).some(item => item.objectName === "spaceGroup.magneticAnalysis" && Ui.inPane(item)))
                            failures.push("Structure Main still offers a magnetic analysis button");
                    }
                }
            }
            compare(failures, [], "Every workflow sidebar puts its .edi editors, tools and view settings in their assigned tabs");
        } finally {
            app.close();
            app.destroy();
            Session.closeProject();
        }
    }
}
