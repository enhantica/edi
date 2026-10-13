// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtCore
import QtTest
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render
import EdiAcceptance 1.0

Item {
    id: surface
    width: 1300
    height: 900
    Component {
        id: mainFactory
        Main {}
    }
    Component {
        id: dialogFactory
        AppPreferencesDialog {}
    }
    Component {
        id: projectFactory
        ProjectPage {}
    }
    Component {
        id: structureFactory
        StructurePage {}
    }
    Component {
        id: experimentFactory
        ExperimentPage {}
    }
    Component {
        id: analysisFactory
        AnalysisPage {}
    }
    Component {
        id: reportFactory
        ReportPage {}
    }
    TestCase {
        name: "ReportSettings"
        when: windowShown
        readonly property url location: Globals.Vars.settingsFile
        function initTestCase() {
            surface.Window.window.width = surface.width;
            surface.Window.window.height = surface.height;
        }
        function cleanup() {
            Preferences.dialogShown = false;
            Session.closeProject();
        }
        function test_store_uses_the_named_ini_inside_an_isolated_root() {
            compare(SettingsProof.fileName(location), "EasyDiffraction.ini", "The one desktop app store has the declared application name and INI format");
            compare(SettingsProof.parentName(location), "EasyScience", "The desktop store uses QSettings user scope under the EasyScience organization");
            verify(SettingsProof.temporary(location), "The actual GUI test continues to use its own fresh configuration directory");
        }
        function test_preferences_projects_holds_only_new_defaults() {
            const dialog = createTemporaryObject(dialogFactory, surface);
            verify(dialog !== null, "The real Preferences dialog exists for the new Projects tab");
            Preferences.dialogShown = true;
            const tabs = Render.descendants(dialog).filter(item => item.text && ["Appearance", "Projects"].includes(item.text) && item.checkable);
            compare(tabs.length, 2, "Preferences has both Appearance and Projects tabs");
            const projects = tabs.find(item => item.text === "Projects");
            mouseClick(projects, projects.width / 2, projects.height / 2);
            verify(waitForPolish(dialog.contentItem), "The actual Projects page completes its layout");
            const texts = Render.texts(dialog).map(item => item.text.replace(/:$/, ""));
            verify(texts.includes("New projects' uncertainties") && texts.includes("New reports' libraries"), "Projects exposes uncertainty and report-library defaults together");
            verify(!texts.includes("Colour scheme"), "The Projects tab contains new-object defaults while the scheme choice belongs to Appearance");
        }
        function test_scheme_and_library_defaults_persist_without_changing_an_open_project() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "A real project supplies the modified-state control");
            const modified = Session.project.modified;
            verify(typeof Preferences.colourScheme === "string" && typeof Preferences.newReportLibraries === "string", "Preferences exposes the two declared string-token defaults");
            Preferences.colourScheme = "colourBlindSafe";
            Preferences.newReportLibraries = "embedded";
            tryVerify(() => SettingsProof.value(location, "Appearance", "colourScheme") === "colourBlindSafe" && SettingsProof.value(location, "Projects", "newReportLibraries") === "embedded", 2000, "Changing the actual Preferences properties writes both tokens to their declared store groups");
            const restored = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property string scheme: Preferences.colourScheme; property string libraries: Preferences.newReportLibraries }');
            verify(!restored.error, "A fresh configured QML engine reloads the actual Preferences singleton");
            compare(restored.scheme, "colourBlindSafe", "A fresh engine restores the colour scheme from Appearance");
            compare(restored.libraries, "embedded", "A fresh engine restores the new-report libraries default from Projects");
            compare(Session.project.modified, modified, "Changing application defaults never modifies the open project");
        }
        function test_legacy_settings_carry_over_once_and_preserve_new_values() {
            const old = SettingsProof.legacy(location);
            verify(old !== location, "The migration fixture distinguishes the retained old file from the named new store");
            SettingsProof.erase(location, "Edi.Preferences", "toolTips");
            SettingsProof.seed(old, "Edi.Preferences", "toolTips", false);
            const code = 'import QtQuick; import edi.app; QtObject { property bool toolTips: Preferences.toolTips }';
            const first = SettingsProof.restart(code);
            verify(!first.error, "The migration runs through a fresh production engine setup");
            compare(first.toolTips, false, "The first engine carries an absent tooltip key from the old settings.ini");
            compare(SettingsProof.value(old, "Edi.Preferences", "toolTips"), false, "Migration leaves the old settings file and value intact");
            SettingsProof.seed(location, "Edi.Preferences", "toolTips", true);
            const second = SettingsProof.restart(code);
            verify(!second.error, "The second engine start reuses the production store");
            compare(second.toolTips, true, "A second start never overwrites a new-store key with the old value");
        }
        function test_window_geometry_restores_and_relocates_an_offscreen_position() {
            for (const entry of [["x", 60], ["y", 40], ["width", 1100], ["height", 700]])
                SettingsProof.seed(location, "Window", entry[0], entry[1]);
            const restored = createTemporaryObject(mainFactory, null);
            verify(restored !== null, "A fresh production Main restores its window from the actual app store");
            compare(JSON.stringify([restored.x, restored.y, restored.width, restored.height]), JSON.stringify([60, 40, 1100, 700]), "Window restart retains nontrivial logical-pixel position and size");
            restored.destroy();
            SettingsProof.seed(location, "Window", "x", 5000);
            const moved = createTemporaryObject(mainFactory, null);
            verify(moved !== null, "A fresh production Main handles an unreachable saved position");
            const screen = SettingsProof.screen();
            verify(moved.x >= screen.x && moved.x < screen.x + screen.width, "An offscreen saved position moves onto the primary screen rather than remaining at x 5000");
        }
        function test_each_workflow_page_exposes_a_settings_tab_data() {
            return ["project", "structure", "experiment", "analysis", "report"].map(name => ({
                        tag: name,
                        page: name
                    }));
        }
        function test_each_workflow_page_exposes_a_settings_tab(data) {
            const factories = {
                project: projectFactory,
                structure: structureFactory,
                experiment: experimentFactory,
                analysis: analysisFactory,
                report: reportFactory
            };
            const page = createTemporaryObject(factories[data.page], surface, {
                width: 1200,
                height: 800
            });
            verify(page !== null && waitForPolish(page), "The actual workflow page lays out before checking its fourth sidebar tab");
            const tab = Render.descendants(page).find(item => item.text === "Settings" && item.checkable);
            verify(tab !== undefined, "Every workflow page exposes a real Settings tab beside Main, Extras and Text");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            tryCompare(tab, "checked", true, 1000, "The Settings tab accepts actual pointer input");
        }
        function choose(control, index) {
            verify(control !== undefined && control.enabled, "The real page setting is enabled before actual pointer input");
            mouseClick(control, control.width / 2, control.height / 2);
            tryVerify(() => control.popup.opened, 1000, "The actual setting popup opens");
            const list = control.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            list.forceLayout();
            const entry = list.itemAtIndex(index);
            verify(entry !== null, "The selected setting token has a real popup delegate");
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(control, "currentIndex", index, 1000, "Actual pointer input selects the declared setting token");
        }
        function test_analysis_log_axis_and_scan_updates_are_page_settings_without_model_edits() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_scan-3f"), "The declared scan opens for Analysis view settings");
            const original = Session.project.analysis.text.text;
            const modified = Session.project.modified;
            Preferences.scanPatternUpdates = 0;
            const page = createTemporaryObject(analysisFactory, surface, {
                width: 1200,
                height: 800,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Analysis page lays out its view controls");
            const tab = Render.descendants(page).find(item => item.text === "Settings" && item.checkable);
            verify(tab !== undefined, "Analysis exposes the real Settings tab after moving view options from Extras");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            tryCompare(tab, "checked", true, 1000, "The actual Analysis Settings tab opens through pointer input");
            let y = null;
            tryVerify(() => {
                y = Render.descendants(page).find(item => item.visible && item.popup && typeof item.textAt === "function" && item.count >= 3 && /^log/i.test(item.textAt(2)));
                return y !== undefined;
            }, 1000, "The y-axis selector lives in the shown Settings pane");
            choose(y, 2);
            tryVerify(() => SettingsProof.value(location, "Analysis", "yAxis") === "log", 2000, "Selecting log persists the control's token in the Analysis store group");
            tryVerify(() => SettingsProof.value(location, "Analysis", "scanPatternUpdates") === 0, 2000, "The moved pattern-update option retains its value in the Analysis group");
            compare(Session.project.analysis.text.text, original, "Changing page settings leaves the analysis model text unchanged");
            compare(Session.project.modified, modified, "Changing y scale and scan redraw policy never modifies the project");
            const restored = SettingsProof.restart('import QtQuick; import QtCore; import EasyApplication.Gui.Globals as Globals; QtObject { property Settings settings: Settings { location: Globals.Vars.settingsFile; category: "Analysis"; property string yAxis: "linear" }; property string axis: settings.yAxis }');
            verify(!restored.error, "A fresh configured engine reads the saved page group");
            compare(restored.axis, "log", "The log token survives destruction of the original Settings control");
        }
        function test_report_library_preference_seeds_only_created_projects() {
            verify(typeof Preferences.newReportLibraries === "string", "The Projects preference exposes the new-report libraries token");
            Preferences.newReportLibraries = "embedded";
            verify(Session.createProject("created_report", "Independent new-project default witness"), "Creating a project applies the declared new-report preference");
            compare(Session.project.report.embedLibraries, true, "Only a newly created project's Embed option starts from the Embedded preference");
            const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            verify(Session.saveAs(url), "The created project's seeded report option is saved for an independent reopen");
            verify(/_report\.html_offline\s+true/.test(SettingsProof.text(url, "project.edi")), "Creation writes the embedded default into project.edi");
            Session.closeProject();
            Preferences.newReportLibraries = "online";
            verify(Session.openProject(url), "The newly created project reopens under a different preference");
            compare(Session.project.report.embedLibraries, true, "A project's explicit embedded option wins over the new-project preference");
            Session.closeProject();
            Preferences.newReportLibraries = "embedded";
            const existing = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            verify(Session.openProject(existing), "An existing project without html_offline opens under the Embedded preference");
            compare(Session.project.report.embedLibraries, false, "Opening a project with no html_offline reads false independently of Preferences");
            verify(Session.save(), "An unchanged existing project can be saved without adding a default");
            verify(!/_report\.html_offline/.test(SettingsProof.text(existing, "project.edi")), "A save never introduces an absent html_offline item");
            Session.project.report.embedLibraries = true;
            compare(Session.project.modified, true, "Changing Embed is an undoable project edit rather than a transient report session option");
            compare(Preferences.newReportLibraries, "embedded", "A report edit leaves the new-project preference unchanged");
            Session.project.undo();
            compare(Session.project.report.embedLibraries, false, "Undo restores the prior project-owned Embed option");
        }
        function test_new_project_rule_migrates_to_projects_without_changing_an_existing_rule() {
            SettingsProof.erase(location, "Projects", "newProjectSuRule");
            SettingsProof.seed(SettingsProof.legacy(location), "Edi.Preferences", "newProjectSuRule", "iucr_99");
            const restored = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property string rule: Preferences.newProjectSuRule }');
            verify(!restored.error, "A fresh production Preferences singleton carries the old new-project rule");
            compare(restored.rule, "iucr_99", "The old two-digit default carries to Projects without silently resetting it");
            compare(SettingsProof.value(location, "Projects", "newProjectSuRule"), "iucr_99", "The migrated default belongs to Projects in the new store");
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "An existing project's own uncertainty rule supplies the independence control");
            const rule = Session.project.suRule;
            const modified = Session.project.modified;
            Preferences.newProjectSuRule = "iucr_99";
            compare(Session.project.suRule, rule, "An existing project's uncertainty rule remains its own after changing the new-project default");
            compare(Session.project.modified, modified, "A new-project preference never modifies an existing project");
        }
        function scanFixture() {
            const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
            verify(String(url) !== "", "Selection tests use an owned temporary copy of the independent three-file scan");
            let text = SettingsProof.text(url, "analysis/analysis.edi");
            text += "\n_sequential_fit.template_file all594687.dat\n";
            verify(SettingsProof.write(url, "analysis/analysis.edi", text), "The selection fixture declares an explicit unchanged template dataset");
            return url;
        }
        function selectedFile() {
            return Probe.rows(Session.project.experiments)[Session.project.currentExperimentIndex].file;
        }
        function test_scan_selection_restores_by_filename_data() {
            return [
                {
                    tag: "same-order",
                    reverse: false
                },
                {
                    tag: "reordered",
                    reverse: true
                }
            ];
        }
        function test_scan_selection_restores_by_filename(data) {
            const url = scanFixture();
            verify(Session.openProject(url), "The independent scan opens by its owned absolute project path");
            Session.project.currentExperimentIndex = 2;
            tryCompare(Session.project, "calculating", false, 10000, "The selected third dataset finishes its lazy projection");
            compare(selectedFile(), "all594842.dat", "The selected witness is the third dataset's stable file identity");
            const template = Probe.rows(Session.project.experiments)[Session.project.templateIndex].file;
            Session.closeProject();
            if (data.reverse) {
                const text = SettingsProof.text(url, "analysis/analysis.edi").replace("_sequential_fit.reverse false", "_sequential_fit.reverse true");
                verify(SettingsProof.write(url, "analysis/analysis.edi", text), "The reorder escape changes the listing without changing dataset identities");
            }
            verify(Session.openProject(url), "The same project path reopens after selection and optional reordering");
            tryCompare(Session.project, "calculating", false, 10000, "Restored selection finishes its real dataset projection");
            compare(selectedFile(), "all594842.dat", "A scan selection restores by file name even when the saved row index points at another dataset");
            compare(Probe.rows(Session.project.experiments)[Session.project.templateIndex].file, template, "Restoring a selected dataset never replaces the scan template");
            compare(Session.project.modified, false, "Restoring a view leaves the reopened project unmodified");
        }
        function test_missing_stored_dataset_falls_back_to_the_template_without_a_message() {
            const url = scanFixture();
            verify(Session.openProject(url), "The missing-file selection fixture opens its real scan catalogue");
            Session.project.currentExperimentIndex = 2;
            tryCompare(Session.project, "calculating", false, 10000, "The stored missing-file witness was a real selected dataset");
            compare(selectedFile(), "all594842.dat", "The missing-file witness starts from the file that will be removed");
            const warnings = Session.loadWarnings.count;
            Session.closeProject();
            verify(SettingsProof.remove(url, "experiments/d20_scan/all594842.dat"), "The escape removes only the owned selected data file");
            verify(Session.openProject(url), "The scan reopens with a missing last-selected file");
            tryCompare(Session.project, "calculating", false, 10000, "The template fallback completes its real projection");
            compare(selectedFile(), "all594687.dat", "A missing stored dataset falls back to the unchanged explicitly declared template");
            compare(Session.project.currentExperimentIndex, Session.project.templateIndex, "The fallback is the template dataset rather than an arbitrary stale row");
            compare(Session.loadWarnings.count, warnings, "A missing stored view selection adds no message to the project's existing diagnostics");
            compare(Session.project.modified, false, "The fallback changes the view without modifying the model");
        }
        function test_recent_project_order_and_last_path_live_in_the_projects_store() {
            const initialized = RecentProjects.rows.count;
            const urls = [];
            for (let i = 0; i < 3; ++i) {
                const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
                verify(String(url) !== "" && Session.openProject(url), "Each recent-project witness opens a different owned absolute path");
                urls.push(SettingsProof.localPath(url));
            }
            const wanted = urls.slice().reverse();
            tryVerify(() => {
                const stored = SettingsProof.value(location, "Projects", "recent");
                return Array.isArray(stored) && JSON.stringify(stored.slice(0, 3)) === JSON.stringify(wanted);
            }, 2000, "Opening A then B then C stores recent paths in C B A order under Projects");
            compare(SettingsProof.value(location, "Projects", "last"), urls[2], "Projects last records the actual last-opened absolute path");
            const restored = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property var paths: RecentProjects.paths() }');
            verify(!restored.error, "A fresh production RecentProjects singleton reloads the history store");
            compare(JSON.stringify(restored.paths.slice(0, 3)), JSON.stringify(wanted), "Restart preserves the actual recent-project order");
        }
        function test_desktop_preferences_exposes_the_store_path_and_reset_actions() {
            const dialog = createTemporaryObject(dialogFactory, surface);
            verify(dialog !== null, "The Preferences store controls belong to the actual dialog");
            const texts = Render.descendants(dialog).filter(item => typeof item.text === "string").map(item => item.text);
            verify(texts.some(text => text.includes(String(location).replace(/^file:\/\//, ""))), "Desktop Preferences shows the entire application-settings path");
            verify(texts.includes("Open folder") && texts.includes("Reset to defaults"), "Desktop Preferences exposes both store actions");
        }
    }
}
