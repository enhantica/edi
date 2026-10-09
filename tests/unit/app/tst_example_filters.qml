// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import "UiInteraction.js" as Ui

Item {
    width: 1000
    height: 1000
    Component {
        id: examplesComponent
        ExamplesGroup {
            width: 900
            collapsed: false
        }
    }
    TestCase {
        name: "ExampleFilters"
        when: windowShown
        property var sourceIds: []

        function resetFilters() {
            Session.examples.searchText = "";
            Session.examples.filterProperty = "purpose";
            Session.examples.filterValue = "";
        }
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            resetFilters();
            sourceIds = ids();
            verify(sourceIds.length > 0);
        }
        function cleanup() {
            resetFilters();
            Session.closeProject();
        }
        function ids() {
            const result = [];
            for (let i = 0; i < Session.examples.count; ++i)
                result.push(Session.examples.text(i, "exampleId"));
            return result;
        }
        function sameIds(actual, expected) {
            compare(JSON.stringify(actual), JSON.stringify(expected));
        }
        function normalized(text) {
            return String(text).normalize("NFKD").toLowerCase();
        }
        function properties() {
            const result = [];
            const model = Session.examples.filterProperties;
            for (let i = 0; i < model.count; ++i)
                result.push({
                    value: model.text(i, "value"),
                    title: model.text(i, "title")
                });
            return result;
        }
        function options() {
            const result = [];
            const model = Session.examples.filterOptions;
            for (let i = 0; i < model.count; ++i)
                result.push({
                    value: model.text(i, "value"),
                    title: model.text(i, "title"),
                    count: Number(model.text(i, "matchingCount"))
                });
            return result;
        }
        function option(value) {
            const found = options().filter(o => o.value === value);
            compare(found.length, 1, "Each facet value has exactly one option: " + value);
            return found[0];
        }
        function sample(id) {
            const index = ids().indexOf(id);
            verify(index >= 0, "Bundled source example exists: " + id);
            return normalized(Session.examples.text(index, "sample"));
        }
        function test_properties_and_known_fitting_modes() {
            sameIds(properties().map(p => p.value), ["purpose", "fittingMode", "facilities", "instruments", "sampleForm", "beamMode", "probe", "scatteringType", "dimensionality", "polarisation"]);
            for (const property of properties()) {
                verify(property.title.length > 0);
                verify(!/\(\d+\)/.test(property.title), "Property picker does not display counts");
            }
            const known = [["pd-neut-cwl_cosio-d20_start-1", "single"], ["pd-neut-tof_ncaf-wish-2bank_start-3", "joint"], ["pd-neut-cwl_cosio-d20_scan-3f", "sequential"], ["pd-xray-cwl_lif", "single"]];
            for (const [id, mode] of known) {
                verify(sourceIds.includes(id));
                sameIds(Session.examples.propertyValues(id, "fittingMode"), [mode]);
            }
        }
        function test_normalized_words_and_property_are_conjunctive() {
            Session.examples.searchText = "co2sio4 ILL";
            const matching = ids();
            verify(matching.includes("pd-neut-cwl_cosio-d20_start-1"));
            verify(matching.includes("pd-neut-cwl_cosio-d20_scan-3f"));
            verify(!matching.includes("pd-neut-cwl_lbco-hrpt_start-2"));
            Session.examples.filterProperty = "fittingMode";
            Session.examples.filterValue = "sequential";
            const expected = matching.filter(id => Session.examples.propertyValues(id, "fittingMode").includes("sequential"));
            verify(expected.length > 0);
            sameIds(ids(), expected);
            Session.examples.searchText = "Co₂SiO₄ ill";
            sameIds(ids(), expected);
            Session.examples.searchText = "co2sio4 ILL absent-word-that-no-example-has";
            compare(Session.examples.count, 0);
        }
        function test_purpose_is_separate_from_fitting_mode() {
            const simulation = Session.examples.propertyValues("pd-xray-cwl_lif", "purpose");
            const refinement = Session.examples.propertyValues("pd-neut-tof_ncaf-wish-2bank_start-3", "purpose");
            sameIds(simulation, ["simulation"]);
            sameIds(refinement, ["refinement"]);
            verify(simulation[0] !== refinement[0]);
            verify(simulation[0] !== "__unknown__" && refinement[0] !== "__unknown__");
            Session.examples.filterValue = simulation[0];
            verify(ids().includes("pd-xray-cwl_lif"));
            verify(!ids().includes("pd-neut-tof_ncaf-wish-2bank_start-3"));
            Session.examples.filterProperty = "fittingMode";
            compare(Session.examples.filterValue, "");
            Session.examples.filterValue = "joint";
            verify(ids().includes("pd-neut-tof_ncaf-wish-2bank_start-3"));
            verify(!ids().includes("pd-xray-cwl_lif"));
        }
        function test_facet_counts_match_unique_source_membership() {
            for (const property of properties()) {
                Session.examples.filterProperty = property.value;
                const choices = options();
                compare(choices[0].value, "");
                compare(choices[0].count, sourceIds.length);
                compare(new Set(choices.map(o => o.value)).size, choices.length);
                for (const choice of choices.slice(1)) {
                    const expected = sourceIds.filter(id => Session.examples.propertyValues(id, property.value).includes(choice.value));
                    verify(expected.length > 0);
                    compare(choice.count, expected.length, property.value + ": " + choice.value);
                    verify(choice.title.includes(String(choice.count)));
                    Session.examples.filterValue = choice.value;
                    sameIds(ids(), expected);
                    compare(option("").count, sourceIds.length, "Counts ignore the chosen value");
                }
                Session.examples.filterValue = "";
                sameIds(ids(), sourceIds);
            }
        }
        function test_counts_follow_search_and_zero_results_retain_choice() {
            Session.examples.filterProperty = "fittingMode";
            Session.examples.filterValue = "joint";
            Session.examples.searchText = "pd-xray-cwl_lif";
            compare(Session.examples.filterValue, "joint");
            compare(Session.examples.count, 0);
            compare(option("").count, 1);
            compare(option("single").count, 1);
            Session.examples.filterValue = "";
            sameIds(ids(), ["pd-xray-cwl_lif"]);
            Session.examples.searchText = "";
            sameIds(ids(), sourceIds);
        }
        function test_unknown_metadata_is_not_an_assumed_instrument() {
            sameIds(Session.examples.propertyValues("pd-xray-cwl_lif", "facilities"), ["__unknown__"]);
            sameIds(Session.examples.propertyValues("pd-xray-cwl_lif", "instruments"), ["__unknown__"]);
            for (const property of ["facilities", "instruments", "dimensionality", "polarisation"]) {
                Session.examples.filterProperty = property;
                const expected = sourceIds.filter(id => Session.examples.propertyValues(id, property).includes("__unknown__"));
                compare(option("__unknown__").count, expected.length);
                Session.examples.filterValue = "__unknown__";
                sameIds(ids(), expected);
            }
        }
        function test_multiphase_identity_includes_every_sample() {
            const yap = sample("pd-neut-cwl_yap-spodi_3k");
            verify(yap.includes("yalo3") && yap.includes("al2o3"), "Both YAlO3 and Al2O3 phases appear in the identity");
            const latp = sample("pd-xray-cwl_latp_scan-4f");
            verify(latp.includes("latp") || latp.includes("li1.3"));
            compare((latp.match(/alpo4/g) || []).length, 2, "Both AlPO4 polymorphs remain visible beside LATP");
            Session.examples.searchText = "YAlO3 Al2O3";
            verify(ids().includes("pd-neut-cwl_yap-spodi_3k"));
        }
        function test_filtered_delegate_opens_its_identity() {
            const expected = "pd-xray-cwl_lif";
            verify(sourceIds.indexOf(expected) > 0, "The fixture starts after the first source row");
            const group = createTemporaryObject(examplesComponent, parent);
            verify(group !== null);
            Session.examples.searchText = expected;
            sameIds(ids(), [expected]);
            verify(waitForPolish(group));
            let row = null;
            tryVerify(() => {
                row = Ui.find(group, "examples.open." + expected);
                return row !== null && Ui.exposed(row);
            });
            const point = Ui.clickPoint(row);
            let delay = 0;
            for (let item = row.parent; item; item = item.parent) {
                if (typeof item.pressDelay === "number")
                    delay = Math.max(delay, item.pressDelay + 1);
            }
            mouseClick(row, point.x, point.y, Qt.LeftButton, Qt.NoModifier, delay);
            tryCompare(Session, "openedExample", expected);
            verify(Session.hasProject, Session.lastError);
        }
    }
}
