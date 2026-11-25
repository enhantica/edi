// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternAreaLayoutAcceptance 1.0
import "RenderedTable.js" as Render
import "../../fixtures/pattern_area_layouts/input.js" as Input

Item {
    id: surface
    width: 1200
    height: 900

    Component {
        id: powder
        PatternChart {
            width: 1100
            height: 760
            experiment: Session.project ? Session.project.currentExperiment : null
            axisProject: Session.project
            settingsPage: "pattern"
        }
    }
    Component {
        id: singleCrystal
        SingleCrystalChart {
            width: 1100
            height: 760
            experiment: Session.project ? Session.project.currentExperiment : null
            project: Session.project
        }
    }

    TestCase {
        id: test
        name: "PatternAreaLayouts"
        when: windowShown
        property var figure
        property var chart
        property var project
        property var root
        property var main
        property var residual
        property var failures

        function init() {
            Preferences.resetToDefaults();
            Preferences.patternYScale = "linear";
            Preferences.patternMeasuredStyle = "band";
            Preferences.structureCurves = true;
            failures = [];
        }
        function cleanup() {
            AreaLayouts.stop();
            if (project)
                project.adjusting = false;
            if (figure)
                figure.destroy();
            figure = chart = project = main = residual = null;
            Session.closeProject();
            Preferences.resetToDefaults();
        }
        function open(path, mixed) {
            root = SettingsProof.copyProject(Probe.repoUrl(path));
            if (mixed)
                verify(Input.mixed(SettingsProof, root), "Distinct measured CW and TOF blocks reach the project loader");
            verify(Session.openProject(root), "The project loader accepts the chart fixture: " + Session.lastError);
            project = Session.project;
            calculated();
        }
        function calculated() {
            tryCompare(project, "calculating", false, 10000, "The calculation settles before checking the selected chart population");
        }
        function frames() {
            surface.Window.window.update();
            verify(waitForPolish(chart, 3000), "The chart completes polish after the operation");
            verify(waitForRendering(chart, 3000), "The chart submits a frame after the operation");
        }
        function show(factory) {
            figure = factory.createObject(surface);
            verify(figure !== null, "The production chart can be instantiated");
            chart = factory === powder ? figure : findChild(figure, "chart");
            verify(chart !== null, "The production figure exposes its Pattern chart");
            main = findChild(chart, "chart.view.main");
            residual = findChild(chart, "chart.view.residual");
            verify(main !== null && residual !== null, "The observer can read the actual main and residual panes");
            AreaLayouts.attach(main, residual);
            frames();
        }
        function phase(label, operation, settled, required = []) {
            AreaLayouts.begin();
            operation();
            tryVerify(settled, 10000, label + " reaches its intended UI state");
            frames();
            const observed = AreaLayouts.result();
            verify(observed.frames > 0, label + " reaches the render synchronization boundary");
            for (const name of required)
                verify(observed.nonempty[name] === true, label + " observes the nonempty " + name + " area");
            console.info("area-layout", label, observed.frames, observed.layouts, observed.drawnShapes, observed.worst, observed.detail);
            // A modest zoom may draw beyond the edges. This limit allows several entire off-plot spans.
            if (observed.worst > 8)
                failures.push(label + ": " + observed.detail);
        }
        function finish() {
            verify(failures.length === 0, "Area points must stay within eight spans of the plot on the axes in use\n" + failures.join("\n"));
        }
        function zoom() {
            const plot = main.plotArea;
            mouseWheel(main, plot.x + plot.width / 2, plot.y + plot.height / 2, 0, 120);
        }
        function span() {
            return main.axisX.max - main.axisX.min;
        }
        function toggleResidual() {
            const row = Render.descendants(chart).find(item => item.objectName === "chart.legend.entry" && item.key === "resid" && item.visible);
            verify(row !== undefined, "The chart legend offers the actual visible residual row");
            mouseClick(row, row.width / 2, row.height / 2);
        }
        function measured() {
            open("tests/fixtures/excluded_display/cw", true);
            project.currentExperimentIndex = 0;
            show(powder);
            phase("measured chart", () => {}, () => residual.visible, ["chart.series.meas.band", "chart.series.resid.band", "chart.series.structure.0"]);
            verify(AreaLayouts.result().drawnShapes > 0, "The observer reaches actual filled shapes in the measured chart");
        }

        function test_switch_beam_mode() {
            open("tests/fixtures/excluded_display/cw", false);
            verify(project.createExperiment(), "The project creates a simulation whose beam mode can be changed");
            calculated();
            show(powder);
            const index = project.currentExperimentIndex;
            for (const token of ["time-of-flight", "constant wavelength"]) {
                phase(token, () => {
                    verify(project.setExperimentType(index, "beamMode", token), "The real experiment model accepts the beam type selection");
                }, () => chart.experiment && chart.experiment.beamModeToken === token && !project.calculating,
                ["chart.series.structure.0"]);
            }
            finish();
        }

        function test_change_blocks_and_link_structure() {
            measured();
            for (const [index, token] of [[1, "time-of-flight"], [0, "constant wavelength"], [2, "constant wavelength"]]) {
                const before = chart.experiment;
                phase("select block " + index, () => project.currentExperimentIndex = index,
                    () => chart.experiment !== before && chart.experiment === project.currentExperiment && chart.experiment.beamModeToken === token && !project.calculating,
                    ["chart.series.meas.band", "chart.series.structure.0"]);
            }
            const contents = SettingsProof.text(root, "structures/phase.edi").replace(/^data_phase/m, "data_second_phase");
            verify(SettingsProof.write(root, "second_phase.edi", contents), "The fixture supplies a second distinct structure record");
            verify(project.loadStructure(Qt.resolvedUrl(String(root) + "/second_phase.edi")), "The second structure loads into the real project");
            calculated();
            const links = project.currentExperiment.linkedStructures;
            const before = links.count;
            phase("link structure", () => links.append(), () => links.count > before && !project.calculating,
                ["chart.series.structure.0", "chart.series.structure.1"]);
            finish();
        }

        function test_zoom_reset_and_residual_layout() {
            measured();
            const start = span();
            phase("wheel zoom", zoom, () => span() < 0.9 * start, ["chart.series.meas.band"]);
            phase("zoom reset", () => mouseClick(findChild(chart, "chart.toolbar.reset")),
                () => span() > 0.99 * start, ["chart.series.meas.band"]);
            const oldHeight = residual.plotArea.height;
            phase("resize residual on linear scale", () => chart.height = 480,
                () => residual.plotArea.height > 0 && residual.plotArea.height < oldHeight - 1,
                ["chart.series.resid.band"]);
            Preferences.patternLegendShown = true;
            frames();
            phase("hide residual", toggleResidual, () => !residual.visible);
            phase("show residual", toggleResidual, () => residual.visible,
                ["chart.series.resid.band"]);
            finish();
        }

        function test_first_adjustment_and_changes_while_held() {
            measured();
            const scale = Probe.rows(project.currentExperiment.linkedStructures)[0].scale;
            const oldMaximum = main.axisY.max;
            const initialScale = scale.value;
            // The slider uses this project state for press and release and edits the parameter's value on a move.
            phase("first held parameter step", () => {
                project.adjusting = true;
                scale.value = initialScale * 25;
            }, () => project.adjusting && !project.calculating && main.axisY.max > oldMaximum);
            const wide = span();
            phase("zoom while held", zoom, () => project.adjusting && span() < 0.9 * wide);
            phase("switch measured style while held", () => Preferences.patternMeasuredStyle = "line",
                () => project.adjusting && findChild(chart, "chart.toolbar.measuredStyle").currentIndex === 1);
            phase("switch block while held", () => project.currentExperimentIndex = 1,
                () => project.adjusting && chart.experiment.beamModeToken === "time-of-flight" && !project.calculating);
            phase("release parameter", () => {
                project.adjusting = false;
                Preferences.patternMeasuredStyle = "band";
            }, () => !project.adjusting, ["chart.series.meas.band", "chart.series.structure.0"]);
            finish();
        }

        function test_calculated_bars() {
            open("docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project", false);
            Preferences.singleCrystalMeasuredStyle = "bars";
            show(singleCrystal);
            const fill = findChild(chart, "chart.series.calc.bars.fill");
            verify(fill !== null && fill.count > 0, "The selected single-crystal case draws actual calculated bars");
            const before = span();
            phase("zoom calculated bars", zoom, () => span() < 0.9 * before);
            verify(AreaLayouts.result().areas["chart.series.calc.bars"] === true,
                "The observer reaches the calculated-bars area slot even when it is empty");
            finish();
        }
    }
}
