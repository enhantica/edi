import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

// Oracle: development hub 's owner quotations and FINAL feedback, not screenshots
// or values extracted from the implementation. Synthetic .edi axes are in
// tests/fixtures/e04_t4/generate.py. Every test creates a fresh window/session.
TestCase {
    id: test
    name: "E04T4FinalIdeas"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }

    function init() {
        failOnWarning(/.*/);
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " gate 1: run the production application");
        verify(waitForRendering(appWindow.contentItem), " gate 1: render before inspection");
        Ui.click(test, Probe, appWindow, "appBar.tab.home");
        tryVerify(() => Ui.control(Probe, appWindow, "home.about") !== null, 2000, " gate 1: each fresh window reaches Home before its independent case");
    }
    function cleanup() {
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem), " gate 1: settle before destroying the window");
        appWindow.destroy();
    }
    function open(caseName) {
        Session.openProject(Qt.resolvedUrl("../../fixtures/e04_t4/" + (caseName || "uniform")));
        verify(Session.hasProject, " gate 1: independent synthetic project opens: " + Session.lastError);
    }
    function pane(page, tier) {
        if (!Ui.control(Probe, appWindow, "appBar.tab." + page).checked)
            Ui.click(test, Probe, appWindow, "appBar.tab." + page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 2000, " gate 1: selected page reaches the viewport");
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + tier);
        if (tab && !tab.checked)
            Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
        verify(waitForPolish(appWindow, 2000), " gate 1: sidebar layout settles");
        tryVerify(() => Review.descendants(Ui.page(appWindow)).filter(item => item.visible && item.interactive === false && item.count === 3 && item.currentItem).every(view => Math.abs(view.currentItem.mapToItem(view, 0, 0).x) < 0.1), 2000, " gate 1: selected sidebar pane reaches the viewport");
    }
    function group(name) {
        const found = Review.findGroup(Ui.page(appWindow), "group." + name);
        verify(found !== null, " gate 1: category is present: " + name);
        Ui.scrollIntoView(Ui.target(found));
        Ui.expandGroup(test, Probe, appWindow, "group." + name);
        return found;
    }
    function named(root, name) {
        const found = Review.find(root, name);
        verify(found !== null, " gate 1: required visible item: " + name);
        return found;
    }
    function closeEnough(actual, expected, message) {
        verify(Math.abs(actual - expected) < 1, " layout: " + message);
    }

    function test_about_description_and_documentation() {
        compare(ApplicationInfo.docsUrl, "https://docs.easydiffraction.org/app/", "idea 4: documentation points to the app documentation");
        Ui.click(test, Probe, appWindow, "home.about");
        const description = findChild(appWindow, "about.description");
        verify(description !== null, "idea 1: About exposes its description");
        compare(description.text, "EasyDiffraction is a software for calculating diffraction patterns based on structural models and refining their parameters against experimental data.", "idea 1: owner-supplied About description is preserved");
        verify(description.lineCount >= 2 && description.lineCount <= 3, "idea 1: description occupies two or three lines");
        compare(description.horizontalAlignment, Text.AlignHCenter, "idea 1: wrapped description is centered");
    }
    function test_home_about_logo_and_version_composition() {
        const home = Review.descendants(appWindow.contentItem).find(item => item.visible && item.markDiameter !== undefined);
        verify(home !== undefined, "idea 2: Home displays the logo lockup");
        const homeDiameter = home.markDiameter;
        const homeVersion = findChild(appWindow, "home.version");
        verify(homeVersion !== null, "ideas 2/3 final feedback: Home has an independent version line");
        closeEnough(home.x + home.width / 2, homeVersion.x + homeVersion.width / 2, "Home logo and version have the same horizontal center");
        verify(homeVersion.y >= home.y + home.height, "idea 3: Home version is below the logo");
        Ui.click(test, Probe, appWindow, "home.about");
        const version = findChild(appWindow, "about.version");
        verify(version !== null, "idea 3: About version is a separate line");
        const logo = Review.descendants(version.parent).find(item => item.markDiameter !== undefined);
        verify(logo !== undefined, "idea 2: About displays its logo");
        compare(logo.markDiameter, homeDiameter, "idea 2: Home and About logo sizes agree");
        closeEnough(logo.x + logo.width / 2, version.x + version.width / 2, "About logo and version have the same horizontal center");
        verify(version.y >= logo.y + logo.height, "idea 3: About version is below the logo");
    }
    function test_main_tabs_and_project_block_names() {
        open();
        const expected = [["project", "description", "lbco_hrpt_s2", "archive"], ["structure", "view", "lbco", "layer-group"], ["experiment", "chart", "hrpt", "microscope"]];
        expected.forEach(row => {
            pane(row[0], "basic");
            const tab = named(Ui.page(appWindow), "mainArea." + row[0] + ".tab." + row[1]);
            compare(tab.text, row[2], "ideas 6–8/23 final feedback: main tab is the datablock name");
            compare(tab.fontIcon, row[3], "idea 23: main tab includes its datablock icon");
        });
        pane("project", "basic");
        const location = named(Ui.page(appWindow), "project.location");
        compare(location.text, decodeURIComponent(String(Qt.resolvedUrl("../../fixtures/e04_t4/uniform")).replace(/^file:\/\//, "")), "idea 21: project Location always displays the opened directory");
        ["structures", "experiments"].forEach(kind => {
            const list = named(Ui.page(appWindow), "project." + kind);
            const label = kind === "structures" ? "Structures (1)" : "Experiments (1)";
            verify(Ui.text(Ui.page(appWindow)).indexOf(label) >= 0, "idea 22: project lists are named with datablock counts");
            verify(Ui.text(list).indexOf(kind === "structures" ? "lbco" : "hrpt") >= 0, "idea 22: project lists show datablock names");
        });
    }
    function test_selector_is_shared_across_all_tabs() {
        open("irregular");
        ["structure", "experiment"].forEach(page => {
            let selector = null;
            ["basic", "extras", "text"].forEach(tier => {
                pane(page, tier);
                const current = named(Ui.page(appWindow), "sideBar.blocks");
                verify(Ui.exposed(current), "idea 9: selector is always visible outside foldable groups");
                if (selector !== null)
                    compare(current, selector, "idea 9: one selector serves all sidebar tabs");
                selector = current;
                if (page === "experiment") {
                    Session.project.currentExperimentIndex = 1;
                    tryCompare(current, "currentIndex", 1, 2000, "idea 9: selecting a non-first experiment stays synchronized");
                    compare(current.currentText, "second", "idea 9: selector displays the selected block name");
                }
            });
        });
    }
    function test_folded_defaults_and_last_visible_border() {
        open();
        ["structure", "experiment", "analysis"].forEach(page => {
            ["basic", "extras"].forEach(tier => {
                pane(page, tier);
                const groups = Review.descendants(Ui.page(appWindow)).filter(item => item.visible && item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)));
                verify(groups.length > 0, "ideas 10/11: active pane has observable groups");
                groups.forEach(item => {
                    if (item.collapsible)
                        compare(item.collapsed, true, "idea 10 withdrawn: every foldable group starts folded");
                });
                compare(groups[groups.length - 1].last, true, "idea 11: last visible group suppresses its bottom border");
                groups.slice(0, -1).filter(item => item.collapsible).forEach(item => compare(item.last, false, "idea 11: preceding foldable categories retain their separators"));
            });
        });
    }
    function test_text_fills_sidebar_with_floating_continue() {
        open();
        ["project", "structure", "experiment", "analysis", "report"].forEach(page => {
            pane(page, "text");
            const text = named(Ui.page(appWindow), "text.view");
            verify(text.readOnly, "idea 5: .edi text remains read-only");
            let viewport = text.parent;
            while (typeof viewport.contentY !== "number" && viewport.parent)
                viewport = viewport.parent;
            verify(viewport.height > appWindow.height / 2, "idea 5 final feedback: editor fills the available sidebar height");
            verify(viewport.clip, "idea 5: text scrolls inside its sidebar viewport");
            const button = Review.find(Ui.page(appWindow), "sideBar.continue");
            if (page !== "report") {
                verify(button !== null && Ui.exposed(button), "idea 5: Continue stays visible");
                const bottom = viewport.mapToItem(appWindow.contentItem, 0, viewport.height).y;
                const buttonBottom = button.mapToItem(appWindow.contentItem, 0, button.height).y;
                verify(bottom >= buttonBottom, "idea 5 final feedback: text extends beneath floating Continue");
            }
        });
    }
    function test_disabled_manual_background_and_url_actions() {
        open();
        [["structure", "structures", "structures.define"], ["experiment", "experiments", "experiments.define"], ["experiment", "background", "background.autodetect"]].forEach(row => {
            pane(row[0], "basic");
            const item = named(group(row[1]), row[2]);
            compare(item.enabled, false, "ideas 13/17: requested unfinished action is visible and disabled");
            verify(item.text.length > 0 && item.width > 0, "ideas 13/17: disabled actions have visible labels and occupied layout space");
        });
        pane("project", "basic");
        const url = named(group("getStarted"), "project.openUrl");
        compare(url.enabled, false, "idea 27: URL loading placeholder is disabled");
        verify(url.text.indexOf("URL") >= 0, "idea 27: URL loading placeholder is named");
    }
    function test_experiment_type_three_by_two_layout() {
        open();
        pane("experiment", "basic");
        const box = group("experiment_type");
        const fields = ["sampleForm", "beamMode", "radiationProbe", "scatteringType"].map(name => named(box, "experimentType." + name));
        const positions = fields.map(item => item.mapToItem(box, 0, 0));
        closeEnough(positions[0].y, positions[1].y, "sample and beam share the first row");
        closeEnough(positions[1].y, positions[2].y, "beam and probe share the first row");
        verify(positions[0].x < positions[1].x && positions[1].x < positions[2].x, "idea 14: experiment type has three columns");
        closeEnough(positions[3].x, positions[0].x, "scattering starts the second row");
        verify(positions[3].y > positions[0].y, "idea 14: fourth selector occupies the second row");
    }
    function test_measured_data_and_increment_summary() {
        [["uniform", "0.125"], ["irregular", "0.125–0.375"]].forEach(row => {
            Session.closeProject();
            open(row[0]);
            pane("experiment", "extras");
            const box = group("data");
            compare(box.title, "Measured data (4)", "idea 15: measured points group is named and counted");
            const field = named(box, "range.step");
            compare(field.text, row[1], "idea 16: independently defined nontrivial axis steps determine inc");
            const table = named(box, "data.list");
            compare(table.count, 4, "idea 15: measured data group includes the .edi points table");
        });
    }
    function test_peak_has_no_subtitles_and_family_rows() {
        open();
        pane("experiment", "basic");
        const box = group("peak");
        const text = Ui.text(box);
        verify(text.indexOf("Broadening") < 0 && text.indexOf("Asymmetry") < 0, "idea 18 withdrawn: neither broadening nor asymmetry subtitle remains");
        const u = named(box, "peak.broad_gauss_u");
        const v = named(box, "peak.broad_gauss_v");
        const w = named(box, "peak.broad_gauss_w");
        const x = named(box, "peak.broad_lorentz_x");
        const y = named(box, "peak.broad_lorentz_y");
        closeEnough(u.mapToItem(box, 0, 0).y, v.mapToItem(box, 0, 0).y, "Gaussian U/V share a row");
        closeEnough(v.mapToItem(box, 0, 0).y, w.mapToItem(box, 0, 0).y, "Gaussian V/W share a row");
        closeEnough(x.mapToItem(box, 0, 0).y, y.mapToItem(box, 0, 0).y, "Lorentzian X/Y share a row");
        verify(x.mapToItem(box, 0, 0).y > u.mapToItem(box, 0, 0).y, "final peak feedback: Gaussian and Lorentzian families have distinct rows");
    }
    function test_plural_loops_and_linked_structure_icons() {
        open();
        pane("experiment", "basic");
        const linked = group("linked_structure");
        compare(linked.title, "Linked structures (1)", "idea 19: linked-structure loop title is plural");
        const icon = named(linked, "linkedStructure.color.0");
        compare(icon.icon, "layer-group", "idea 20: linked row carries a structure icon");
        const linkedColor = String(icon.iconColor);
        pane("structure", "basic");
        const structures = group("structures");
        compare(String(named(structures, "structures.color.0").iconColor), linkedColor, "ideas 12/20: linked row uses its structure's datablock colour");
        pane("experiment", "extras");
        compare(group("preferred_orientation").title, "Preferred orientations (1)", "idea 19: preferred-orientation loop title is plural");
    }
    function test_datablock_and_analysis_iconified_names() {
        open();
        pane("structure", "basic");
        const structureIcon = named(group("structures"), "structures.color.0");
        compare(structureIcon.icon, "layer-group", "idea 12: structure table has a datablock icon");
        const structureColor = String(structureIcon.iconColor);
        // Independent gui-components v0.9.1 Colors.qml model palette: orange.
        compare(structureColor.toLowerCase(), Style.Colors.isDarkPalette ? "#ffcc80" : "#ff9800", "idea 12: first structure uses the upstream model orange");
        pane("experiment", "basic");
        const experimentIcon = named(group("experiments"), "experiments.color.0");
        compare(experimentIcon.icon, "microscope", "idea 12: experiment table has a datablock icon");
        // Independent gui-components v0.9.1 chartForegroundsExtra[2]: light blue.
        compare(String(experimentIcon.iconColor).toLowerCase(), Style.Colors.isDarkPalette ? "#81d4fa" : "#03a9f4", "idea 12: first experiment uses the upstream measured-data blue");
        verify(String(experimentIcon.iconColor) !== structureColor, "idea 12: structure and experiment colours are distinct");
        pane("analysis", "basic");
        const rows = Probe.rows(Session.project.parameters);
        const occupancy = rows.find(row => row.parameter && row.parameter.name === "occupancy");
        verify(occupancy !== undefined, "idea 12: independent .edi atom occupancy is represented");
        const helper = Qt.createQmlObject('import QtQuick; import edi.app; QtObject { function pieces(item) { return ParameterNames.segments(item); } }', appWindow);
        const pieces = helper.pieces(occupancy.parameter);
        compare(pieces[0].icon, "layer-group", "idea 12: Analysis name starts with the datablock icon");
        compare(String(pieces[0].color), structureColor, "idea 12: Analysis reuses the datablock colour");
        verify(pieces.some(piece => piece.icon === "atom") && pieces.some(piece => piece.icon === "fill"), "idea 12: atom occupancy name includes atom and occupancy icons");
        verify(pieces.some(piece => piece.text === occupancy.parameter.rowLabel), "idea 12: Analysis name includes its atom label");
        helper.destroy();
    }
    function test_messages_counter_view_dismiss_and_reopen() {
        open("messages");
        pane("project", "basic");
        const messages = Session.loadWarnings;
        const rows = Probe.rows(messages);
        verify(rows.some(row => row.message.indexOf('unsupported _minimizer.type "bumps (lm)"') >= 0), "idea 26: independently declared unsupported minimizer becomes a message");
        verify(rows.some(row => row.message.indexOf('unsupported _calculator.type "cryspy"') >= 0), "idea 26: independently declared unsupported calculator becomes a message");
        verify(rows.some(row => row.severity === "error"), "idea 25: invalid zero-endpoint calculation becomes a central error");
        const status = findChild(appWindow, "statusBar.warnings");
        verify(status !== null && status.visible, "idea 24: central status item is present");
        compare(Number(status.valueText), messages.count, "idea 24: status counter follows listed messages");
        verify(status.alert, "idea 24: unread messages color the status value red");
        verify(Ui.text(Ui.page(appWindow)).indexOf("Warnings") < 0, "idea 24: Project description has no Warnings row");
        const point = Ui.clickPoint(status);
        verify(point !== null, "idea 24: message status item accepts actual input");
        mouseClick(status, point.x, point.y);
        const dialog = findChild(appWindow, "warnings");
        verify(dialog !== null, "idea 24: clicking status opens the central dialog");
        tryCompare(dialog, "opened", true, 2000, "idea 24: Messages popup opens");
        compare(messages.unviewedCount, 0, "idea 24: opening marks messages viewed");
        compare(status.alert, false, "idea 24: viewed messages clear the red alert");
        const count = messages.count;
        const dismiss = named(dialog.contentItem, "warnings.dismiss.0");
        mouseClick(dismiss, dismiss.width / 2, dismiss.height / 2);
        compare(messages.count, count - 1, "idea 24: each message can be dismissed independently");
        const all = findChild(dialog, "warnings.dismissAll");
        verify(all !== null && all.enabled, "idea 24: Dismiss all is enabled for remaining messages");
        mouseClick(all, all.width / 2, all.height / 2);
        compare(messages.count, 0, "idea 24: Dismiss all removes all messages");
        compare(Number(status.valueText), 0, "idea 24: empty list still has a zero counter");
        compare(all.enabled, false, "idea 24: empty list disables Dismiss all");
        tryVerify(() => findChild(dialog, "warnings.empty").visible, 2000, "final Messages feedback: empty state is visible");
        dialog.close();
        Session.closeProject();
        open("messages");
        verify(messages.count >= 3 && messages.unviewedCount > 0, "ideas 24–26: reopening independently unsupported project raises fresh messages");
    }
    function test_messages_geometry_and_neutral_experiment() {
        open("messages");
        pane("experiment", "basic");
        verify(Ui.text(Ui.page(appWindow)).indexOf("Calculation refused") < 0, "idea 25: Experiment has only a neutral placeholder, no local red diagnostic");
        const dialog = findChild(appWindow, "warnings");
        verify(dialog !== null, "ideas 24/25: shared dialog exists");
        dialog.open();
        tryCompare(dialog, "opened", true, 2000, "ideas 24/25: shared dialog opens");
        const list = findChild(dialog, "warnings.list");
        verify(list !== null && list.clip, "final Messages feedback: long message lists are clipped and scrollable");
        const width = dialog.width;
        const height = dialog.height;
        verify(width > appWindow.width / 4 && width < appWindow.width, "final Messages feedback: readable fixed width fits the window");
        verify(height < appWindow.height, "final Messages feedback: height fits within the app window");
        Session.loadWarnings.dismissAll();
        verify(waitForPolish(appWindow, 2000), "final Messages feedback: empty-list geometry settles");
        closeEnough(dialog.width, width, "Messages width stays fixed when emptied");
        verify(dialog.height < height && list.height > 0, "final Messages feedback: height follows rows with a nonzero empty row");
        verify(Review.descendants(list.parent).some(item => item.border && item.border.width > 0 && item.width >= list.width && item.height >= list.height && item.z >= list.z), "final Messages feedback: unbroken frame covers the list including its empty state");
        Session.closeProject();
        open("overflow");
        tryVerify(() => list.contentHeight > list.height, 2000, "final Messages feedback: overflowing rows are taller than the bounded list viewport");
        verify(dialog.height < appWindow.height, "final Messages feedback: overflowing messages keep the dialog within the app window");
        closeEnough(dialog.width, width, "overflow does not widen the Messages dialog");
        list.positionViewAtEnd();
        tryVerify(() => list.contentY > 0, 2000, "final Messages feedback: overflowing messages can actually scroll");
    }
    function test_demo_example_has_three_messages() {
        verify(Session.openExample("pd-neut-tof_fe_pseudo-voigt"), "idea 26: the intentionally unsupported bundled example opens");
        verify(Session.loadWarnings.count >= 3, "idea 26 final widening: example has calculator, minimizer and another unsupported-value message");
        verify(Session.needsSaveAs, "final saving feedback: an example's first Save requires Save as");
    }
    function test_messages_status_counts_unviewed_messages() {
        open("messages");
        pane("project", "basic");
        const status = findChild(appWindow, "statusBar.warnings");
        verify(status !== null, "idea 24: Messages counter is always present");
        compare(Number(status.valueText), Session.loadWarnings.unviewedCount, "idea 24: status counter counts not-yet-viewed messages");
        const point = Ui.clickPoint(status);
        verify(point !== null, "idea 24: Messages counter is actionable");
        mouseClick(status, point.x, point.y);
        const dialog = findChild(appWindow, "warnings");
        tryCompare(dialog, "opened", true, 2000, "idea 24: opening displays the message list");
        tryCompare(Session.loadWarnings, "unviewedCount", 0, 2000, "idea 24: opening marks the warnings viewed");
        compare(Number(status.valueText), 0, "idea 24: the not-viewed count is zero after viewing messages");
    }
    function test_save_roundtrip_and_modified_state() {
        open();
        compare(Session.project.modified, false, "final saving feedback: opening starts with no unsaved edits");
        Session.project.description = "independent  save witness";
        compare(Session.project.modified, true, "final saving feedback: an edit marks the project modified");
        const target = Qt.resolvedUrl("../../../build/-acceptance/saved");
        verify(Session.saveAs(target), "final saving feedback: Save as writes the project through core");
        compare(Session.project.modified, false, "final saving feedback: successful Save clears modified state");
        compare(Session.needsSaveAs, false, "final saving feedback: subsequent Save uses the chosen directory");
        Session.project.description = "independent  second save";
        verify(Session.save(), "final saving feedback: later Save writes to the chosen directory");
        const before = [Session.project.name, Session.project.description, Session.project.currentStructure.cell.lengthA.value];
        Session.closeProject();
        verify(Session.openProject(target), "final saving feedback: the saved project reopens");
        compare(Session.project.name, before[0], "final saving feedback: project name round-trips");
        compare(Session.project.description, before[1], "final saving feedback: edited description round-trips");
        compare(Session.project.currentStructure.cell.lengthA.value, before[2], "final saving feedback: stored structural parameter round-trips");
        compare(Session.project.modified, false, "final saving feedback: reopened save starts unmodified");
    }
    // Route C: development hub decision-records 2026-10-02, b4ca288be. The save-as-crysta
    // gate moves to the crysta writer/seeds follow-up. The calculator load-warning
    // checks above and the ordinary save round-trip remain  requirements.
}
