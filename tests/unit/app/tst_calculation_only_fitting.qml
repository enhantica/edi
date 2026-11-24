import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as View

TestCase {
    id: test
    name: "CalculationOnlyFitting"
    when: windowShown
    property var appWindow
    property var extraField
    property var source
    Component {
        id: application
        Main {}
    }
    Component {
        id: parameterField
        ParameterField {
            x: 25
            y: 80
            z: 10000
            width: 200
            height: 45
        }
    }
    SignalSpy {
        id: running
        target: Session.project ? Session.project.fit : null
        signalName: "runningChanged"
    }
    SignalSpy {
        id: recalculated
        target: Session.project
        signalName: "recalculated"
    }

    function init() {
        Session.closeProject();
        Preferences.analysisYScale = "linear";
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Calculation-only acceptance hosts the production application window");
        appWindow.width = 1300;
        // Keep the bottom fitting controls inside the headless screen for real pointer input.
        appWindow.height = 720;
        verify(waitForRendering(appWindow.contentItem), "The calculation-only window renders before input");
    }
    function cleanup() {
        if (extraField)
            extraField.destroy();
        extraField = null;
        Probe.clearWatches();
        Session.closeProject();
        appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function ready() {
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale, 10000, "Every actual calculation publishes current pattern rows before inspection");
        compare(Session.project.currentExperiment.pattern.calculationError, "", "The authored calculation must finish without an engine error");
    }
    function open(measured) {
        source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/excluded_display/cw"));
        let text = SettingsProof.text(source, "experiments/pattern.edi");
        verify(text.includes("phase 1\n"), "The independent cubic fixture supplies a known unit structure scale");
        text = text.replace("phase 1\n", "phase 1()\n");
        if (!measured) {
            verify(text.includes("loop_\n_data.two_theta\n"), "The authored measured loop is explicitly removed for the calculation-only control");
            text = text.split("loop_\n_data.two_theta\n")[0] + "_data_range.two_theta_min 10\n_data_range.two_theta_max 90\n_data_range.two_theta_step 0.5\n";
        }
        verify(SettingsProof.write(source, "experiments/pattern.edi", text), "The disposable project preserves the independent structure and instrument while declaring its measured-data state");
        verify(SettingsProof.write(source, "observed.xye", "10 100 2\n20 110 2\n30 120 2\n40 130 2\n50 140 2\n60 150 2\n70 160 2\n80 170 2\n90 180 2\n"), "The load-data control has independently authored positive observations and uncertainties");
        verify(Session.openProject(source), "The authored calculation-only or measured project loads through Session: " + Session.lastError);
        ready();
        compare(Session.project.currentExperiment.calculationOnly, !measured, "Measured-data presence follows the authored file rather than the project label or axis size");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis enters the real viewport before its fitting controls are used");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
        verify(waitForPolish(appWindow.contentItem), "The real Analysis table finishes layout");
    }
    function control(name) {
        const item = name.startsWith("statusBar.") ? Ui.control(Probe, appWindow, name) : Ui.find(Ui.page(appWindow), name, true);
        verify(item !== null, "The actual Analysis page exposes " + name);
        return item;
    }
    function scale() {
        const item = Session.project.currentExperiment.scale;
        verify(item !== null && item.refinable, "The witness reaches the real editable structure-scale parameter");
        return item;
    }
    function scaleRow() {
        const table = control("parameters.list");
        table.sourceModel.nameFilter = "scale";
        tryCompare(table, "count", 1, 2000, "The real name filter isolates the single authored structure scale");
        table.positionViewAtIndex(0, ListView.Contain);
        table.forceLayout();
        tryVerify(() => Ui.find(table, "parameters.value.0", true) !== null, 2000, "The scale's actual row delegate is materialized before input");
        return table;
    }
    function input(item, button) {
        Ui.scrollIntoView(item);
        verify(waitForPolish(appWindow.contentItem), "Attempted fitting and free-control pointer targets finish their actual layout");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "Attempted fitting and free-control pointer targets reach a settled frame");
        const point = Ui.clickPoint(item);
        verify(point !== null, "The attempted fitting route has a real pointer target");
        mouseClick(item, point.x, point.y, button === undefined ? Qt.LeftButton : button);
    }
    function flags() {
        return Probe.rows(Session.project.parameters).map(row => [String(row.path), row.parameter.free]);
    }
    function noFreeChange(action, reason) {
        const before = JSON.stringify(flags());
        const modified = Session.project.modified;
        const watch = Probe.watch(scale());
        action();
        verify(waitForPolish(appWindow.contentItem), "Attempted free edits settle through the production event loop");
        compare(JSON.stringify(flags()), before, "Without measured data every free flag stays unchanged: " + reason);
        compare((Probe.events(watch).freeChanged || []).length, 0, "Blocked free edits publish no parameter-free change");
        compare(Session.project.modified, modified, "Blocked free edits do not dirty the project");
    }
    function test_start_data() {
        return ["disabled", "tooltip", "hover-tooltip", "pointer", "keyboard", "invokable"].map(route => ({
                    tag: route,
                    route: route
                }));
    }
    function test_start(data) {
        open(false);
        const fit = Session.project.fit, button = control("statusBar.fit.button");
        if (data.route === "disabled") {
            verify(!button.clickable && !fit.available, "A project without measured data disables both Start fitting and its application command");
        } else if (data.route === "tooltip") {
            compare(button.ToolTip.text, "Fit the free parameters", "The disabled status Fit retains the exact owner tooltip");
            verify(/measur/i.test(fit.unavailableReason) && /data/i.test(fit.unavailableReason), "The unavailable model still explains the measured-data requirement");
        } else if (data.route === "hover-tooltip") {
            Ui.scrollIntoView(button);
            verify(waitForPolish(appWindow.contentItem), "The disabled fitting hover target completes its actual layout");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The disabled fitting hover target reaches a settled frame");
            const point = Ui.clickPoint(button);
            verify(point !== null, "The disabled fitting button remains reachable for its explanatory hover");
            mouseMove(button, point.x, point.y);
            tryVerify(() => Probe.objectsWithProperty(button, "enterAnimationDuration").some(tip => tip.visible && tip.opened && tip.opacity >= 0.99 && View.textItems(tip.contentItem).some(item => item.text === "Fit the free parameters")), 3000, "Hovering disabled Start fitting displays the owner tooltip when preferences enable it");
        } else {
            running.clear();
            const status = fit.status;
            if (data.route === "invokable")
                fit.start();
            else {
                if (data.route === "keyboard") {
                    Ui.scrollIntoView(button);
                    appWindow.requestActivate();
                    button.forceActiveFocus();
                    tryVerify(() => !button.clickable || button.activeFocus, 1000, "An enabled fitting button receives focus before the independent keyboard attempt");
                    verify(SettingsProof.key(button, Qt.Key_Space), "The fitting keyboard attempt sends Space to the actual application window");
                } else
                    input(button);
            }
            verify(waitForRendering(appWindow.contentItem), "Attempted fitting input is delivered before its effect is checked");
            compare(running.count, 0, "No pointer, keyboard or direct application route starts a fit without measured data");
            compare(fit.status, status, "A blocked fit does not become a failed attempted fit");
        }
    }
    function test_free_controls_data() {
        return ["checkbox", "checkbox-keyboard", "header", "header-pointer", "value-menu", "field-menu", "value-signal", "field-signal"].map(route => ({
                    tag: route,
                    route: route
                }));
    }
    function test_free_controls(data) {
        open(false);
        scaleRow();
        if (data.route === "checkbox") {
            const box = control("parameters.free.0");
            verify(!box.enabled, "The visible free checkbox is disabled in a calculation-only project");
            noFreeChange(() => input(box), "A disabled free checkbox cannot change the saved free flag");
        } else if (data.route === "checkbox-keyboard") {
            const box = control("parameters.free.0");
            noFreeChange(() => {
                Ui.scrollIntoView(box);
                appWindow.requestActivate();
                box.forceActiveFocus();
                tryVerify(() => !box.enabled || box.activeFocus, 1000, "An enabled free checkbox receives focus before its keyboard attempt");
                verify(SettingsProof.key(box, Qt.Key_Space), "The free-checkbox keyboard attempt reaches the actual application window");
            }, "Keyboard input cannot toggle a free checkbox without measured data");
        } else if (data.route === "header" || data.route === "header-pointer") {
            const header = control("parameters.freeHeader");
            if (data.route === "header") {
                compare(header.interactionEnabled, false, "The exported header interaction state follows the disabled bulk pointer actor without measured data");
            } else {
                noFreeChange(() => input(header), "Clicking the disabled free header cannot change parameter flags");
                verify(!Probe.visiblePopups(appWindow).some(popup => findChild(popup, "parameters.freeHeader.free") !== null), "The disabled free header cannot open its bulk-free menu");
            }
        } else {
            let field = control("parameters.value.0");
            if (data.route.startsWith("field-")) {
                extraField = parameterField.createObject(appWindow.contentItem, {
                    item: scale()
                });
                verify(extraField !== null && extraField.enabled, "The production parameter field stays editable without measured data");
                field = extraField;
            }
            if (data.route.endsWith("signal")) {
                noFreeChange(() => field.fitToggled(!scale().free), "The parameter menu's free signal cannot bypass the no-measured-data rule");
            } else {
                const popup = Ui.parameterPopup(test, field);
                const toggle = Ui.parameterPopupItem(test, field, popup, "free");
                verify(toggle !== null && (!toggle.visible || !toggle.enabled), "Value-cell and parameter-field menus cannot offer an active free toggle without measured data");
            }
        }
    }
    function test_free_commands_data() {
        const rows = [];
        for (const route of ["parameter", "bulk", "table-role"])
            for (const makeFree of [false, true])
                rows.push({
                    tag: route + "-" + makeFree,
                    route: route,
                    makeFree: makeFree
                });
        return rows;
    }
    function test_free_commands(data) {
        open(false);
        const rows = Probe.rows(Session.project.parameters);
        const uid = data.makeFree ? "cell.length_a" : "linked_structure.scale";
        const index = rows.findIndex(row => String(row.parameter.uid) === uid && row.parameter.free !== data.makeFree);
        verify(index >= 0, "The authored project reaches both fixed-to-free and free-to-fixed attempts");
        const parameter = rows[index].parameter;
        noFreeChange(() => {
            if (data.route === "parameter")
                parameter.free = data.makeFree;
            else if (data.route === "bulk")
                Session.project.setParametersFree([parameter], data.makeFree);
            else
                Probe.writeRole(Session.project.parameters, index, "free", data.makeFree);
        }, "Direct parameter, bulk-header and editable-role routes cannot toggle free without measured data");
    }
    function test_values_still_recalculate() {
        open(false);
        scaleRow();
        const cell = control("parameters.value.0");
        verify(cell.enabled && !cell.readOnly, "Calculation-only parameter values remain editable in the actual table");
        const before = Probe.rows(Session.project.currentExperiment.pattern);
        verify(before.length > 2 && before.some(row => row.intensityCalc > row.intensityBkg), "The physical scale control starts with a nonzero calculated peak contribution");
        const chart = View.find(Ui.page(appWindow), "chart");
        verify(chart !== null, "Analysis retains its real calculated-pattern chart");
        tryVerify(() => PatternProof.series(chart, "chart.series.calc").some(line => line.points.some(point => isFinite(point.y))), 3000, "The original calculated pattern reaches its actual chart series before the value edit");
        const drawnBefore = JSON.stringify(PatternProof.series(chart, "chart.series.calc"));
        recalculated.clear();
        const popup = Ui.parameterPopup(test, cell);
        const editor = Ui.parameterValue(test, cell, popup);
        Ui.focusParameter(test, editor);
        verify(SettingsProof.type(editor, "2"), "The actual scale value editor accepts real keyboard text");
        verify(SettingsProof.key(editor, Qt.Key_Return), "The actual scale editor commits through its ordinary Return handler");
        popup.close();
        compare(scale().value, 2, "The requested nontrivial scale value is retained without enabling fitting");
        tryVerify(() => recalculated.count > 0 && !Session.project.calculating, 10000, "A calculation-only value edit publishes a real later calculation");
        ready();
        const after = Probe.rows(Session.project.currentExperiment.pattern);
        compare(after.length, before.length, "A scale edit preserves the independently declared calculation grid");
        let peaks = 0;
        for (let i = 0; i < before.length; ++i) {
            if (!isFinite(before[i].intensityCalc) || !isFinite(after[i].intensityCalc))
                continue;
            const background = 40 + (before[i].x - 10) / 2;
            fuzzyCompare(after[i].intensityBkg, background, 1e-8, "The authored linear background remains independent of the structure scale");
            const expected = background + 2 * (before[i].intensityCalc - background);
            fuzzyCompare(after[i].intensityCalc, expected, Math.max(1e-8, Math.abs(expected) * 1e-10), "Doubling structure scale doubles net calculated intensity at every included grid point");
            if (before[i].intensityCalc > background + 1e-5)
                peaks++;
        }
        verify(peaks > 0, "The scale invariant reaches real peaks rather than background-only identity points");
        tryVerify(() => JSON.stringify(PatternProof.series(chart, "chart.series.calc")) !== drawnBefore, 3000, "The edited calculation-only pattern replaces real chart coordinates instead of retaining the old drawing");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The changed calculation-only chart reaches an actual frame");
        const capture = PatternProof.capture(appWindow, "calculation-only-value-edit");
        verify(capture.openGL && capture.saved, "The editable calculation-only pattern retains a real OpenGL capture");
    }
    function measuredControls(edit) {
        verify(control("statusBar.fit.button").clickable && Session.project.fit.available, "At least one measured experiment enables Start fitting without a restart");
        scaleRow();
        verify(control("parameters.free.0").enabled && control("parameters.freeHeader").interactionEnabled === true, "Measured data enables both the free column and its bulk header");
        if (!edit)
            return;
        const before = scale().free;
        input(control("parameters.free.0"));
        compare(scale().free, !before, "Measured-data free checkboxes retain their ordinary edit behavior");
        scale().free = before;
        compare(scale().free, before, "Measured-data direct free assignment retains ordinary behavior");
        for (const makeFree of [false, true]) {
            input(control("parameters.freeHeader"));
            const name = "parameters.freeHeader." + (makeFree ? "free" : "fixed");
            tryVerify(() => Probe.visiblePopups(appWindow).some(popup => findChild(popup, name) !== null), 1000, "Measured data preserves the real bulk-free header menu");
            const popup = Probe.visiblePopups(appWindow).find(item => findChild(item, name) !== null);
            const choice = findChild(popup, name);
            verify(choice !== null && choice.enabled, "Measured-data bulk menu choices remain enabled");
            input(choice);
            compare(scale().free, makeFree, "Measured-data header actions still write the selected free or fixed state");
        }
    }
    function test_data_transitions_data() {
        return ["load", "undo-last-data", "remove-last-data"].map(flow => ({
                    tag: flow,
                    flow: flow
                }));
    }
    function test_data_transitions(data) {
        open(false);
        const project = Session.project;
        verify(project.loadDataInto(project.currentExperiment, Qt.resolvedUrl(source + "/observed.xye")), "The real plain-data loader replaces the calculation-only experiment with authored measurements");
        ready();
        compare(Session.project, project, "Loading measured data keeps the same open application project");
        verify(!project.currentExperiment.calculationOnly, "Loading measurements changes actual experiment data presence");
        measuredControls(false);
        if (data.flow === "undo-last-data") {
            project.undo();
            ready();
            verify(project.currentExperiment.calculationOnly, "Undoing the last measured-data load restores the original simulation");
        } else if (data.flow === "remove-last-data") {
            verify(project.createExperiment(), "The removal control keeps a real calculation-only experiment beside the measured one");
            project.removeExperiment(0);
            ready();
            verify(project.currentExperiment.calculationOnly, "Removing the last measured experiment leaves only a calculation-only experiment");
        } else
            return;
        verify(!control("statusBar.fit.button").clickable && !project.fit.available, "Removing the last measured data disables fitting again in the same application project");
        scaleRow();
        verify(!control("parameters.free.0").enabled && control("parameters.freeHeader").interactionEnabled === false, "Removing the last measured data disables free edits again without a restart");
    }
    function test_measured_and_mixed_projects() {
        open(true);
        measuredControls(true);
        verify(Session.project.createExperiment(), "The mixed control adds a real calculation-only experiment beside measured data");
        ready();
        verify(Session.project.currentExperiment.calculationOnly, "The mixed witness selects its calculation-only experiment");
        verify(control("statusBar.fit.button").clickable && Session.project.fit.available, "Measured data anywhere in the project enables fitting even when the selected experiment is calculation-only");
        Session.project.currentExperimentIndex = 0;
        ready();
        running.clear();
        Session.project.fit.start();
        verify(running.count > 0, "The unchanged measured-data application command really starts a fit");
        tryVerify(() => !Session.project.fit.running && Session.project.fit.canUndo, 10000, "The measured-data control completes an actual fit with an undoable result");
    }
    function test_visible_disabled_controls_without_measurements() {
        open(false);
        scaleRow();
        const free = control("parameters.free.0");
        verify(Ui.exposed(free) && !free.enabled, "Without measured data the Free column stays visible and disabled");
        const header = control("parameters.freeHeader");
        verify(Ui.exposed(header) && !header.interactionEnabled, "Without measured data the Free header retains its visible column geometry");
        const variability = control("parameters.variability");
        verify(Ui.exposed(variability) && !variability.enabled, "The parameter variability selector remains visible and disabled without measured data");
        compare(control("statusBar.fit.button").keyIcon, "play", "The idle Fit button uses the plain play icon");
    }
    function rejectedPowderPoint(x) {
        return x<=15 || (x>=38.5 && x<=41.5) || x>=85;
    }
    function removePowderRanges() {
        const regions=Session.project.currentExperiment.excludedRegions;
        const count=Probe.rows(regions).length;
        compare(count,3,"The powder scale witness contains all three authored excluded regions");
        for(let i=0;i<count;++i) regions.remove(0);
        ready();
        return count;
    }
    function restorePowderRanges(count) {
        for(let i=0;i<count;++i) Session.project.undo();
        ready();
    }
    function powderStimulus() {
        open(false);
        const count=removePowderRanges(), rows=Probe.rows(Session.project.currentExperiment.pattern);
        let data="",wn=0,wd=0,un=0,ud=0,rn=0,rd=0,peak=0,peakRatio=0;
        for(let i=0;i<rows.length;++i) {
            const row=rows[i],net=row.intensityCalc-row.intensityBkg;
            if(!isFinite(net)) continue;
            // The engine profile is an input stimulus for a normal-equation invariant.
            // Nonproportional net observations distinguish weighting and peak ratios.
            const sigma=[1,4,2][i%3],ratio=rejectedPowderPoint(row.x)?1e10:1.2+0.35*(i%5);
            const observed=row.intensityBkg+ratio*net+100+17*(i%7);
            data+=row.x+" "+observed+" "+sigma+"\n";
            rn+=net*(observed-row.intensityBkg)/(sigma*sigma); rd+=net*net/(sigma*sigma);
            if(rejectedPowderPoint(row.x)) continue;
            wn+=net*(observed-row.intensityBkg)/(sigma*sigma); wd+=net*net/(sigma*sigma);
            un+=net*(observed-row.intensityBkg); ud+=net*net;
            if(net>peak) {peak=net;peakRatio=(observed-row.intensityBkg)/net;}
        }
        restorePowderRanges(count);
        console.info("Independent scale stimuli:",JSON.stringify({weighted:wn/wd,unit:un/ud,raw:rn/rd,peak:peakRatio,admittedDenominator:wd,rawDenominator:rd}));
        verify(wd>0 && rd>wd,"Admitted and rejected powder points both carry calculated Bragg intensity");
        verify(Math.abs(wn/wd-un/ud)>1e-4,"The powder load witness separates inverse-variance weights from unit weights");
        verify(Math.abs(wn/wd-peakRatio)>1e-4,"The powder load witness separates WLS from a background-subtracted peak ratio");
        verify(Math.abs(wn/wd-rn/rd)>1e-3,"Rejected observations change the optimum if the automatic initializer bypasses admission");
        verify(SettingsProof.write(source,"scaled.xye",data),"The powder scale witness stages nonproportional measurements and poisoned excluded points");
        return {k:wn/wd,unit:un/ud,peak:peakRatio,raw:rn/rd,data:data};
    }
    function loadPowderStimulus() {
        const stimulus=powderStimulus();
        verify(Session.project.loadDataInto(Session.project.currentExperiment,Qt.resolvedUrl(source+"/scaled.xye")),"The real powder data loader receives the admission-sensitive witness");
        ready();
        return stimulus;
    }
    function commonFactorWitness() {
        let wn=0,wd=0,un=0,ud=0;
        for(const row of Probe.rows(Session.project.currentExperiment.pattern)) {
            if(!isFinite(row.intensityCalc)||!isFinite(row.intensityMeas)||!(row.intensityMeasSu>0)) continue;
            const background=40+(row.x-10)/2, net=row.intensityCalc-background;
            fuzzyCompare(row.intensityBkg,background,1e-8,"Every scale trigger holds the authored background fixed");
            const observed=row.intensityMeas-background,w=1/(row.intensityMeasSu*row.intensityMeasSu);
            wn+=w*net*observed;wd+=w*net*net;un+=net*observed;ud+=net*net;
        }
        verify(wd>0,"Every phase trigger leaves admitted measured calculated signal");
        verify(Math.abs(wn/wd-un/ud)>1e-4,"Every phase-trigger witness distinguishes inverse-variance from unit weights");
        const count=removePowderRanges();
        let rn=0,rd=0;
        for(const row of Probe.rows(Session.project.currentExperiment.pattern)) {
            const net=row.intensityCalc-row.intensityBkg,w=1/(row.intensityMeasSu*row.intensityMeasSu);
            if(!isFinite(net)||!isFinite(row.intensityMeas)||!isFinite(w)) continue;
            rn+=w*net*(row.intensityMeas-row.intensityBkg);rd+=w*net*net;
        }
        restorePowderRanges(count);
        verify(Math.abs(rn/rd-wn/wd)>1e-3,"Every phase trigger's rejected points change the optimum if admission is bypassed");
        return wn/wd;
    }
    function scaleMatches(actual,expected) { return isFinite(actual) && Math.abs(actual-expected)<=3e-5; }
    function test_scale_gate_rejects_competing_estimators_and_missing_trigger() {
        const stimulus=powderStimulus();
        verify(scaleMatches(stimulus.k,stimulus.k),"The scale gate accepts the independent admitted weighted optimum");
        for(const wrong of [stimulus.unit,stimulus.peak,stimulus.raw,1])
            verify(!scaleMatches(wrong,stimulus.k),"The actual scale comparison rejects unit weights, peak ratio, raw admission and an omitted load trigger");
    }
    function test_measured_load_fits_common_scale_with_fixed_background_and_one_undo() {
        const stimulus=powderStimulus(), project=Session.project, before=scale().value;
        verify(project.loadDataInto(project.currentExperiment,Qt.resolvedUrl(source+"/scaled.xye")),"Loading measurements exercises the actual automatic scale trigger");
        ready();
        const actual=scale().value;
        // Also exercises the same admitted objective after initialization.
        const remaining=commonFactorWitness();
        project.undo();ready();
        fuzzyCompare(scale().value,before,1e-12,"One undo restores the pre-load scale with the measurement load");
        verify(project.currentExperiment.calculationOnly,"One undo restores the calculation-only experiment");
        verify(scaleMatches(actual,before*stimulus.k),"Loading data applies the independent weighted admitted optimum rather than a peak or unit-weight estimator");
        verify(scaleMatches(remaining,1),"The automatically scaled powder profile satisfies the admitted normal equation");
    }

    function phaseScales() {
        return Probe.rows(Session.project.currentExperiment.linkedStructures).map(row => ({id: row.structureId, value: row.scale.value}));
    }
    function test_powder_phase_change_data() {
        return [{tag: "add", action: "add"}, {tag: "remove", action: "remove"}];
    }
    function test_powder_phase_change(data) {
        loadPowderStimulus();
        const project = Session.project;
        const structure = SettingsProof.text(source, "structures/phase.edi");
        verify(SettingsProof.write(source, "extra.edi", structure.replace("data_phase", "data_extra").replace(/_cell.length_([abc]) 4/g, "_cell.length_$1 5")), "A second phase has a distinct lattice and independent peaks");
        verify(project.loadStructure(Qt.resolvedUrl(source + "/extra.edi")), "The actual structure loader supplies the second phase");
        ready();
        const links = project.currentExperiment.linkedStructures;
        if (data.action === "remove") {
            links.append();
            ready();
            verify(SettingsProof.write(source, "third.edi", structure.replace("data_phase", "data_third").replace(/_cell.length_([abc]) 4/g, "_cell.length_$1 6")), "The removal witness keeps two independent phase scales after removing a third");
            verify(project.loadStructure(Qt.resolvedUrl(source + "/third.edi")), "The actual structure loader supplies the third phase");
            links.append();
            ready();
        }
        let rows = Probe.rows(links);
        rows.forEach((row, index) => row.scale.value = [2, 3, 5][index]);
        ready();
        const before = phaseScales();
        const undoText = project.currentExperiment.text.inputText;
        if (data.action === "add")
            links.append();
        else
            links.remove(2);
        ready();
        const scales = phaseScales();
        compare(scales.length, 2, "A phase edit leaves two live scales whose ratio can distinguish one common factor from independent fitting");
        const expectedRatio = data.action === "add" ? 2 : 2 / 3;
        fuzzyCompare(scales[0].value / scales[1].value, expectedRatio, 1e-8, "Automatic scale adjustment preserves the pre-edit ratio, including the newly added phase's default scale");
        const remainingFactor=commonFactorWitness();
        project.undo();
        ready();
        compare(JSON.stringify(phaseScales()), JSON.stringify(before), "One undo restores every prior phase scale and the phase membership");
        compare(project.currentExperiment.text.inputText, undoText, "Undo restores the complete pre-edit experiment declaration");
        verify(scaleMatches(remainingFactor,1), "Adding or removing a phase automatically reaches the closed-form common-factor optimum");
    }

    function test_single_crystal_phase_replacement_fits_scale_and_undoes_once() {
        Session.closeProject();
        source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fitting_correctness/admission_project"));
        const structure = SettingsProof.text(source, "structures/phase.edi");
        verify(SettingsProof.write(source, "extra.edi", structure.replace("data_phase", "data_extra")), "The single-crystal replacement has the same independently known one-atom Ni amplitude");
        verify(Session.openProject(source), "The authored single-crystal scale witness opens through the actual Session");
        const project = Session.project;
        tryVerify(() => !project.calculating, 10000, "The single-crystal calculation settles before changing its linked phase");
        verify(project.loadStructure(Qt.resolvedUrl(source + "/extra.edi")), "A replacement single-crystal phase enters through the actual structure loader");
        tryVerify(() => !project.calculating, 10000, "The replacement structure load settles before the phase-link edit");
        const experiment = project.currentExperiment;
        experiment.scale.value = 2.3;
        const before = experiment.text.inputText;
        const oldId = experiment.linkedStructureId;
        experiment.linkedStructureId = "extra";
        tryVerify(() => !project.calculating, 10000, "Replacing the single-crystal phase publishes its later calculation");
        compare(experiment.linkedStructureId, "extra", "The phase selector really replaces the enabled single-crystal link");
        const loadedScale = experiment.scale.value;
        const expected=JSON.parse(SettingsProof.text(source,"reference.json")).bank.scale;
        project.undo();
        tryVerify(() => !project.calculating, 10000, "Undo of the single-crystal phase replacement settles");
        compare(experiment.linkedStructureId, oldId, "One undo restores the former single-crystal phase link");
        fuzzyCompare(experiment.scale.value, 2.3, 1e-12, "One undo restores the scale before the automatic phase-change fit");
        compare(experiment.text.inputText, before, "Undo restores the full pre-replacement single-crystal declaration");
        fuzzyCompare(loadedScale, expected, 1e-5, "Replacing a single-crystal phase fits only the independently merged, non-absent, non-excluded observations above the cutoff");
    }
    function test_running_fit_uses_plain_stop_then_plain_play() {
        open(true);
        scale().free = true;
        const fit = Session.project.fit;
        const button = control("statusBar.fit.button");
        compare(button.keyIcon, "play", "An idle measured-data fit exposes the plain play icon");
        fit.start();
        verify(fit.running, "The icon transition is observed during an actual started fit");
        compare(button.keyIcon, "stop", "An actual running fit exposes the plain stop icon");
        fit.cancel();
        tryVerify(() => !fit.running, 10000, "The actual fit settles after Stop");
        compare(button.keyIcon, "play", "A settled fit restores the plain play icon");
    }

    function test_single_crystal_measured_load_and_one_undo() {
        Session.closeProject();
        source = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/fitting_correctness/admission_project"));
        verify(Session.openProject(source), "The independent Ni experiment opens before replacing its measured reflections");
        const project = Session.project, experiment = project.currentExperiment;
        tryVerify(() => !project.calculating, 10000, "The saved single-crystal calculation settles before data replacement");
        experiment.scale.value = 2.3;
        const before = experiment.text.inputText;
        const original=SettingsProof.text(source,"experiments/bank.edi").split("_refln.intensity_meas_su\n")[1].trim().split("\n");
        // The original observations are nonproportional; scaling their intensities changes
        // merged scatter weights while retaining the rejected weak row below cutoff.
        const data=original.map(line=>{const row=line.trim().split(/\s+/).map(Number);row[3]=row[3]*1.7;return row.join(" ");}).join("\n")+"\n";
        verify(SettingsProof.write(source,"replacement.hkl",data),"The single-crystal replacement includes strong excluded/absent points and unequal-weight merged equivalents");
        verify(project.loadDataInto(experiment,Qt.resolvedUrl(source+"/replacement.hkl")),"The actual single-crystal data loader reaches the common-factor trigger");
        tryVerify(()=>!project.calculating,10000,"The single-crystal data replacement settles");
        const afterScale=project.currentExperiment.scale.value;
        const expected=JSON.parse(SettingsProof.text(source,"reference.json")).replacement.scale;
        project.undo();
        tryVerify(() => !project.calculating, 10000, "Undo of the single-crystal data load settles");
        fuzzyCompare(project.currentExperiment.scale.value,2.3,1e-12,"One undo restores the previous single-crystal scale with its data");
        compare(project.currentExperiment.text.inputText,before,"One undo restores the complete previous single-crystal input declaration");
        fuzzyCompare(afterScale,expected,1e-5,"Single-crystal data replacement composes merging, absence policy, omission, range and fit cutoff in the independent weighted optimum");
    }
    function test_disabled_phase_keeps_scale_while_remaining_phase_rescales() {
        loadPowderStimulus();
        const project=Session.project, experiment=project.currentExperiment;
        const structure=SettingsProof.text(source,"structures/phase.edi");
        verify(SettingsProof.write(source,"extra.edi",structure.replace("data_phase","data_extra")),"A second powder phase supplies a genuinely disabled scale witness");
        verify(project.loadStructure(Qt.resolvedUrl(source+"/extra.edi")),"The second structure is added through the actual loader");
        experiment.linkedStructures.append();
        ready();
        let rows=Probe.rows(experiment.linkedStructures);
        rows[0].scale.value=2;
        rows[1].scale.value=3;
        ready();
        verify(experiment.linkedStructures.setEnabled(1,false),"The phase-disable action exercises the declared removal trigger");
        ready();
        rows=Probe.rows(experiment.linkedStructures);
        const disabledScale=rows[1].scale.value;
        const remainingFactor=commonFactorWitness();
        project.undo();
        ready();
        const restored=Probe.rows(experiment.linkedStructures);
        verify(restored[1].enabled,"One undo restores the disabled phase membership");
        fuzzyCompare(restored[0].scale.value,2,1e-12,"One undo restores the first pre-disable scale");
        fuzzyCompare(restored[1].scale.value,3,1e-12,"One undo restores the second pre-disable scale");
        fuzzyCompare(disabledScale,3,1e-12,"A disabled link keeps its own scale during common-factor initialization");
        verify(scaleMatches(remainingFactor,1),"Disabling a phase fits only the remaining enabled phase contribution");
    }

    function test_powder_link_replacement_fits_scale_and_undoes_once() {
        loadPowderStimulus();
        const project=Session.project,experiment=project.currentExperiment;
        const structure=SettingsProof.text(source,"structures/phase.edi");
        verify(SettingsProof.write(source,"extra.edi",structure.replace("data_phase","data_extra").replace(/_cell.length_([abc]) 4/g,"_cell.length_$1 5")),"The powder replacement supplies different phase peaks");
        verify(project.loadStructure(Qt.resolvedUrl(source+"/extra.edi")),"The replacement powder structure enters through its actual loader");
        ready();
        experiment.scale.value=2.3;ready();
        const before=experiment.text.inputText,old=experiment.linkedStructureId;
        experiment.linkedStructureId="extra";ready();
        compare(experiment.linkedStructureId,"extra","The powder phase selector actually replaces its one linked structure");
        const remaining=commonFactorWitness();
        project.undo();ready();
        compare(experiment.linkedStructureId,old,"One undo restores the former powder linked structure");
        fuzzyCompare(experiment.scale.value,2.3,1e-12,"One undo restores the pre-replacement powder scale");
        compare(experiment.text.inputText,before,"One undo restores the full powder phase declaration");
        verify(scaleMatches(remaining,1),"Powder linked-structure replacement applies the admitted weighted common factor with the background fixed");
    }

    function test_common_scale_no_change_data() {
        return [{tag:"zero-calculation",zero:true},{tag:"negative-optimum",zero:false}];
    }
    function test_common_scale_no_change(data) {
        open(false);
        const project=Session.project;
        scale().value=data.zero?0:2.3;
        ready();
        const before=scale().value;
        let observations="", numerator=0, denominator=0;
        const rows=Probe.rows(project.currentExperiment.pattern);
        for(let index=0;index<rows.length;++index) {
            const row=rows[index];
            if(!isFinite(row.intensityCalc)||!isFinite(row.intensityBkg)) continue;
            const observed=row.intensityBkg/2, sigma=1+index%3, net=row.intensityCalc-row.intensityBkg;
            observations+=row.x+" "+observed+" "+sigma+"\n";
            numerator+=net*(observed-row.intensityBkg)/(sigma*sigma);
            denominator+=net*net/(sigma*sigma);
        }
        if(data.zero)
            fuzzyCompare(denominator,0,1e-20,"The zero-signal guard genuinely has a zero normal-equation denominator");
        else
            verify(denominator>0 && numerator<0,"The nonpositive-factor guard genuinely has calculated signal and a negative weighted optimum");
        verify(SettingsProof.write(source,"guard.xye",observations),"The no-change witness declares either zero calculated signal or a negative optimum");
        verify(project.loadDataInto(project.currentExperiment,Qt.resolvedUrl(source+"/guard.xye")),"The no-change guard is reached by a real measured-data load: "+project.lastError);
        ready();
        fuzzyCompare(scale().value,before,1e-12,"A zero denominator or nonpositive common factor leaves scales unchanged");
        const notes=Probe.rows(Session.loadWarnings).filter(row=>/phase scales.*left|scale.*unchanged/i.test(String(row.message)));
        compare(notes.length,1,"A skipped common factor posts one explanatory info line in Messages");
    }

}
