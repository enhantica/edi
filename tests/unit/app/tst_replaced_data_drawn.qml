// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EdiFitReference 1.0
import ChartBackendAcceptance 1.0
import TooltipAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "ReplacedData"
    when: windowShown
    property var app
    Component {
        id: application
        Main {}
    }
    function init() {
        RunLog.dismissCrash();
        AppState.reset();
        app = application.createObject(null, {
            width: 1280,
            height: 900,
            visible: true
        });
        verify(app && waitForRendering(app.contentItem), "Replacement uses a real rendered application window");
        app.requestActivate();
    }
    function cleanup() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
    }
    function press(item) {
        app.update();
        verify(waitForRendering(app.contentItem), "Actual replacement input follows a rendered frame");
        const point = Ui.clickPoint(item);
        verify(point && item.enabled, "The real replacement action is exposed and enabled");
        mouseClick(item, point.x, point.y);
    }
    function open(kind) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.referenceUrl(kind))), "The regression opens its independently authored " + kind + " input");
        tryCompare(Session.project, "calculating", false, 15000, "Initial diffraction calculation settles before replacement");
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        tryVerify(() => app.pagesBuilt === app.pagesWanted, 10000, "The actual experiment workflow finishes building before input");
    }
    function chartPage(page) {
        Ui.click(test, Probe, app, "appBar.tab." + page);
        const owner = Render.descendants(Ui.page(app)).find(item => item.pageName === page && item.current);
        verify(owner !== undefined, "The active loader exposes the real workflow page before chart selection");
        let tab;
        tryVerify(() => {
            tab = owner.pageViewItem ? Array.from(owner.pageViewItem.tabs).find(item => item.objectName === "mainArea.tab.pattern") : null;
            return tab && tab.enabled && Ui.rendered(tab);
        }, 5000, "The real " + page + " page offers its rendered Pattern tab before input");
        if (!tab.checked)
            press(tab);
        tryCompare(tab, "checked", true, 2000, "Pointer input selects the Pattern view");
        tryVerify(() => !Ui.moving(app.contentItem), 2000, "The chart viewport finishes moving before hover");
        app.update();
        verify(waitForRendering(app.contentItem), "The selected chart publishes a rendered frame");
        let chart;
        tryVerify(() => {
            chart = Render.descendants(owner.pageViewItem).find(item => item.objectName === "chart" && item.shown && Ui.rendered(item));
            return !!chart;
        }, 3000, "The active workflow owns its live shared chart");
        return chart;
    }
    function replacement(kind, hoverTarget = null) {
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        let group;
        tryVerify(() => {
            group = Ui.find(Ui.page(app), "experiments.group", true);
            return group !== null;
        }, 2000, "The selected Basic tab exposes its actual Experiments group");
        Ui.scrollIntoView(group.titleArea);
        if (group.collapsed)
            press(group.titleArea);
        tryVerify(() => !group.collapsed && !group.folding, 2000, "The actual Experiments table finishes expanding before its row menu is used");
        Ui.click(test, Probe, app, "experiments.dataMore.0");
        let action;
        tryVerify(() => {
            action = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "experiments.load.dataFile" && Ui.exposed(item));
            return !!action;
        }, 2000, "The actual row ellipsis opens its replacement File action");
        press(action);
        let dialogs;
        tryVerify(() => {
            dialogs = Array.from(SettingsProof.projectFileDialogs(app, false));
            return dialogs.length === 1;
        }, 2000, "The row File action opens exactly one real system chooser");
        const file = Probe.referenceUrl(kind === "powder" ? "replacement.xye" : "replacement.dat");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], file, false), "The real chooser delivers the independently authored replacement file");
        if (hoverTarget)
            verify(TooltipClock.movePointer(hoverTarget, hoverTarget.width * 0.6, hoverTarget.height * 0.6), "A real hover reaches the previous drawing immediately after the chooser accepts replacement, before settling");
        tryVerify(() => {
            const current = Session.project.currentExperiment;
            const measured = kind === "powder" ? current.measCalcPoints().meas : Probe.rows(current.singleCrystalReflections).map(row => row.intensityMeas);
            return measured && measured.length === (kind === "powder" ? 6 : 3) && measured[0] === 23;
        }, 10000, "The row replacement really publishes the independently authored new observations");
        tryVerify(() => !Session.project.calculating, 15000, "Replacing measured data finishes the actual recalculation");
    }
    function fit() {
        const f = Session.project.fit;
        verify(f.available, "The authored powder input permits an actual fit before replacing its observations");
        f.start();
        tryVerify(() => !f.running && f.outcome !== "", 15000, "An actual completed fit establishes old quality and status values");
        verify(f.goodnessOfFit !== "", "The regression starts with a real prior chi-square");
        for (const dialog of Probe.objectsWithProperty(app, "opened").filter(item => item.opened && typeof item.standardButton === "function")) {
            const ok = dialog.standardButton(Dialog.Ok);
            if (ok)
                press(ok);
        }
    }
    function test_a_hover_all_chart_panes_data() {
        return [
            {
                tag: "powder"
            },
            {
                tag: "single"
            }
        ];
    }
    function test_a_hover_all_chart_panes(data) {
        open(data.tag);
        const oldChart = chartPage("experiment");
        verify(ChartBackendProof.gpu(oldChart), "Hover regression uses the real Qt Graphs RHI renderer, not the Qt Quick software fallback");
        const image = ChartBackendProof.snapshot(oldChart);
        verify(image.valid && image.ink > 0, "Populated chart series really draw before the old experiment is replaced");
        verify(TooltipClock.movePointer(oldChart, oldChart.width / 2, oldChart.height / 2), "A genuine window mouse move enters the old drawing before replacement");
        replacement(data.tag, oldChart);
        const visited = [];
        for (const page of ["experiment", "analysis", "structure"]) {
            const chart = chartPage(page);
            const panes = Render.descendants(chart).filter(item => item.seriesList !== undefined && Ui.rendered(item));
            const names = panes.map(item => item.objectName);
            verify(names.includes("chart.view.main") && names.includes("chart.view.residual"), "The hover reaches both data and residual plots after replacement");
            if (data.tag === "powder")
                verify(names.includes("chart.view.bragg"), "The powder replacement also reaches its Bragg point renderer");
            for (const pane of panes) {
                for (const y of [0.1, 0.5, 0.9])
                    for (const x of [0.1, 0.3, 0.5, 0.7, 0.9])
                        verify(TooltipClock.movePointer(pane, pane.width * x, pane.height * y), "Every live chart pane receives actual native hover moves after data replacement");
                visited.push(page + ":" + pane.objectName);
            }
            app.update();
            verify(waitForRendering(app.contentItem), "The native scene remains alive and renders after every hover sweep");
            if (page !== "structure") {
                const owner = Render.descendants(Ui.page(app)).find(item => item.pageName === page && item.current);
                const comparison = Array.from(owner.pageViewItem.tabs).find(item => item.objectName === "mainArea.tab.measCalc");
                verify(comparison && comparison.enabled, "Measured replacement data enables its real measured-versus-calculated chart on each eligible host");
                press(comparison);
                tryCompare(comparison, "checked", true, 2000, "Actual pointer input selects the comparison chart after replacement");
                tryVerify(() => !Ui.moving(app.contentItem), 2000, "The measured-versus-calculated viewport settles before hover");
                const currentView = owner.pageViewItem.items[owner.pageViewItem.tabIndex];
                verify(currentView && currentView.shown, "The comparison hover is scoped to the tab's actual current item");
                const plots = Render.descendants(currentView).filter(item => item.seriesList !== undefined && Ui.rendered(item));
                compare(plots.length, 1, "The real comparison tab exposes exactly its current Qt Graphs plot");
                for (const pane of plots) {
                    for (const y of [0.1, 0.5, 0.9])
                        for (const x of [0.1, 0.3, 0.5, 0.7, 0.9])
                            verify(TooltipClock.movePointer(pane, pane.width * x, pane.height * y), "The measured-versus-calculated point renderer receives genuine native hover moves after replacement");
                    visited.push(page + ":comparison");
                }
                app.update();
                verify(waitForRendering(app.contentItem), "The comparison scene remains alive after replacement and hover");
            }
        }
        verify(visited.length >= 8, "The hover gate cannot pass without reaching the real plots on every workflow host");
        console.info("REPLACED_DATA_HOVER " + JSON.stringify(visited));
    }
    function test_b_replacement_recalculates_on_the_new_grid() {
        open("powder");
        replacement("powder");
        const e = Session.project.currentExperiment;
        compare(e.pattern.count, 6, "The replacement publishes all six authored observations");
        compare(e.pattern.xMin, 31, "The calculation takes the new observation grid's first abscissa");
        compare(e.pattern.xMax, 71, "The calculation takes the new observation grid's last abscissa");
        compare(Array.from(e.measCalcPoints().meas), [23, 29, 19, 31, 17, 37], "The live measured series equals the independently supplied replacement rows");
        verify(!e.pattern.stale && e.pattern.calculationError === "", "The replaced pattern is current and reports no calculation failure");
        verify(FitOracle.freshCalculated(Session.project), "The displayed calculation after replacement equals a fresh calculation of the new data state");
    }
    function test_c_replacement_retires_old_quality_and_status() {
        open("powder");
        fit();
        const old = Session.project.currentExperiment;
        verify(old.fitOutcome !== "", "The old experiment really carries a completed fit outcome before replacement");
        replacement("powder");
        const current = Session.project.currentExperiment;
        compare(current.fitOutcome, "", "A completed fit to old observations supplies no outcome for replacement data");
        for (const page of ["experiment", "analysis", "structure"]) {
            const chart = chartPage(page);
            compare(chart.reliability, "", "The new data cannot display old Rwp or chi-square as its own reliability");
        }
        const status = findChild(app, "statusBar.fit");
        verify(status !== null, "The stale-quality check reaches the actual status bar");
        const chi = Render.descendants(status).filter(item => item.keyText === "χ²" && typeof item.valueText === "string" && Ui.exposed(item));
        verify(chi.every(item => item.valueText === ""), "The actual status bar clears chi-square belonging to the replaced observations");
        const outcome = findChild(app, "statusBar.fit.outcome");
        verify(!Ui.exposed(outcome) || outcome.valueText === "" || outcome.valueText === "Outdated", "The old fit status is removed or explicitly marked outdated after replacement");
    }
}
