import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

TestCase {
    id: test
    name: "Fittability"
    when: windowShown
    property var appWindow
    property var group
    property var savedShowStates
    Component {
        id: host
        ApplicationWindow {
            width: 1000
            height: 800
            visible: true
        }
    }
    Component {
        id: parameters
        ParametersGroup {
            width: 920
            tableViewportHeight: 700
        }
    }

    function init() {
        Session.closeProject();
        savedShowStates = null;
        if (typeof Preferences.analysisShowNotMeasured === "boolean") {
            savedShowStates = [Preferences.analysisShowNotMeasured, Preferences.analysisShowBySymmetry, Preferences.analysisShowByConstraint, Preferences.analysisShowFixedSettings];
            Preferences.analysisShowNotMeasured = true;
            Preferences.analysisShowBySymmetry = true;
            Preferences.analysisShowByConstraint = true;
            Preferences.analysisShowFixedSettings = true;
        }
        appWindow = host.createObject(null);
        verify(appWindow !== null, "Fit eligibility is observed in a real Qt window");
    }
    function cleanup() {
        if (group)
            group.destroy();
        group = null;
        if (savedShowStates) {
            Preferences.analysisShowNotMeasured = savedShowStates[0];
            Preferences.analysisShowBySymmetry = savedShowStates[1];
            Preferences.analysisShowByConstraint = savedShowStates[2];
            Preferences.analysisShowFixedSettings = savedShowStates[3];
        }
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function open(relative) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl(relative))), "The authored project opens through the real application loader");
        group = parameters.createObject(appWindow.contentItem, {
            project: Session.project
        });
        verify(group !== null && waitForPolish(group), "The production Analysis table completes layout");
        return Ui.find(group, "parameters.list", true);
    }
    function rows() {
        return Probe.rows(Session.project.parameters);
    }
    function selectRow(table, block, category, name, rowLabel) {
        const filter = table.sourceModel;
        filter.clearFilters();
        filter.datablockFilter = block;
        filter.categoryFilter = category;
        filter.nameFilter = name;
        verify(waitForPolish(group), "The selected actual table filter completes layout");
        const found = Probe.rows(filter);
        const index = found.findIndex(row => row.name === name && (!rowLabel || row.rowLabel === rowLabel));
        verify(index >= 0, "Analysis includes the requested numerical input: " + block + "." + category + "." + name);
        table.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(table), "The selected numerical input has an instantiated visible table delegate");
        return {
            row: found[index],
            index: index
        };
    }
    function test_reasons_data() {
        return [
            {
                tag: "radius",
                project: "sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction",
                block: "experiment:heidi",
                category: "extinction",
                field: "crystal_radius",
                reason: "a descriptor, never fitted"
            },
            {
                tag: "limit",
                project: "pd-neut-cwl_hs-hrpt",
                block: "experiment:hrpt",
                category: "peak",
                field: "asym_beba_limit",
                reason: "a descriptor, never fitted"
            },
            {
                tag: "cell",
                project: "sc-neut-cwl_tb2ti2o7-heidi_basic",
                block: "structure:tb2ti2o7",
                category: "cell",
                field: "length_a",
                reason: "this fit's data cannot determine it"
            },
            {
                tag: "tied-cell",
                project: "sc-neut-cwl_tb2ti2o7-heidi_basic",
                block: "structure:tb2ti2o7",
                category: "cell",
                field: "length_b",
                reason: "set by symmetry"
            },
            {
                tag: "coordinate",
                project: "sc-neut-cwl_tb2ti2o7-heidi_basic",
                block: "structure:tb2ti2o7",
                category: "atom_site",
                field: "fract_x",
                label: "Tb",
                reason: "set by symmetry"
            },
            {
                tag: "constraint",
                project: "sc-neut-tof_taurine_fit",
                block: "experiment:senju_2",
                category: "extinction",
                field: "coefficient_11",
                reason: "set by a constraint"
            },
            {
                tag: "dispersion",
                project: "pd-xray-cwl_pbso4-lab",
                block: "experiment:lab",
                category: "instrument",
                field: "setup_wavelength",
                reason: "the fit cannot vary it yet"
            }
        ];
    }
    function test_reasons(data) {
        const table = open("docs/user/cli/" + data.project + "/project");
        const selected = selectRow(table, data.block, data.category, data.field, data.label);
        compare(selected.row.fittable, false, "A blocked input remains listed with fitting disabled");
        verify(String(selected.row.fitReason).startsWith(data.reason), "Every actual Analysis row carries the shared reason text");
        const checkbox = Ui.find(group, "parameters.free." + selected.index, true);
        verify(checkbox !== null, "The blocked row has a real Free checkbox");
        verify(!checkbox.enabled && !checkbox.checked, "A fixed blocked input has a visible disabled unticked Free checkbox");
        const tooltip = "Cannot be fitted: " + String(selected.row.fitReason);
        const tooltipSources = [checkbox].concat(Review.descendants(checkbox));
        verify(tooltipSources.some(item => item.ToolTip && item.ToolTip.text === tooltip || item.text === tooltip), "The actual Free control explains its disabled state with the shared tooltip");
        if (data.tag === "dispersion") {
            verify(String(selected.row.fitReason).includes("sasaki1989") && String(selected.row.fitReason).includes("declare _scattering_source.xray_dispersion none to fit it"), "The app explains the active dispersion limitation and its supported alternative");
        }
    }
    function test_exact_inventory_and_partition() {
        const table = open("tests/fixtures/fittability/projects/single");
        const expected = ["phase.cell.length_a", "phase.cell.length_b", "phase.cell.length_c", "phase.cell.angle_alpha", "phase.cell.angle_beta", "phase.cell.angle_gamma", "phase.atom_site.Ni.fract_x", "phase.atom_site.Ni.fract_y", "phase.atom_site.Ni.fract_z", "phase.atom_site.Ni.occupancy", "phase.atom_site.Ni.adp_iso", "bank.instrument.setup_wavelength", "bank.extinction.crystal_radius", "bank.extinction.domain_radius", "bank.linked_structure.phase.scale"];
        const actual = rows().map(row => [row.blockName, row.category, row.rowLabel, row.name].filter(x => x !== "").join("."));
        compare(JSON.stringify(actual.sort()), JSON.stringify(expected.sort()), "The unfiltered project model equals every numerical input, with no data, results or computed rows");
        const filter = table.sourceModel;
        compare(Probe.rows(filter).map(row => [row.blockName, row.category, row.rowLabel, row.name].filter(x => x !== "").join(".")).sort(), expected.sort(), "Selecting every show group restores every numerical input in the actual Analysis view");
        compare(JSON.stringify(filter.variabilityCounts), JSON.stringify([15, 0, 7, 8]), "Free, Fixed and Not fittable partition the independent single-crystal input inventory");
        const picker = Ui.find(group, "parameters.variability", true);
        verify(picker !== null && picker.count === 4, "The actual variability picker includes Not fittable");
        filter.variability = ParameterFilterModel.NotFittable;
        compare(Probe.rows(filter).length, 8, "Not fittable selects exactly the eight blocked numerical inputs");
        filter.variability = ParameterFilterModel.All;
        filter.datablockFilter = "structure:phase";
        filter.categoryFilter = "cell";
        compare(JSON.stringify(filter.variabilityCounts), JSON.stringify([6, 0, 0, 6]), "Variability counts follow both datablock and category selections");
        filter.clearFilters();
        const items = [];
        for (let i = 0; i < rows().length; ++i)
            items.push(filter.parameterAt(i));
        Session.project.setParametersFree(items, true);
        compare(rows().filter(row => row.free).length, 7, "Free all changes only the seven fittable inputs");
        compare(JSON.stringify(filter.variabilityCounts), JSON.stringify([15, 7, 0, 8]), "Free all preserves the partition and every blocked row");
    }
    function test_readonly_descriptors_data() {
        return [
            {
                tag: "position",
                project: "tests/fixtures/fittability/projects/powder",
                category: "background",
                field: "position",
                label: "a",
                value: 20
            },
            {
                tag: "cutoff",
                project: "tests/fixtures/fittability/projects/powder",
                category: "peak",
                field: "cutoff_fwhm",
                value: 5
            },
            {
                tag: "order",
                project: "tests/fixtures/loop_parameter_ids/polynomial",
                category: "background",
                field: "order",
                label: "ramp",
                value: 1
            },
            {
                tag: "texture",
                project: "tests/fixtures/loop_parameter_ids/line-segment",
                category: "preferred_orientation",
                field: "index_l",
                label: "phase",
                value: 1
            }
        ];
    }
    function test_readonly_descriptors(data) {
        const table = open(data.project);
        const selected = selectRow(table, "experiment:bank", data.category, data.field, data.label);
        compare(selected.row.value, data.value, "The descriptor displays its authored numerical value");
        compare(selected.row.fittable, false, "Non-Parameter descriptors cannot be freed");
        const field = Ui.find(group, "parameters.value." + selected.index, true);
        verify(field !== null, "The descriptor has a real displayed value cell");
        verify(field.readOnly || !field.enabled || !field.activeFocusOnPress, "Non-Parameter descriptor values are read-only in Analysis");
    }
    function test_context_change_keeps_a_clearable_free_flag() {
        const table = open("tests/fixtures/fittability/projects/mixed");
        const selected = selectRow(table, "structure:phase", "cell", "length_a");
        selected.row.parameter.free = true;
        compare(selected.row.parameter.free, true, "The powder experiment makes the shared cell fittable");
        const experiments = Probe.rows(Session.project.experiments);
        const powder = experiments.findIndex(row => row.name === "powder");
        verify(powder >= 0, "The changing context includes the authored powder experiment");
        Session.project.removeExperiment(powder);
        const changed = selectRow(table, "structure:phase", "cell", "length_a");
        compare(changed.row.free, true, "Removing powder preserves the existing free flag");
        compare(changed.row.fittable, false, "Removing powder re-derives the data limitation");
        const checkbox = Ui.find(group, "parameters.free." + changed.index, true);
        verify(checkbox !== null && checkbox.checked && checkbox.enabled, "The blocked surviving free flag remains enabled solely so it can be cleared");
        const point = Ui.clickPoint(checkbox);
        verify(point !== null, "The clearable free checkbox accepts real pointer input");
        mouseClick(checkbox, point.x, point.y);
        tryCompare(checkbox, "checked", false, 500, "The user can clear the stale free flag");
        tryCompare(checkbox, "enabled", false, 500, "The cleared blocked flag cannot be re-enabled");
    }
}
