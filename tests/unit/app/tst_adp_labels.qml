import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import PatternPolishAcceptance 1.0
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1100
    height: 1000
    Component {
        id: adpComponent
        AtomSiteAdpGroup { width: 1100 }
    }
    Component {
        id: fieldComponent
        ParameterField { item: null; y: 500; width: 220 }
    }
    Component {
        id: analysisComponent
        ParametersGroup { y: 560; width: 1100; tableViewportHeight: 400 }
    }
    TestCase {
        id: test
        name: "AdpLabels"
        property var adps: null
        property var field: null
        property var analysis: null
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/e04_t1/editable-project")), "The independent ADP fixture opens");
        }
        function cleanup() {
            for (const object of [adps, field, analysis])
                if (object !== null) object.destroy();
            adps = null;
            field = null;
            analysis = null;
            wait(0);
            Session.closeProject();
            Probe.releaseScratchProjects();
        }
        function control(name) {
            return Render.descendants(adps).find(item => item.objectName === name);
        }
        function plain(text) {
            return String(text).replace(/₁/g, "1").replace(/₂/g, "2").replace(/₃/g, "3").replace(/\s/g, "");
        }
        function test_type_change_updates_heading_tooltip_analysis_and_fields_data() {
            return [
                {tag: "Uiso", previous: "Biso", type: "Uiso", iso: "Uiso", tensor: "", units: "Å²"},
                {tag: "Uani", previous: "Uiso", type: "Uani", iso: "U eq", tensor: "U", units: "Å²"},
                {tag: "Bani", previous: "Uani", type: "Bani", iso: "B eq", tensor: "B", units: "Å²"},
                {tag: "beta", previous: "Bani", type: "beta", iso: "B eq", tensor: "β", units: ""},
                {tag: "Biso", previous: "beta", type: "Biso", iso: "Biso", tensor: "", units: "Å²"}
            ];
        }
        function test_type_change_updates_heading_tooltip_analysis_and_fields(data) {
            adps = adpComponent.createObject(surface, {structure: Session.project.currentStructure});
            analysis = analysisComponent.createObject(surface, {project: Session.project});
            field = fieldComponent.createObject(surface);
            verify(adps !== null && analysis !== null && field !== null, "The real ADP, Analysis and parameter surfaces are created");
            const model = Session.project.currentStructure.atomSiteAdps;
            for (const expected of [data]) {
                const count = Probe.rows(model).length;
                for (let index = 0; index < count; ++index)
                    model.setType(index, expected.previous);
                wait(0);
                for (let index = 0; index < count; ++index)
                    model.setType(index, expected.type);
                tryVerify(() => Probe.rows(model).every(row => row.adpType === expected.type), 2000, "Every site publishes its new ADP type");
                const row = Probe.rows(model)[0];
                tryVerify(() => plain(row.adpIso.shortName) === plain(expected.iso), 2000, "The parameter symbol follows the declared ADP type");
                field.item = row.adpIso;
                tryVerify(() => plain(field.label) === plain(expected.iso), 2000, "The real parameter field refreshes its displayed label");
                tryVerify(() => control("atomSiteAdp.iso.0") !== undefined, 2000, "The ADP table renders the isotropic cell");
                const cell = control("atomSiteAdp.iso.0");
                if (expected.tensor !== "") {
                    const before = row.adpIso.value;
                    const shown = String(cell.text);
                    const number = shown.trim().replace(/−/g, "-");
                    verify(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(number), "The equivalent cell displays a complete numeric value");
                    const displayed = Number(number);
                    const quantum = before === 0 ? 0 : Math.pow(10, Math.floor(Math.log10(Math.abs(before))) - 4);
                    const tolerance = quantum / 2 + Math.abs(before) * Number.EPSILON * 8;
                    verify(Number.isFinite(displayed) && Math.abs(displayed - before) <= tolerance, "The equivalent value is accurate to the approved five significant digits");
                    mouseClick(cell);
                    keyClick(Qt.Key_A, Qt.ControlModifier);
                    for (let key = 0; key < 3; ++key) keyClick(Qt.Key_9);
                    keyClick(Qt.Key_Return);
                    compare(row.adpIso.value, before, "Typing cannot change an anisotropic equivalent");
                    compare(String(cell.text), shown, "A refused edit retains the displayed equivalent value");
                }
                const tooltip = String(cell.ToolTip.text);
                verify(plain(tooltip).includes(plain(expected.iso)), "The actual cell tooltip names the declared ADP quantity regardless of symbol spacing");
                verify(tooltip.includes("Å²"), "Every isotropic or equivalent displacement tooltip gives square angstroms");
                verify(tooltip.includes("_atom_site.adp_iso"), "The isotropic or equivalent tooltip names its exact saved item");
                verify(tooltip.includes(expected.tensor === "" ? "Isotropic displacement" : "Equivalent isotropic displacement"), "The tooltip distinguishes an editable isotropic value from a tensor equivalent");
                tryVerify(() => Render.texts(adps).some(item => item.text === "iso/eq"), 2000, "The rendered ADP heading retains the owner-approved iso/eq label");
                const rows = Probe.rows(Session.project.parameters);
                const parameter = rows.find(item => item.parameter && item.parameter.path === row.adpIso.path);
                // ADR-0019: a dependent has its field on Structure and no Analysis row.
                if (expected.tensor === "") {
                    verify(parameter !== undefined, "Analysis retains the editable isotropic parameter identity");
                    compare(plain(parameter.parameter.shortName), plain(expected.iso), "The Analysis row uses the same current symbol");
                    compare(parameter.parameter.displayUnits, "Å²", "The isotropic Analysis row gives its exact unit");
                } else {
                    verify(parameter === undefined, "A read-only equivalent has no fitted-parameter Analysis row");
                }
                if (expected.tensor !== "") {
                    for (const component of ["11", "22", "33", "12", "13", "23"]) {
                        const item = row["ani" + component];
                        verify(item !== null, "An anisotropic site exposes every tensor component");
                        compare(plain(item.shortName), expected.tensor + component, "Tensor symbols follow U, B or beta");
                        compare(item.displayUnits, expected.units, "Beta tensor components are unitless and U/B use square angstroms");
                        const tensorParameter = rows.find(entry => entry.parameter && entry.parameter.path === item.path);
                        // The first site is La at m-3m: only its 11 seed is independent.
                        compare(item.refinable, component === "11", "The cubic site exposes only its independent tensor seed");
                        if (component === "11") {
                            verify(tensorParameter !== undefined, "Analysis retains the independent tensor parameter identity");
                            compare(plain(tensorParameter.parameter.shortName), expected.tensor + component, "The Analysis tensor symbol refreshes with the type");
                            compare(tensorParameter.parameter.displayUnits, expected.units, "The Analysis tensor row gives its declared unit");
                        } else {
                            verify(tensorParameter === undefined, "A symmetry follower has no fitted-parameter Analysis row");
                        }
                    }
                }
            }
        }
        function test_reopened_powder_results_display_percent_and_bank_phase_identity() {
            Session.closeProject();
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/fit_quality/gui")), "The independent result fixture opens");
            const summary = Probe.rows(Session.project.fit.results);
            const agreement = Session.project.fit.results.agreement;
            const rows = Probe.rows(agreement);
            const columns = agreement.columns;
            compare(rows.length, 3, "The saved joint result retains its global row and both named datasets");
            compare(columns.map(column => column.factor).join("|"), "R<sub>p</sub>|R<sub>wp</sub>|R<sub>exp</sub>|cR<sub>p</sub>|cR<sub>wp</sub>|R<sub>Bragg</sub>|R<sub>F</sub>", "Agreement columns follow the owner-approved conventional, corrected and phase factor order");
            compare(columns[5].structure, "lbco", "The Bragg column names its actual linked structure");
            compare(columns[6].structure, "lbco", "The amplitude column names the same linked structure");
            const chi = PatternProof.fitRecord(Session.project).bankChi;
            for (const expected of [
                {
                    bank: "hrpt",
                    rwp: 12.34,
                    rp: 8.76,
                    rexp: 6.54,
                    crp: 18.76,
                    cwrp: 22.34,
                    chi: 3.56,
                    bragg: 4.32,
                    amplitude: 2.10
                },
                {
                    bank: "aux",
                    rwp: 31.23,
                    rp: 21.54,
                    rexp: 9.87,
                    crp: 41.56,
                    cwrp: 51.23,
                    chi: 7.89,
                    bragg: 14.32,
                    amplitude: 12.10
                }
            ]) {
                const matching = rows.filter(row => row.label === expected.bank);
                compare(matching.length, 1, "Every independent bank has exactly one agreement row with its own identity");
                const row = matching[0];
                compare(row.values.length, 7, "Every bank retains all profile, corrected and linked-phase factors");
                const values = [expected.rp, expected.rwp, expected.rexp, expected.crp, expected.cwrp, expected.bragg, expected.amplitude];
                values.forEach((value, column) => verify(Math.abs(Number(row.values[column]) - value) < .0051, "Every independently declared bank and phase factor is displayed as a percentage"));
                verify(Math.abs(Number(chi[expected.bank]) - expected.chi) < 1e-12, "The retired bank chi-square display remains checked in the loaded result with its dimensionless value");
            }
            const globalChi = summary.find(row => /χ/.test(row.metric));
            verify(globalChi !== undefined && !globalChi.value.includes("%"), "The summary's reduced chi-square stays dimensionless rather than a percentage");
            compare(globalChi.value, "5.56", "The summary retains the independently saved global reduced chi-square");
        }
        function test_latest_fit_clears_visible_uncertainty_and_undo_restores_it_data() {
            return ["single", "sequential", "independent"].map(mode => ({tag: mode, mode: mode}));
        }
        function test_latest_fit_clears_visible_uncertainty_and_undo_restores_it(data) {
            Session.closeProject();
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/fit_quality/uncertainty-" + data.mode)), "The rational polynomial fixture opens");
            const scratch = Probe.scratchProjectUrl();
            verify(Session.saveAs(scratch), "Every app transition runs in a fresh writable project copy");
            let project = Session.project;
            field = fieldComponent.createObject(surface);
            verify(field !== null, "The real uncertainty field is created");
            const parameterRow = Probe.rows(project.parameters).find(row => row.parameter && row.parameter.name === "coef" && row.parameter.free);
            verify(parameterRow !== undefined, "The independent input contains a free polynomial coefficient");
            let parameter = parameterRow.parameter;
            project.fit.start();
            verify(project.fit.running, "The first real app fit starts its worker");
            tryVerify(() => !project.fit.running, 10000, "The first real app fit completes");
            verify(parameter.hasUncertainty && parameter.uncertainty > 0, "The first app fit publishes its uncertainty");
            let before = parameter.uncertainty;
            if (data.mode !== "single") {
                verify(project.fit.canReset, "A completed scan exposes the existing Reset fits action");
                project.fit.reset();
                tryVerify(() => project.fit.available && !project.fit.canReset, 3000, "Reset starts a fresh scan rather than resuming a foreign free-set header");
                const prior = Probe.rows(project.parameters).find(row => row.parameter && row.parameter.name === "coef" && row.parameter.free);
                verify(prior !== undefined, "The reset scan has an independent free polynomial coefficient");
                parameter = prior.parameter;
                verify(parameter.hasUncertainty && parameter.uncertainty > 0, "The next scan starts from its actual positive prior uncertainty");
                before = parameter.uncertainty;
            }
            field.item = parameter;
            parameter.free = false;
            project.fit.start();
            verify(project.fit.running, "The fit after unchecking free starts its worker");
            tryVerify(() => !project.fit.running, 10000, "The fit after unchecking free completes");
            tryCompare(parameter, "hasUncertainty", false, 2000, "The fixed parameter has no latest-fit uncertainty");
            compare(field.parameter.error, "", "The visible parameter field clears its uncertainty text");
            project.undo();
            tryCompare(parameter, "hasUncertainty", true, 2000, "Fit undo restores the cleared uncertainty");
            verify(Math.abs(parameter.uncertainty-before) < 1e-12, "Fit undo restores the same prior uncertainty");
        }
    }
}
