// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import "ApprovedPalette.js" as Approved
import QtQuick.Window
import QtQuick.Controls
import QtTest
import "ExampleProjects.js" as Examples
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1400
    height: 1000
    Component {
        id: projectFactory
        DescriptionTab {
            project: Session.project
        }
    }
    Component {
        id: experimentFactory
        ExperimentPage {
            current: true
        }
    }
    Component {
        id: analysisFactory
        AnalysisPage {
            current: true
        }
    }
    TestCase {
        name: "ExperimentColourIdentity"
        when: windowShown
        property int oldTheme
        property var reference: Approved.reference(SettingsProof)
        property var oldScheme
        function initTestCase() {
            oldTheme = Style.Colors.theme;
            try {
                oldScheme = Approved.getScheme(Preferences);
            } catch (error) {
                oldScheme = null;
            }
            surface.Window.window.width = surface.width;
            surface.Window.window.height = surface.height;
        }
        function cleanup() {
            Session.closeProject();
            Style.Colors.theme = oldTheme;
            if (oldScheme)
                Approved.setScheme(Preferences, oldScheme);
            else
                Preferences.resetToDefaults();
        }
        function icon(root) {
            return Render.descendants(root).find(item => item.isIcon === true && item.modelData.icon === ParameterNames.blockIcon("experiment"));
        }
        function ink(value) {
            return String(value).toLowerCase();
        }
        function test_one_experiment_colour_across_pages_data() {
            const subjects = [
                {
                    kind: "single",
                    example: "pd-neut-cwl_lbco-hrpt",
                    count: 1
                },
                {
                    kind: "joint",
                    example: "pd-neut-tof_ncaf-wish-3bank_start-5",
                    fixture: true,
                    count: 3
                },
                {
                    kind: "scan",
                    example: "pd-neut-cwl_cosio-d20_scan-162f",
                    fixture: true,
                    count: 162
                }
            ];
            const rows = [];
            for (const subject of subjects)
                for (const scheme of reference.schemes)
                    for (const dark of [false, true])
                        rows.push(Object.assign({}, subject, {
                            tag: subject.kind + ("-" + scheme.id) + (dark ? "-dark" : "-light"),
                            scheme: scheme.id,
                            dark: dark
                        }));
            return rows;
        }
        function test_one_experiment_colour_across_pages(data) {
            verify(Examples.open(this, Session, data.example, data.fixture === true), "The colour witness opens the real single, joint or 162-file scan example: " + data.example);
            tryCompare(Session.project, "calculating", false, 15000, "The opened colour witness settles its initial calculation");
            compare(Session.project.experiments.count, data.count, "Each colour witness reaches its independently declared experiment or dataset count");
            Approved.setScheme(Preferences, data.scheme);
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            const project = createTemporaryObject(projectFactory, surface, {
                width: surface.width,
                height: surface.height
            });
            verify(project !== null && waitForPolish(project), "The actual Project description renders its experiment list");
            const list = findChild(project, "project.experiments");
            verify(list !== null, "The colour reference reaches the rendered Project experiment list");
            const positions = data.count > 11 ? [0, 4, data.count - 5, data.count - 1] : Array.from({
                length: data.count
            }, (_, i) => i);
            const expected = {};
            for (const position of positions) {
                const row = Render.descendants(list).find(item => item.modelData === position && Array.isArray(item.segments));
                verify(row !== undefined && icon(row) !== undefined, "The Project list materializes the requested experiment place " + position);
                expected[position] = ink(icon(row).color);
            }
            const approved = Approved.colours(SettingsProof, data.scheme, "measured", data.count, data.dark, {
                scan: data.kind === "scan",
                experiments: data.kind === "scan" ? 1 : data.count,
                structures: Session.project.structures.count
            });
            for (const position of positions)
                compare(expected[position], approved[position], "The Project icon equals its independently frozen approved place for the full experiment count");
            project.visible = false;
            const failures = [];
            for (const consumer of ["Experiment", "Analysis", "Evolution"]) {
                if (consumer === "Evolution" && data.kind !== "scan")
                    continue;
                const page = createTemporaryObject(consumer === "Experiment" ? experimentFactory : analysisFactory, surface, {
                    width: surface.width,
                    height: surface.height
                });
                verify(page !== null && waitForPolish(page), "The real " + consumer + " page lays out its selector and chart");
                if (consumer === "Evolution")
                    page.showMainTab(2);
                const selector = findChild(page, "mainArea.blocks");
                verify(selector !== null, "The colour witness reaches the real " + consumer + " experiment selector");
                compare(selector.count, data.count, "Each selector uses the same complete experiment inventory as Project");
                const roles = {};
                for (const position of positions) {
                    Session.project.currentExperimentIndex = position;
                    tryCompare(Session.project, "calculating", false, 15000, "The selected dataset calculation settles before its measured colour is read");
                    tryCompare(selector, "currentIndex", position, 2000, "The actual page selector follows the selected experiment identity");
                    verify(waitForPolish(page), "The selected experiment finishes page layout before colour inspection");
                    const selected = icon(selector);
                    verify(selected !== undefined, "The selected experiment has an actual rendered selector icon");
                    if (ink(selected.color) !== expected[position])
                        failures.push(consumer + " selected[" + position + "]=" + ink(selected.color) + " expected=" + expected[position]);
                    selector.popup.open();
                    const popupList = selector.popup.contentItem;
                    popupList.positionViewAtIndex(position, ListView.Contain);
                    popupList.forceLayout();
                    tryVerify(() => popupList.itemAtIndex(position) !== null, 2000, "The popup materializes the same dataset place as the Project list");
                    const popupIcon = icon(popupList.itemAtIndex(position));
                    verify(popupIcon !== undefined, "The actual popup delegate draws its experiment icon");
                    if (ink(popupIcon.color) !== expected[position])
                        failures.push(consumer + " popup[" + position + "]=" + ink(popupIcon.color) + " expected=" + expected[position]);
                    selector.popup.close();
                    if (consumer !== "Evolution") {
                        const series = findChild(page, "chart.series.meas");
                        const points = findChild(page, "chart.measured");
                        verify(series !== null && points !== null, "The colour gate reaches both actual measured line and point consumers");
                        if (ink(series.color) !== expected[position] || ink(points.color) !== expected[position])
                            failures.push(consumer + " measured[" + position + "] line=" + ink(series.color) + " points=" + ink(points.color) + " expected=" + expected[position]);
                        for (const role of ["calc", "bkg", "resid", "bragg.0"]) {
                            const drawn = findChild(page, "chart.series." + role);
                            verify(drawn !== null, "The calculated, background, residual and Bragg colour consumers remain present");
                            if (roles[role] === undefined)
                                roles[role] = ink(drawn.color);
                            compare(ink(drawn.color), roles[role], "Changing the experiment's palette place never changes its " + role + " role colour");
                        }
                    }
                }
                page.visible = false;
                page.destroy();
            }
            compare(failures.length, 0, "One experiment keeps its Project palette place/count in every selector and measured series; actual mismatches: " + failures.join("; "));
        }
    }
}
