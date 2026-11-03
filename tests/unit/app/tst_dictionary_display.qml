import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "DisplayedText.js" as Displayed
import "FileSpelling.js" as FileSpelling

Item {
TestCase {
    id: test
    name: "DictionaryDisplay"
    when: windowShown
    property var appWindow
    property var expected
    property var selectorGroup: null
    Component { id: application; Main {} }
    function init() {
        expected = JSON.parse(Probe.readReferenceFile("dictionary.json"));
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Display checks use the production application window");
        Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.hasProject, "The independent P1 display project opens in the app");
        verify(waitForRendering(appWindow.contentItem), "The production window renders before inspection");
    }
    function cleanup() {
        if (selectorGroup) selectorGroup.destroy();
        selectorGroup = null;
        Session.closeProject();
        appWindow.destroy();
    }
    function test_page_data() {
        return [{tag: "structure", page: "structure"},
                {tag: "experiment", page: "experiment"},
                {tag: "analysis", page: "analysis"},
                {tag: "report", page: "report"}];
    }
    function test_page(data) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, "The selected workflow page reaches the actual viewport");
        const tier = data.page === "analysis" ? "extras" : "basic";
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + tier);
        if (tab && !tab.checked) Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
        tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000,
                  "The selected sidebar finishes its transition before inspection");
        const root = Ui.page(appWindow);
        const anchor = {structure: "cell", experiment: "instrument", analysis: "minimizer", report: "reportContents"}[data.page];
        Ui.expandGroup(test, Probe, appWindow, "group." + anchor);
        const anchorGroup = Ui.control(Probe, appWindow, "group." + anchor);
        verify(anchorGroup !== null, "Each checked page reaches its expected real sidebar group");
        const shown = Review.descendants(anchorGroup).filter(item => Ui.rendered(item));
        verify(shown.length > 0, "Every checked page has real rendered content");
        for (const item of shown) {
            if (typeof item.text !== "string") continue;
            verify(!/^_[a-zA-Z0-9_]+\./.test(item.text),
                   "A rendered field never shows a raw EDI data name");
            verify(!expected.tokens.includes(item.text),
                   "A rendered field shows its dictionary option name rather than the stored token");
        }
        for (const group of [anchorGroup]) {
            const id = String(group.objectName).slice(6);
            const reference = expected.categories[id];
            if (!reference || typeof group.title !== "string") continue;
            compare(group.title, reference.loop ? reference.loop_title : reference.title,
                    "Every rendered category title follows its dictionary source");
            const categoryName = new RegExp(reference.edi_name + "(?![\\w.])");
            const pending = [group];
            const seen = new Set();
            let tooltip = null;
            while (pending.length) {
                const item = pending.pop();
                if (!item || seen.has(item)) continue;
                seen.add(item);
                if (item.parent === group.titleArea && typeof item.open === "function" && typeof item.text === "string")
                    tooltip = item;
                for (const child of item.data || []) pending.push(child);
                for (const child of item.children || []) pending.push(child);
                if (item.contentItem) pending.push(item.contentItem);
            }
            verify(tooltip !== null && categoryName.test(tooltip.text),
                   "Every rendered category title has its category in its title-area tooltip");
        }
        for (const field of shown.filter(item => item.item && typeof item.label === "string")) {
            const uid = String(field.item.category) + "." + String(field.item.name);
            const reference = expected.items[uid];
            if (!reference) continue;
            const labels = [reference.display_name];
            for (const token in (reference.variants || {})) {
                const variant = reference.variants[token];
                if (variant && variant.display_name) labels.push(variant.display_name);
            }
            verify(labels.includes(field.label),
                   "Every rendered parameter field uses its dictionary label or declared type variant");
            const tag = reference.edi_names ? reference.edi_names[0] : reference.cif_tag;
            verify([field].concat(Review.descendants(field)).some(item =>
                       typeof item.mapToItem === "function" && item.ToolTip && item.ToolTip.text.includes(tag)),
                   "Every rendered parameter label has its actual file item in a tooltip");
        }
        if (data.page !== "structure") return;
        const parameter = Session.project.currentStructure.cell.lengthA;
        parameter.value = 3.890915;
        Ui.expandGroup(test, Probe, appWindow, "group.cell");
        const field = Ui.control(Probe, appWindow, "cell.length_a");
        verify(field !== null, "Cell display is checked through its real field");
        Ui.scrollIntoView(field);
        const written = FileSpelling.parameter(Session.project.currentStructure.text.text, "cell.length_a");
        tryCompare(field, "text", written, 2000,
                   "The rendered cell field follows file/Text spelling under the active save rule");
        compare(field.label, expected.items["cell.length_a"].display_name,
                "The field label is read from the independently loaded dictionary file");
        verify(field.ToolTip.text.includes("_cell.length_a"),
               "The field tooltip identifies the EDI item it labels");
        field.forceActiveFocus();
        tryCompare(field, "text", written, 2000,
                   "An active edit field retains the same file/Text spelling");
        root.forceActiveFocus();
        compare(parameter.value, 3.890915, "Leaving an unchanged edit preserves the stored double");
        parameter.value = 3.8;
        tryCompare(field, "text", FileSpelling.parameter(Session.project.currentStructure.text.text, "cell.length_a"), 2000,
                   "A field retains exactly the file/Text trailing-zero spelling");
        compare(parameter.value, 3.8, "Display padding leaves the stored value unchanged");
    }
    function test_instrument_selectors() {
        const component = Qt.createComponent(Probe.referenceUrl("instrument-group.qml"), Component.PreferSynchronous);
        compare(component.status, Component.Ready, "The production instrument component loads: " + component.errorString());
        selectorGroup = component.createObject(appWindow.contentItem, {
            experiment: Qt.binding(() => Session.project ? Session.project.currentExperiment : null),
            width: 500
        });
        verify(selectorGroup !== null, "The selector actor instantiates the actual production component");
        const anchorGroup = selectorGroup;
        const facility = Review.find(selectorGroup, "instrument.facility");
        const instrument = Review.find(selectorGroup, "instrument.name");
        verify(facility !== null && instrument !== null, "The instrument group has both description selectors");
        compare(facility.label, "Facility", "The facility selector has a capitalised label");
        compare(instrument.label, "Instrument", "The instrument selector has a capitalised label");
        compare(facility.token, "", "An omitted facility displays Not specified");
        compare(instrument.token, "", "An omitted instrument displays Not specified");
        verify(!facility.enabled && !instrument.enabled, "Native experiment metadata selectors are disabled");
        for (const selector of [facility, instrument]) {
            const options = Probe.rows(selector.options);
            compare(options[0].token, "", "Each description list starts with the unspecified token");
            compare(options[0].label, "Not specified", "Each description list starts with Not specified");
        }
        const left = facility.mapToItem(anchorGroup, 0, 0);
        const right = instrument.mapToItem(anchorGroup, 0, 0);
        compare(left.y, right.y, "Description selectors occupy the same row");
        verify(left.x < right.x, "Facility is left of Instrument");
        const wavelength = Review.find(selectorGroup, "instrument.setup_wavelength");
        verify(wavelength.mapToItem(anchorGroup, 0, 0).y > left.y,
               "The description row precedes numeric instrument fields");
        const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(SettingsProof.write(directory, "pattern.xye", "10 21 2\n11 24 3\n12 26 4\n"),
               "The data-file control writes an independently authored measured pattern");
        verify(Session.project.loadData(0, String(directory) + "/pattern.xye"),
               "The data-file control loads an authored measured pattern");
        verify(facility.enabled && instrument.enabled, "Data-file descriptions can be selected");
        compare(facility.token, "", "A data-file facility starts unspecified");
        compare(instrument.token, "", "A data-file instrument starts unspecified");
        Session.project.currentExperiment.facilityToken = "MLZ";
        compare(Probe.rows(instrument.options).map(row => row.token).join("|"), "|SPODI",
                "MLZ powder instruments exclude single-crystal HEiDi");
        Session.project.currentExperiment.facilityToken = "PSI";
        compare(Probe.rows(instrument.options).map(row => row.token).join("|"), "|HRPT",
                "Changing facility changes the powder instrument list");
        Session.project.currentExperiment.instrumentToken = "HRPT";
        compare(instrument.token, "HRPT", "Selecting an instrument updates the real experiment");
        Session.project.currentExperiment.facilityToken = "";
        compare(instrument.token, "", "Clearing a facility clears its dependent instrument");
        const unspecified = Session.project.currentExperiment.text.text;
        verify(/_instrument\.facility\s+\?/.test(unspecified), "An unspecified facility is written as ?");
        verify(/_instrument\.name\s+\?/.test(unspecified), "An unspecified instrument is written as ?");
        const cif = "data_authored\n" +
            "_easydiffraction_experiment_type.sample_form powder\n" +
            "_easydiffraction_experiment_type.beam_mode 'constant wavelength'\n" +
            "_easydiffraction_experiment_type.radiation_probe neutron\n" +
            "_easydiffraction_experiment_type.scattering_type bragg\n" +
            "_easydiffraction_peak.type cwl-gaussian\n" +
            "_diffrn_radiation_wavelength.value 1.5406\n_pd_calib.2theta_offset 0.123\n" +
            "_diffrn_source.facility 'Authored source'\n_diffrn_source.beamline 'Authored instrument'\n" +
            "_pd_phase_block.id phase\n_pd_phase_block.scale 2.3000\n" +
            "loop_\n_pd_meas.2theta_scan\n_pd_meas.intensity_total\n_pd_meas.intensity_total_su\n" +
            "10 21 2\n11 24 3\n12 26 4\n";
        verify(SettingsProof.write(directory, "authored.cif", cif), "The CIF metadata control writes authored text");
        verify(Session.project.loadExperiments([String(directory) + "/authored.cif"]),
               "The app imports the authored CIF experiment through its public entrance: " + Session.lastError);
        compare(facility.token, "Authored source", "A CIF facility is filled from metadata");
        compare(instrument.token, "Authored instrument", "A CIF instrument is filled from metadata");
        verify(!facility.enabled && !instrument.enabled, "CIF metadata selectors are disabled");
        verify(Probe.rows(instrument.options).some(row => row.token === "Authored instrument"),
               "File metadata outside the catalogue remains visible in the selector");
        const native = Probe.readFile(SettingsProof.localPath(Probe.repoUrl(
            "tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi")))
            .replace("data_bank", "data_native_metadata") +
            "\n_instrument.name NativeInstrument\n_instrument.facility NativeFacility\n";
        verify(SettingsProof.write(directory, "native.edi", native), "The native metadata control writes authored text");
        verify(Session.project.loadExperiments([String(directory) + "/native.edi"]),
               "The app imports the authored native experiment");
        compare(facility.token, "NativeFacility", "A native facility is filled from metadata");
        compare(instrument.token, "NativeInstrument", "A native instrument is filled from metadata");
        verify(!facility.enabled && !instrument.enabled, "Native metadata selectors remain disabled");
        Session.closeProject();
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-cwl_pr2nio4-5c2_basic/project")),
               "The sample-form control opens a single-crystal example");
        const single = Session.project.currentExperiment;
        single.facilityToken = "MLZ";
        compare(Probe.rows(single.instrumentOptions).map(row => row.token).join("|"), "|HEiDi",
                "MLZ single-crystal instruments exclude powder SPODI");
    }

    function test_category_data() {
        return [
            {tag: "cell", page: "structure", tier: "basic", group: "cell", uid: "cell.length_a", value: 3.890915},
            {tag: "fractional", page: "structure", tier: "basic", group: "atom_site", uid: "atom_site.fract_x", value: 0.33333},
            {tag: "occupancy", page: "structure", tier: "basic", group: "atom_site", uid: "atom_site.occupancy", value: 0.5823456},
            {tag: "instrument", page: "experiment", tier: "basic", group: "instrument", uid: "instrument.setup_wavelength", value: 1.49412345},
            {tag: "peak", page: "experiment", tier: "basic", group: "peak", uid: "peak.broad_gauss_u", value: 0.123456789},
            {tag: "background", page: "experiment", tier: "basic", group: "background", uid: "background.intensity", value: 0.000012345678},
            {tag: "linked_structure", page: "experiment", tier: "basic", group: "linked_structure", uid: "linked_structure.scale", value: 1234567.8},
            {tag: "absorption", page: "experiment", tier: "extras", group: "absorption", uid: "absorption.mu_r", value: 0.036123456},
            {tag: "preferred_orientation", page: "experiment", tier: "extras", group: "preferred_orientation", uid: "preferred_orientation.march_r", value: 0.923456}
        ];
    }
    function test_category(data) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, "The category's page reaches the viewport before sidebar interaction");
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + data.tier);
        if (tab && !tab.checked) Ui.click(test, Probe, appWindow, "sideBar.tab." + data.tier);
        tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000,
                  "The category's sidebar finishes its transition");
        if (data.tag === "absorption")
            Session.project.currentExperiment.absorptionType = "cylinder-hewat";
        Ui.expandGroup(test, Probe, appWindow, "group." + data.group);
        const group = Ui.control(Probe, appWindow, "group." + data.group);
        verify(group !== null, "Every numeric category reaches its real group");
        const candidates = Review.descendants(group).filter(item => item.item &&
            String(item.item.category) + "." + String(item.item.name) === data.uid);
        verify(candidates.length > 0, "Every numeric witness reaches its own real parameter editor");
        const field = candidates[0];
        Ui.scrollIntoView(field);
        field.item.value = data.value;
        const written = FileSpelling.parameter(FileSpelling.block(Session.project, field.item), data.uid);
        verify(written !== "" && Number.isFinite(Number(written)),
               "Every numeric category has a nonempty numeric file/Text witness");
        tryVerify(() => Review.descendants(field).some(item =>
            Displayed.problem(item, written, false) === ""), 2000,
            "Every category field renders exactly its file/Text value in a native text item");
        compare(field.item.value, data.value, "The native rendered display preserves the input double");
    }

}

TestCase {
    id: stateTest
    visible: true
    width: 600
    height: 800
    name: "DescriptionLoadState"
    when: windowShown
    property var selectorGroup: null
    function cleanup() {
        if (selectorGroup) selectorGroup.destroy();
        selectorGroup = null;
        Session.closeProject();
    }
    function test_description_load_state_data() {
        const rows = [];
        for (const form of ["powder", "single"]) {
            for (const path of ["fresh", "replace", "reopen", "native_filename", "cif"]) {
                if (form === "single" && path === "native_filename") continue;
                rows.push({tag: form + "_" + path, form: form, path: path});
            }
        }
        return rows;
    }
    function test_description_load_state(data) {
        const single = data.form === "single";
        const project = single ? "docs/user/cli/sc-neut-cwl_pr2nio4-5c2_basic/project"
                               : "tests/fixtures/loop_parameter_ids/line-segment";
        verify(Session.openProject(Probe.repoUrl(project)), "The load-state witness opens its sample form");
        const directory = SettingsProof.copyProject(Probe.repoUrl(project));
        const component = Qt.createComponent(Probe.referenceUrl("instrument-group.qml"), Component.PreferSynchronous);
        compare(component.status, Component.Ready, "The load-state witness loads the production instrument group");
        selectorGroup = component.createObject(stateTest, {
            experiment: Qt.binding(() => Session.project ? Session.project.currentExperiment : null), width: 500
        });
        verify(selectorGroup !== null, "Load-state assertions inspect the actual production selectors");
        const facility = Review.find(selectorGroup, "instrument.facility");
        const instrument = Review.find(selectorGroup, "instrument.name");
        verify(facility !== null && instrument !== null, "Both sample forms expose facility and instrument selectors");
        const file = single ? "pattern.hkl" : "pattern.xye";
        const points = single ? "2 0 0 21 2\n4 0 0 24 3\n6 0 0 26 4\n"
                              : "10 21 2\n11 24 3\n12 26 4\n";
        verify(SettingsProof.write(directory, file, points), "Load-state data are independently authored observations");
        if (data.path === "cif") {
            const cif = "data_state\n" +
                "_easydiffraction_experiment_type.sample_form '" + (single ? "single crystal" : "powder") + "'\n" +
                "_easydiffraction_experiment_type.beam_mode 'constant wavelength'\n" +
                "_easydiffraction_experiment_type.radiation_probe neutron\n" +
                "_easydiffraction_experiment_type.scattering_type bragg\n" +
                (single ? "" : "_easydiffraction_peak.type cwl-gaussian\n_pd_calib.2theta_offset 0.123\n") +
                "_diffrn_radiation_wavelength.value 1.5406\n" +
                "_diffrn_source.facility 'Authored source'\n_diffrn_source.beamline 'Authored instrument'\n" +
                "_pd_phase_block.id " + (single ? "pr2nio4" : "phase") + "\n_pd_phase_block.scale 2.3\n" +
                (single ? "loop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n_refln.intensity_meas\n_refln.intensity_meas_su\n"
                        : "loop_\n_pd_meas.2theta_scan\n_pd_meas.intensity_total\n_pd_meas.intensity_total_su\n") + points;
            verify(SettingsProof.write(directory, "state.cif", cif), "The metadata control uses authored CIF declarations");
            verify(Session.project.loadExperiments([String(directory) + "/state.cif"]),
                   "Both sample forms import metadata-bearing CIF: " + Session.lastError);
        } else if (data.path === "native_filename") {
            const name = single ? "pr2nio4" : "bank";
            let native = Probe.readFile(SettingsProof.localPath(Probe.repoUrl(project + "/experiments/" + name + ".edi")));
            native = native.replace(/^data_\S+/, "data_state_native");
            native = native.replace(/_instrument\.(name|facility)[^\n]*\n/g, "");
            native += "\n_instrument.name 'Authored instrument'\n_instrument.facility 'Authored source'\n_data_source.file_name " + file + "\n";
            verify(SettingsProof.write(directory, "state.edi", native), "Native metadata includes a persisted data filename");
            verify(Session.project.loadExperiments([String(directory) + "/state.edi"]),
                   "The native import restores authored metadata and data provenance: " + Session.project.lastError);
        } else {
            if (data.path === "replace") {
                Session.project.currentExperiment.facilityToken = single ? "MLZ" : "PSI";
                Session.project.currentExperiment.instrumentToken = single ? "HEiDi" : "HRPT";
                compare(instrument.token, single ? "HEiDi" : "HRPT", "The replacement control starts with nonempty metadata");
            }
            verify(Session.project.loadData(0, String(directory) + "/" + file),
                   "The public data-file entrance loads observations for both sample forms");
            verify(facility.enabled && instrument.enabled, "A current data-file load enables both description selectors");
            compare(facility.token, "", "Every data-file transition resets facility to Not specified");
            compare(instrument.token, "", "Every data-file transition resets instrument to Not specified");
            if (data.path !== "reopen") return;
            Session.project.currentExperiment.facilityToken = single ? "MLZ" : "PSI";
            Session.project.currentExperiment.instrumentToken = single ? "HEiDi" : "HRPT";
            const destination = Probe.scratchProjectUrl();
            verify(Session.saveAs(destination), "Data-loaded observations and chosen descriptions save through the project writer");
            Session.closeProject();
            verify(Session.openProject(destination), "The saved project reopens through its native entrance");
        }
        const saved = data.path === "reopen";
        compare(facility.token, saved ? (single ? "MLZ" : "PSI") : "Authored source",
                "A native or CIF entrance displays the facility stored in that file");
        compare(instrument.token, saved ? (single ? "HEiDi" : "HRPT") : "Authored instrument",
                "A native or CIF entrance displays the instrument stored in that file");
        verify(!facility.enabled && !instrument.enabled,
               "Native and CIF entrances lock descriptions even when measured-data provenance is present");
    }

}
}
