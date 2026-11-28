// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import PatternPolishAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "DisabledPhaseProjection"
    when: windowShown

    property var app
    property var breaches: []
    property var inventory: []
    readonly property var phases: ["obsidian", "saffron", "indigo", "azure"]
    Component {
        id: application
        Main {
            width: 1400
            height: 1000
            visible: true
        }
    }
    Component {
        id: parameters
        ParametersGroup {
            width: 950
            height: 550
        }
    }
    Component {
        id: magnetic
        MagneticPopup {}
    }
    Component {
        id: pattern
        PatternChart {
            width: 1200
            height: 690
            findKPage: true
            settingsPage: "pattern"
        }
    }

    Component {
        id: evolution
        EvolutionChart {
            width: 950
            height: 550
        }
    }

    function reaches(surface, payload, active, positive) {
        const text = (JSON.stringify(payload) ?? "").toLowerCase();
        inventory.push(surface);
        for (const phase of phases) {
            if (phase !== active && text.includes(phase))
                breaches.push(surface + " publishes disabled " + phase);
        }
        if (positive && !text.includes(positive))
            breaches.push(surface + " loses the positive witness " + positive);
    }
    function expect(surface, ok) {
        inventory.push(surface);
        if (!ok)
            breaches.push(surface);
    }
    function phaseLabel(item) {
        return Array.from(item.segments).filter(piece => piece.text !== undefined).map(piece => String(piece.text));
    }
    function render(base, label) {
        app.update();
        verify(waitForRendering(base, 5000), "The real " + label + " surface renders");
    }
    function inspectModel(project, active) {
        const analysis = project.analysis;
        const group = createTemporaryObject(parameters, app.contentItem, {
            project: project
        });
        verify(group && waitForPolish(group), "The actual Analysis Parameters group is laid out");
        const table = findChild(group, "parameters.list");
        const block = findChild(group, "parameters.datablock");
        const category = findChild(group, "parameters.category");
        const variability = findChild(group, "parameters.variability");
        verify(table && block && category && variability, "Analysis binds the real table and all three filters");
        const options = combo => Array.from({
                length: combo.count
            }, (_, i) => combo.textAt(i));
        const rows = Probe.rows(table.sourceModel).map(row => row.path);
        reaches("Analysis parameter rows", rows, active, active);
        reaches("Analysis datablocks", options(block), active, active);
        reaches("Analysis categories", options(category), active, null);
        reaches("Analysis variability", options(variability), active, null);
        expect("Analysis advertised total matches its actual table", table.count === rows.length);
        const blockOptions = options(block);
        const chosen = blockOptions.findIndex(label => label.toLowerCase().includes(active));
        const allCount = /\((\d+)\)\s*$/.exec(blockOptions[0]);
        const phaseCount = /\((\d+)\)\s*$/.exec(blockOptions[chosen] ?? "");
        expect("Analysis totals count the same visible population as the table", allCount && Number(allCount[1]) === rows.length && phaseCount && Number(phaseCount[1]) > 0);
        if (chosen >= 0) {
            block.activated(chosen);
            const filtered = Probe.rows(table.sourceModel).map(row => row.path);
            reaches("Analysis active datablock filter result", filtered, active, active);
            expect("Analysis phase filter count matches the filtered table", phaseCount && Number(phaseCount[1]) === filtered.length);
            block.activated(0);
        }
        const aliasName = {
            "obsidian": "zz_obsidian",
            "saffron": "aa_saffron",
            "indigo": "ab_indigo",
            "azure": "ac_azure"
        }[active];
        reaches("Analysis alias rows", Probe.rows(analysis.aliases).map(row => [row.id, row.parameter]), active, aliasName);
        reaches("Alias parameter offers", analysis.aliases.parameterNames, active, active);
        reaches("Analysis constraints", Probe.rows(analysis.constraints).map(row => [row.id, row.expression]), active, "zz_visible_rule");
        const beforeConstraint = Probe.rows(analysis.constraints).map(row => row.id);
        const relationText = analysis.text.text;
        analysis.constraints.append();
        const appendedRule = Probe.rows(analysis.constraints).find(row => !beforeConstraint.includes(row.id));
        expect("Constraint Append creates a selectable visible rule", appendedRule !== undefined);
        if (appendedRule)
            reaches("Appended constraint expression", appendedRule.expression, active, null);
        if (analysis.text.text !== relationText)
            project.undo();
        const aliasIds = () => Probe.rows(analysis.aliases).map(row => row.id);
        const before = aliasIds();
        const declarations = analysis.text.text;
        analysis.aliases.append();
        const appended = Probe.rows(analysis.aliases).find(row => !before.includes(row.id));
        expect("Alias Append creates one visible row", aliasIds().length === before.length + 1);
        if (appended)
            reaches("Appended alias target", appended.parameter, active, null);
        if (analysis.text.text !== declarations)
            project.undo();
        reaches("Correlation labels", project.correlations.labels, active, active === "obsidian" ? active : null);
        project.report.active = true;
        tryVerify(() => !project.report.calculating && Object.keys(project.report.model).length > 0, 15000, "The real report publishes its populated model");
        const report = project.report.model;
        reaches("Report payload", report, active, active === "obsidian" ? active : null);
        for (const section of Object.keys(report)) {
            const content = (JSON.stringify(report[section]) ?? "").toLowerCase();
            if (phases.some(phase => phase !== active && content.includes(phase)))
                console.log("Report sections with disabled phase data: " + section);
        }
        group.destroy();
    }

    function inspectChart(chart, project, active) {
        render(chart, "Pattern");
        const labels = Render.descendants(chart).filter(item => item.visible && item.objectName === "chart.bragg.label");
        const legend = Render.descendants(chart).filter(item => item.visible && item.objectName === "chart.legend.entry" && item.bragg);
        reaches("Pattern tick labels", labels.map(phaseLabel), active, active);
        reaches("Pattern legend", legend.map(phaseLabel), active, active);
        const tickCount = PatternProof.series(chart, "chart.series.bragg.").filter(row => row.points.some(point => Number.isFinite(point.x) && Number.isFinite(point.y))).length;
        const expected = active === "azure" ? 1 : 2;
        expect("Pattern has exactly the active phase's populated tick series", tickCount === expected);
        const fills = Render.series(chart).filter(area => /^chart\.series\.structure\.\d+$/.test(area.objectName) && area.outline.count > 0 && area.upperSeries.count > 0 && area.lowerSeries.count > 0 && area.outline.color.a > 0);
        expect("Pattern has exactly the active phase's populated component curves and fills", fills.length === expected);
        const index = project.currentExperimentIndex;
        compare(project.magneticParentOf(index), active === "azure" ? project.structureIndex(active) : -1, "Find k resolves the enabled Crystal candidate, excluding all disabled phases");
        chart.setPeakMode(true);
        if (active === "azure") {
            if (!project.kSearch.marks.length)
                project.toggleKMarkAt(35);
            const note = project.kSearch.note;
            const search = project.kSnapshot();
            expect("Find k snapshots the enabled Crystal only (" + note + "; " + project.lastError + ")", search.parent === project.structureIndex(active) && search.marks?.length > 0);
        } else {
            expect("Find k never snapshots a disabled Crystal", Object.keys(project.kSnapshot()).length === 0);
        }
        chart.setPeakMode(false);
        for (const phase of phases) {
            const choices = project.magneticDataChoices(project.structureIndex(phase));
            expect("Find k never admits a disabled or magnetic phase " + phase, phase === "azure" && phase === active || !choices.some(choice => choice.eligible));
        }
    }

    function switchPhase(project, name) {
        const model = project.currentExperiment.linkedStructures;
        const links = Probe.rows(model);
        verify(links.length === phases.length, "The management table retains all four links throughout visibility changes");
        for (const [i, row] of links.entries()) {
            if (row.enabled && row.structureId !== name)
                verify(model.setEnabled(i, false), "The real link toggle disables the old participant");
        }
        const target = links.findIndex(row => row.structureId === name);
        verify(target >= 0 && model.setEnabled(target, true), "The real link toggle enables the requested alternate");
        tryCompare(project, "calculating", false, 15000, "The active bank finishes recalculating after the link change");
    }

    function inspectAdd(name, broken) {
        const project = open(name);
        const prior = project.analysis.text.text;
        const count = project.structures.count;
        const aliases = () => Probe.rows(project.analysis.aliases).map(row => [row.id, row.parameter]);
        const priorAliases = aliases();
        const missingAliases = rows => rows.filter(row => row[1].startsWith("missing.preferred_orientation."));
        const textureRows = () => Probe.rows(project.currentExperiment.preferredOrientation).map(row => row.structureId);
        verify(textureRows().includes("azure"), "The actual active Crystal owns a March texture to carry through Add");
        if (broken) {
            const stored = SettingsProof.text(Probe.referenceUrl(name), "analysis/analysis.edi");
            verify(stored.includes("zz_missing missing.preferred_orientation.azure.march_r") && missingAliases(priorAliases).length === 1, "The real Analysis model retains the one independently declared missing-bank texture alias before Add");
        }
        const index = project.structureIndex("azure");
        const popup = createTemporaryObject(magnetic, app.contentItem, {
            project: project,
            structureIndex: index,
            structure: project.structureAt(index),
            initialK: "1/2,0,0",
            startMoments: false
        });
        verify(popup, "The same production magnetic Add popup accepts the ordinary Crystal context");
        popup.open();
        tryVerify(() => popup.opened && !popup.busy && popup.found !== null, 12000, "The ordinary popup obtains a commensurate graph");
        const nodes = popup.nodes.map((node, i) => node.bns && node.row === 1 && node.momentAllowed ? i : -1).filter(i => i >= 0);
        verify(nodes.length >= 2, "The Add witness reaches a real multi-candidate graph");
        for (const index of nodes.slice(0, 2))
            popup.toggle(index);
        const add = findChild(popup.footer, "magnetic.add");
        verify(add && add.enabled, "The actual Add button is available for both chosen candidates");
        mouseClick(add, add.width / 2, add.height / 2);
        tryVerify(() => project.structures.count !== count || popup.refusal !== "", 5000, "Add returns either an actual publication or an explicit refusal");
        if (project.structures.count !== count) {
            expect("Add publishes both children together", project.structures.count === count + 2);
            const children = project.lastMagneticAdded().map(row => row.name);
            expect("Add selects the first added magnetic phase", project.currentStructure.name === children[0]);
            expect("Both added phases inherit the parent's texture", children.length === 2 && children.every(name => textureRows().includes(name)));
            const after = project.analysis.text.text;
            const marchTargets = text => text.match(/\bd20\.(?:preferred_orientation\.)?[^\s]+\.march_r\b/g) ?? [];
            if (broken) {
                const published = aliases();
                expect("Add does not multiply or replace the pre-existing unresolved texture alias", JSON.stringify(missingAliases(published)) === JSON.stringify(missingAliases(priorAliases)));
                expect("Add copies a resolved alias for its enabled child even with the original unrelated error", published.some(row => row[0].startsWith("ac_azure_") && row[1].startsWith("d20.") && row[1].endsWith(".march_r")));
            } else {
                expect("Add carries the two resolved aliases for the children's actual bank", marchTargets(after).length === marchTargets(prior).length + 2);
            }
            project.undo();
            expect("Add Undo restores the exact analysis declarations", project.structures.count === count && project.analysis.text.text === prior && JSON.stringify(aliases()) === JSON.stringify(priorAliases));
        } else {
            if (!broken)
                expect("A healthy project admits both candidates (" + popup.refusal + ")", false);
            expect("Refused Add preserves its entire relation declaration", project.analysis.text.text === prior && JSON.stringify(aliases()) === JSON.stringify(priorAliases));
            popup.close();
        }
    }

    function init() {
        inventory = [];
        breaches = [];
        if (!SettingsProof.fileFacts(Probe.referenceUrl("projection"), "project.edi").exists)
            skip("The system gate provides the generated four-phase witness");
    }

    function open(name) {
        verify(Session.openProject(Probe.referenceUrl(name)), "The normal loader opens " + name + ": " + Session.lastError);
        app = application.createObject(null);
        verify(app && waitForRendering(app.contentItem), "The production app renders the scoped experiment");
        app.requestActivate();
        tryVerify(() => app.pagesWanted > 0 && app.pagesBuilt === app.pagesWanted, 12000, "All real workflow pages become available");
        const project = Session.project;
        tryCompare(project, "calculating", false, 15000, "The input project settles before inspection");
        return project;
    }

    function projectViolations() {
        console.log("Projection surfaces: " + JSON.stringify(inventory));
        compare(breaches, [], "Every exercised consumer excludes the disabled phases: " + JSON.stringify(breaches));
    }

    function test_healthy_add() {
        inspectAdd("additions", false);
        projectViolations();
    }

    function test_unresolved_add() {
        inspectAdd("broken", true);
        projectViolations();
    }

    function test_sequential() {
        const project = open("sequential");
        verify(project.scan && project.analysis.sequentialFit.declared, "A two-dataset sequential declaration opens in the real scan mode");
        const chart = createTemporaryObject(evolution, app.contentItem, {
            project: project
        });
        verify(chart && waitForPolish(chart), "The real Evolution selector is laid out");
        const selector = findChild(chart, "evolution.parameters");
        verify(selector && selector.blocks === project.evolution.parameters, "The Evolution parameter offers use the actual selector's rows");
        const offered = () => Probe.rows(selector.blocks).map(row => [row.name, row.label, row.group]);
        reaches("Evolution parameter offers before the scan", offered(), "obsidian", "obsidian");
        project.fit.start();
        verify(project.fit.running, "The sequential fit is admitted by the real worker");
        tryVerify(() => !project.fit.running && project.fit.outcome !== "", 45000, "The measured sequential fit retires through the ordinary fit controller");
        const csv = SettingsProof.text(Probe.referenceUrl("sequential"), "analysis/results.csv").trim().split(/\r?\n/);
        verify(csv.length === 3, "The sequential producer writes two real results and their CSV header");
        reaches("Sequential fitted parameter CSV", csv[0], "obsidian", "obsidian");
        reaches("Evolution parameter offers after the scan", offered(), "obsidian", "obsidian");
        expect("Evolution publishes fitted scan data", project.evolution.fitted);
        projectViolations();
    }

    function test_consumers() {
        const project = open("projection");
        expect("Structure management retains all four phases", Probe.rows(project.structures).length === phases.length);
        expect("Link management retains all three disabled alternatives", Probe.rows(project.currentExperiment.linkedStructures).filter(row => !row.enabled).length === 3);
        const oldCurves = Preferences.structureCurves, oldLegend = Preferences.patternLegendShown, oldDialog = Preferences.showFitResults;
        Preferences.structureCurves = true;
        Preferences.patternLegendShown = true;
        Preferences.showFitResults = false;
        const chart = createTemporaryObject(pattern, app.contentItem, {
            axisProject: project,
            experiment: project.currentExperiment
        });
        verify(chart && waitForPolish(chart), "The real chart is attached to this bank");
        for (const active of phases) {
            if (active !== "obsidian")
                switchPhase(project, active);
            inspectModel(project, active);
            inspectChart(chart, project, active);
        }
        switchPhase(project, "obsidian");
        const links = () => Probe.rows(project.currentExperiment.linkedStructures).filter(row => !row.enabled).map(row => [row.structureId, row.scale?.value ?? row.scale]);
        const disabledScale = links();
        verify(disabledScale.every(row => Number.isFinite(row[1])), "The disabled scales are read from their real parameter controls");
        const fit = project.fit;
        fit.start();
        verify(fit.running, "The bank fit is admitted by the real worker");
        tryVerify(() => !fit.running && fit.outcome !== "", 25000, "A real fit completes on the enabled magnetic phase");
        reaches("Fitted parameters", Probe.rows(project.analysis.fitStart).map(row => row.id), "obsidian", "obsidian");
        expect("A completed fit leaves every disabled phase scale unchanged", JSON.stringify(links()) === JSON.stringify(disabledScale));
        const dialog = findChild(app, "fit.results");
        verify(dialog, "The real fit-results dialog is available");
        dialog.open();
        tryCompare(dialog, "opened", true, 3000, "The actual fit results dialog opens");
        render(dialog.contentItem, "fit results");
        const agreement = findChild(dialog.contentItem, "fit.results.agreement");
        verify(agreement && agreement.count > 0, "The fit dialog contains real phase agreement rows and headings");
        reaches("Fit results columns", Render.texts(agreement.headerItem).map(item => item.text), "obsidian", "obsidian");
        dialog.close();
        chart.destroy();
        Preferences.structureCurves = oldCurves;
        Preferences.patternLegendShown = oldLegend;
        Preferences.showFitResults = oldDialog;
        projectViolations();
    }
    function cleanup() {
        if (app) {
            app.close();
            app.destroy();
            app = null;
            wait(0);
        }
        Session.closeProject();
    }
}
