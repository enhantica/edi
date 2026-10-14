// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtCore
import QtTest
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render
import EdiAcceptance 1.0

Item {
    id: surface
    width: 1300
    height: 900
    FontMetrics {
        id: fontMeasure
    }
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
            SettingsProof.endAnimationClock();
            Preferences.dialogShown = false;
            Session.closeProject();
        }
        function test_preferences_share_columns_without_truncating_any_item_data() {
            return [
                {
                    tag: "light",
                    dark: false
                },
                {
                    tag: "dark",
                    dark: true
                }
            ];
        }
        function test_preferences_share_columns_without_truncating_any_item(data) {
            const oldTheme = EaStyle.Colors.theme;
            EaStyle.Colors.theme = data.dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
            const dialog = createTemporaryObject(dialogFactory, surface);
            verify(dialog !== null, "The layout gate creates the actual Preferences dialog");
            Preferences.dialogShown = true;
            tryCompare(dialog, "opened", true, 2000, "The real Preferences dialog opens before measuring its tabs");
            verify(SettingsProof.beginAnimationClock(), "The public Qt animation clock settles each actual Preferences slide before geometric measurements");
            const tabs = ["Prompts", "Updates", "Appearance", "Projects", "Experimental", "Develop"];
            const labels = [["Enable tool tips:", "Enable user guides:"], ["Check on application start:"], ["Theme:", "Colour scheme:", "Sidebar:", "Auto collapse:"], ["New projects' uncertainties:", "New reports' libraries:"], ["Zoom:", "Language:"], ["Logging to:", "Logging level:", "Engine threads:", "Diagnostics:", "Settings:"]];
            const failures = [], labelWidths = [], boxWidths = [], boxXs = [], labelXs = [];
            function inkTop(item) {
                const at = item.mapToItem(dialog.contentItem, 0, 0);
                const top = item.topPadding || 0, bottom = item.bottomPadding || 0;
                const ink = typeof item.paintedHeight === "number" ? item.paintedHeight : item.height - top - bottom;
                const extra = Math.max(0, item.height - top - bottom - ink);
                return at.y + top + (item.verticalAlignment === Text.AlignVCenter ? extra / 2 : item.verticalAlignment === Text.AlignBottom ? extra : 0);
            }
            for (let t = 0; t < tabs.length; ++t) {
                const buttons = Render.descendants(dialog.contentItem).filter(item => item.text === tabs[t] && typeof item.checked === "boolean" && typeof item.clicked === "function");
                compare(buttons.length, 1, "The actual Preferences tab button is found uniquely by its visible title " + tabs[t]);
                mouseClick(buttons[0], buttons[0].width / 2, buttons[0].height / 2);
                tryCompare(buttons[0], "checked", true, 2000, "Pointer input opens the Preferences " + tabs[t] + " tab");
                wait(0);
                verify(SettingsProof.stepAnimationClock(2000), "The actual Preferences tab slide completes on the controlled Qt clock");
                wait(0);
                verify(SettingsProof.stepAnimationClock(2000), "The public Qt clock also settles slides queued after the click event");
                wait(0);
                verify(waitForPolish(dialog.contentItem), "The settled Preferences tab geometry is polished before observing widths and text tops");
                function inside(item) {
                    const at = item.mapToItem(dialog.contentItem, 0, 0);
                    return item.visible && at.x >= 0 && at.y >= 0 && at.x + item.width <= dialog.contentItem.width + 0.5 && at.y + item.height <= dialog.contentItem.height + 0.5;
                }
                tryVerify(() => labels[t].every(text => Render.texts(dialog.contentItem).some(item => item.text === text && inside(item))), 2500, "Every declared row of " + tabs[t] + " finishes sliding wholly into the actual popup; actual " + JSON.stringify(Render.texts(dialog.contentItem).filter(item => labels[t].includes(item.text)).map(item => ({
                            text: item.text,
                            visible: item.visible,
                            point: item.mapToItem(dialog.contentItem, 0, 0),
                            width: item.width,
                            height: item.height,
                            popup: [dialog.contentItem.width, dialog.contentItem.height]
                        }))));
                const all = Render.descendants(dialog.contentItem).filter(inside);
                const combos = all.filter(item => typeof item.textAt === "function" && item.popup && typeof item.count === "number");
                for (const combo of combos) {
                    const textItem = combo.contentItemLabel || combo.contentItem;
                    fontMeasure.font = textItem.font;
                    let needed = 0;
                    for (let i = 0; i < combo.count; ++i)
                        needed = Math.max(needed, fontMeasure.advanceWidth(combo.textAt(i)));
                    const available = textItem.width - (textItem.leftPadding || 0) - (textItem.rightPadding || 0);
                    if (available + 0.5 < needed)
                        failures.push(tabs[t] + " " + combo.objectName + " longest item needs " + needed + " text pixels, has " + available + "; control=" + combo.width + "; arrow=" + combo.indicator.width);
                    boxWidths.push(combo.width);
                    boxXs.push(combo.mapToItem(dialog.contentItem, 0, 0).x);
                }
                const sideButtons = all.filter(item => typeof item.clicked === "function" && ["Check now", "Show", "Open folder", "Reset to defaults"].includes(item.text));
                for (const button of sideButtons)
                    boxWidths.push(button.width);
                for (const title of labels[t]) {
                    const label = Render.texts(dialog.contentItem).find(item => item.text === title && inside(item));
                    labelWidths.push(label.width);
                    labelXs.push(label.mapToItem(dialog.contentItem, 0, 0).x);
                    let parent = label.parent;
                    const siblings = parent.children.filter(item => item !== label && item.mapToItem(parent, 0, 0).x >= label.x + label.width - 0.5);
                    let control = siblings.sort((a, b) => Math.abs(a.y - label.y) - Math.abs(b.y - label.y))[0];
                    if (!control) {
                        failures.push(tabs[t] + " has no right-hand control for " + title);
                        continue;
                    }
                    // A disabled control can sit in a hover/tooltip wrapper.
                    // Measure its real checkbox or button, preserving the wrapper's layout.
                    const actionable = Render.descendants(control).find(item => item.indicator && item.checked !== undefined || item.rowButton === true);
                    const firstInk = Render.texts(control).find(item => typeof item.text === "string" && item.text.length > 0);
                    // A Settings column begins with its path label, then buttons.
                    // Unwrap a hover wrapper only when it adds no earlier text line.
                    if (actionable && (!firstInk || Render.descendants(actionable).includes(firstInk)))
                        control = actionable;
                    const isButton = control.rowButton === true || (typeof control.clicked === "function" && !control.indicator);
                    const isTextlessCheck = control.checked !== undefined && control.indicator && !control.text;
                    if (isButton || isTextlessCheck) {
                        // A textless checkbox has no text line: its indicator centre
                        // supplies the alignment. A button's face centre supplies it.
                        const target = isTextlessCheck ? control.indicator : control;
                        const targetCentre = target.mapToItem(dialog.contentItem, 0, target.height / 2).y;
                        const inkHeight = typeof label.paintedHeight === "number" ? label.paintedHeight : label.height - (label.topPadding || 0) - (label.bottomPadding || 0);
                        const labelCentre = inkTop(label) + inkHeight / 2;
                        if (Math.abs(labelCentre - targetCentre) > 1)
                            failures.push(tabs[t] + " " + title + " actual label ink centre=" + labelCentre + "; " + (isTextlessCheck ? "checkbox indicator" : "button face") + " centre=" + targetCentre + "; control=" + control.objectName);
                    } else {
                        const first = control.contentItemLabel || control.contentItem || Render.texts(control)[0] || control;
                        if (Math.abs(inkTop(label) - inkTop(first)) > 1)
                            failures.push(tabs[t] + " " + title + " actual label text top=" + inkTop(label) + "; actual control first text top=" + inkTop(first) + "; control=" + control.objectName);
                    }
                }
            }
            function same(values, name) {
                if (values.length === 0 || Math.max(...values) - Math.min(...values) > 1)
                    failures.push(name + " actual=" + JSON.stringify(values));
            }
            same(labelWidths, "One label-column width across every tab");
            same(boxWidths, "Every combo box and row button shares one control width");
            same(boxXs, "The control column starts at the same place on every tab");
            same(labelXs, "The label column starts at the same place on every tab");
            SettingsProof.endAnimationClock();
            EaStyle.Colors.theme = oldTheme;
            compare(failures.length, 0, "Preferences keeps one label/control layout across all tabs, displays every longest item plus its arrow, and top-aligns labels with the control first line; actual " + failures.join("; "));
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
            tryCompare(dialog, "opened", true, 2000, "The actual Preferences popup opens before its named tabs are inspected");
            const appearance = findChild(dialog, "preferences.tab.appearance");
            const projects = findChild(dialog, "preferences.tab.projects");
            verify(appearance !== null && projects !== null, "Preferences exposes preferences.tab.appearance and preferences.tab.projects; actual " + JSON.stringify({
                appearance: appearance !== null,
                projects: projects !== null
            }));
            mouseClick(projects, projects.width / 2, projects.height / 2);
            verify(waitForPolish(dialog.contentItem), "The actual Projects page completes its layout");
            function visibleTexts() {
                return Render.texts(dialog.contentItem).filter(item => {
                    const at = item.mapToItem(dialog.contentItem, 0, 0);
                    return at.x >= 0 && at.y >= 0 && at.x + item.width <= dialog.contentItem.width + 0.5 && at.y + item.height <= dialog.contentItem.height + 0.5;
                }).map(item => item.text.replace(/:$/, ""));
            }
            tryVerify(() => visibleTexts().includes("New projects' uncertainties") && visibleTexts().includes("New reports' libraries"), 2000, "The opened preferences.tab.projects finishes sliding its two default labels into view; initial visible text " + JSON.stringify(visibleTexts()));
            const texts = visibleTexts();
            verify(!texts.includes("Colour scheme"), "The opened preferences.tab.projects keeps Colour scheme on Appearance; visible text " + JSON.stringify(texts));
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
            const tab = findChild(page, "sideBar.tab.settings");
            verify(tab !== null, "The actual " + data.page + " page exposes sideBar.tab.settings beside Main, Extras and Text; actual " + tab);
            const populated = data.page === "experiment" || data.page === "analysis";
            compare(tab.enabled, populated, "Owner decision 55c4dbd07: each empty Settings tab is disabled and each populated tab stays actionable; page=" + data.page);
            const checked = tab.checked;
            mouseClick(tab, tab.width / 2, tab.height / 2);
            if (populated)
                tryCompare(tab, "checked", true, 1000, "A populated Settings tab accepts actual pointer input");
            else
                compare(tab.checked, checked, "Pointer input cannot activate an empty Settings tab");
        }
        function choose(control, index) {
            verify(control !== undefined && control.enabled, "The real page setting is enabled before actual pointer input");
            tryVerify(() => {
                const at = control.mapToItem(surface, 0, 0);
                return at.x >= 0 && at.y >= 0 && at.x + control.width <= surface.width && at.y + control.height <= surface.height;
            }, 2000, "The actual " + control.objectName + " finishes sliding inside the test window before pointer input");
            verify(waitForRendering(control), "The actual " + control.objectName + " is rendered before opening its popup");
            mouseClick(control, control.width / 2, control.height / 2);
            tryVerify(() => control.popup.opened, 1000, "Pointer input opens " + control.objectName + ".popup; initial opened " + control.popup.opened + "; control centre " + JSON.stringify(control.mapToItem(surface, control.width / 2, control.height / 2)));
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
            const tab = findChild(page, "sideBar.tab.settings");
            verify(tab !== null, "The actual Analysis page exposes sideBar.tab.settings; actual " + tab);
            mouseClick(tab, tab.width / 2, tab.height / 2);
            tryCompare(tab, "checked", true, 1000, "The actual Analysis Settings tab opens through pointer input");
            const chartGroup = findChild(page, "group.chartSettings");
            verify(chartGroup !== null, "Analysis Settings exposes group.chartSettings; actual " + chartGroup);
            if (chartGroup.collapsed)
                mouseClick(chartGroup.titleArea, chartGroup.titleArea.width / 2, chartGroup.titleArea.height / 2);
            const y = findChild(page, "settings.chart.yScale");
            verify(y !== null, "Analysis Settings exposes settings.chart.yScale; actual " + y);
            tryVerify(() => y.visible && y.mapToItem(chartGroup, 0, 0).y + y.height <= chartGroup.height, 2000, "settings.chart.yScale clears its expanded group's clip before pointer input");
            choose(y, 2);
            tryVerify(() => SettingsProof.value(location, "Analysis", "yScale") === "log", 2000, "settings.chart.yScale index 2 reads log at QSettings Analysis/yScale in " + SettingsProof.localPath(location) + "; initial read " + JSON.stringify(SettingsProof.settingFacts(location, "Analysis", "yScale")));
            tryVerify(() => SettingsProof.value(location, "Analysis", "scanPatternUpdates") === 0, 2000, "Preferences.scanPatternUpdates=0 reads zero at QSettings Analysis/scanPatternUpdates in " + SettingsProof.localPath(location) + "; initial read " + JSON.stringify(SettingsProof.settingFacts(location, "Analysis", "scanPatternUpdates")));
            compare(Session.project.analysis.text.text, original, "Changing page settings leaves the analysis model text unchanged");
            compare(Session.project.modified, modified, "Changing y scale and scan redraw policy never modifies the project");
            const restored = SettingsProof.restart('import QtQuick; import QtCore; import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as Globals; QtObject { property Settings settings: Settings { location: Globals.Vars.settingsFile; category: "Analysis"; property string yScale: "linear" }; property string axis: settings.yScale }');
            verify(!restored.error, "A fresh configured engine reads the saved page group");
            compare(restored.axis, "log", "A fresh engine reads QSettings Analysis/yScale after selecting settings.chart.yScale index 2; actual token " + restored.axis);
        }
        function test_report_library_preference_seeds_only_created_projects() {
            verify(typeof Preferences.newReportLibraries === "string", "The Projects preference exposes the new-report libraries token");
            Preferences.newReportLibraries = "embedded";
            const page = createTemporaryObject(projectFactory, surface, {
                width: 1200,
                height: 800
            });
            verify(page !== null && waitForPolish(page), "The real Project page lays out its creation workflow");
            const create = findChild(page, "project.create");
            verify(create !== null, "Get started exposes project.create; actual " + create);
            mouseClick(create, create.width / 2, create.height / 2);
            const dialog = SettingsProof.creationDialog(page);
            verify(dialog !== null, "project.create opens the real dialog with projectName and projectParentDirectory");
            tryCompare(dialog, "opened", true, 2000, "The real Create project dialog opens before its fields are filled");
            dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
            dialog.projectName = "created_report";
            dialog.projectDescription = "Independent new-project default witness";
            const name = findChild(dialog, "createProject.name");
            verify(name !== null, "Create project exposes createProject.name; actual " + name);
            mouseClick(name, name.width / 2, name.height / 2);
            keyClick(Qt.Key_Return);
            tryVerify(() => Session.project !== null && Session.project.name === "created_report", 2000, "Return in createProject.name reaches the Get started creation handler; actual project " + Session.project + "; lastError " + Session.lastError);
            compare(Session.project.report.embedLibraries, true, "After Return in the actual Create project dialog, ReportViewModel.embedLibraries reads true with Preferences.newReportLibraries=embedded; actual " + Session.project.report.embedLibraries);
            const url = SettingsProof.emptyDirectory();
            verify(Session.saveAs(url), "The created project's seeded report option is saved for an independent reopen");
            verify(/_report\.html_offline\s+true/.test(SettingsProof.text(url, "reports/report.edi")), "After Session.saveAs, reports/report.edi contains _report.html_offline true; actual text " + JSON.stringify(SettingsProof.text(url, "reports/report.edi")));
            Session.closeProject();
            // A newly created blank project has no loadable structure or experiment yet.
            // Add independent inputs without altering its report record or metadata.
            for (const relative of ["structures/phase.edi", "experiments/bank.edi", "analysis/analysis.edi"])
                verify(SettingsProof.write(url, relative, SettingsProof.repoText("tests/fixtures/loop_parameter_ids/line-segment/" + relative)), "The newly created project's reopen witness adds the independent " + relative + " without changing reports/report.edi");
            Preferences.newReportLibraries = "online";
            verify(Session.openProject(url), "The newly created project reopens under a different preference; lastError " + Session.lastError);
            compare(Session.project.report.embedLibraries, true, "A project's explicit embedded option wins over the new-project preference");
            Session.closeProject();
            Preferences.newReportLibraries = "embedded";
            const existing = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            verify(Session.openProject(existing), "An existing project without html_offline opens under the Embedded preference");
            compare(Session.project.report.embedLibraries, false, "Opening a project with no html_offline reads false independently of Preferences");
            verify(Session.save(), "An unchanged existing project can be saved without adding a default");
            verify(!/_report\.html_offline/.test(SettingsProof.text(existing, "reports/report.edi")), "A save never introduces an absent html_offline item");
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
            let recentFacts = SettingsProof.settingFacts(location, "Projects", "recent");
            tryVerify(() => {
                recentFacts = SettingsProof.settingFacts(location, "Projects", "recent");
                return JSON.stringify(Array.from(recentFacts.list).slice(0, 3)) === JSON.stringify(wanted);
            }, 2000, "After Session.openProject returns for C, QSettings Projects/recent contains C B A in " + SettingsProof.localPath(location) + "; initial typed read " + JSON.stringify(recentFacts) + "; wanted " + JSON.stringify(wanted));
            compare(SettingsProof.value(location, "Projects", "last"), urls[2], "After opening C, QSettings Projects/last in " + SettingsProof.localPath(location) + " records its absolute path; actual " + JSON.stringify(SettingsProof.settingFacts(location, "Projects", "last")));
            const restored = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property var paths: RecentProjects.paths() }');
            verify(!restored.error, "A fresh production RecentProjects singleton reloads the history store");
            compare(JSON.stringify(restored.paths.slice(0, 3)), JSON.stringify(wanted), "A fresh engine reads RecentProjects.paths() from Projects/recent; actual " + JSON.stringify(restored.paths) + "; wanted " + JSON.stringify(wanted));
        }
        function test_desktop_preferences_exposes_the_store_path_and_reset_actions() {
            const dialog = createTemporaryObject(dialogFactory, surface);
            verify(dialog !== null, "The Preferences store controls belong to the actual dialog");
            Preferences.dialogShown = true;
            tryCompare(dialog, "opened", true, 2000, "Desktop Preferences opens before its store controls are inspected");
            const develop = findChild(dialog, "preferences.tab.develop");
            verify(develop !== null, "The store controls are reached through preferences.tab.develop; actual " + develop);
            mouseClick(develop, develop.width / 2, develop.height / 2);
            const path = findChild(dialog, "preferences.settingsPath");
            verify(path !== null, "Develop exposes the named preferences.settingsPath label; actual " + path);
            compare(path.text, SettingsProof.localPath(location), "preferences.settingsPath.text shows the decoded local app-store path; actual " + JSON.stringify(path.text) + "; wanted " + SettingsProof.localPath(location));
            const folder = findChild(dialog, "preferences.openSettingsFolder");
            const reset = findChild(dialog, "preferences.resetSettings");
            verify(folder !== null && reset !== null, "Develop exposes preferences.openSettingsFolder and preferences.resetSettings; actual " + JSON.stringify({
                folder: folder !== null,
                reset: reset !== null
            }));
            compare(folder.text, "Open folder", "preferences.openSettingsFolder names its store action; actual " + folder.text);
            compare(reset.text, "Reset to defaults", "preferences.resetSettings names its store action; actual " + reset.text);
        }
    }
}
