// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQml.Models
import QtTest
import edi.app

TestCase {
    id: test
    name: "ParameterGroups"
    when: windowShown

    ListModel {
        id: rows
    }
    ParameterFilterModel {
        id: filter
        sourceModel: rows
    }
    Instantiator {
        id: shown
        model: filter
        delegate: QtObject {
            required property string path
        }
    }
    function append(kind, category, names) {
        names.forEach(name => rows.append({
                blockKind: kind,
                category: category,
                name: name,
                displayName: name,
                path: kind + "." + category + "." + name,
                free: rows.count % 2 === 0
            }));
    }
    function init() {
        failOnWarning(/.*/);
        filter.sourceModel = rows;
        filter.nameFilter = "";
        filter.variability = ParameterFilterModel.All;
        filter.categoryFilter = "";
        rows.clear();
    }
    function paths() {
        const result = [];
        for (let i = 0; i < shown.count; ++i)
            result.push(shown.objectAt(i).path);
        return result.sort();
    }
    function expect(group, kind, category, names) {
        filter.categoryFilter = group;
        compare(paths(), names.map(name => kind + "." + category + "." + name).sort());
    }
    function test_atoms() {
        append("structure", "atom_site", ["fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"]);
        append("structure", "atom_site_aniso", ["adp_11", "adp_22", "adp_33", "adp_12", "adp_13", "adp_23"]);
        append("structure", "cell", ["length_a"]);
        expect("@coordinates", "structure", "atom_site", ["fract_x", "fract_y", "fract_z"]);
        expect("@occupancies", "structure", "atom_site", ["occupancy"]);
        filter.categoryFilter = "@displacement";
        compare(shown.count, 7);
        verify(paths().every(path => path.includes(".adp_")));
        filter.categoryFilter = "@atoms";
        compare(shown.count, 11);
    }
    function test_peak_subsets_data() {
        return [
            {
                tag: "CW",
                broad: ["broad_gauss_u", "broad_gauss_v", "broad_gauss_w", "broad_lorentz_x", "broad_lorentz_y"],
                mix: ["mixing_eta_0", "mixing_eta_1"],
                asym: ["asym_fcj_1", "asym_fcj_2", "asym_beba_a0", "asym_beba_b0", "asym_beba_a1", "asym_beba_b1"]
            },
            {
                tag: "TOF",
                broad: ["broad_gauss_sigma_0", "broad_gauss_sigma_1", "broad_gauss_sigma_2", "broad_gauss_size", "broad_gauss_strain", "broad_lorentz_gamma_0", "broad_lorentz_gamma_1", "broad_lorentz_gamma_2", "broad_lorentz_size", "broad_lorentz_strain"],
                mix: [],
                asym: ["rise_alpha_0", "rise_alpha_1", "decay_beta_0", "decay_beta_1"]
            }
        ];
    }
    function test_peak_subsets(data) {
        append("experiment", "peak", data.broad.concat(data.mix, data.asym));
        append("experiment", "instrument", ["offset"]);
        expect("@peakBroadening", "experiment", "peak", data.broad);
        expect("@peakAsymmetry", "experiment", "peak", data.asym);
        if (data.mix.length)
            expect("@peakMixing", "experiment", "peak", data.mix);
        else
            verify(!filter.categories.includes("@peakMixing"));
        expect("peak", "experiment", "peak", data.broad.concat(data.mix, data.asym));
        verify(!filter.categories.includes("@peakShape"));
    }
    function test_every_group_count_and_combined_filters() {
        append("structure", "cell", ["length_a", "length_b"]);
        append("structure", "atom_site", ["fract_x", "occupancy", "adp_iso"]);
        append("experiment", "peak", ["broad_gauss_u", "mixing_eta_0", "rise_alpha_0", "asym_beba_a0"]);
        ["instrument", "background", "linked_structure", "absorption", "preferred_orientation", "scattering_source", "future_category"].forEach(category => append("experiment", category, ["one", "two"]));
        const groups = filter.categoryGroups;
        groups.forEach(group => {
            filter.categoryFilter = group.key;
            compare(shown.count, group.count, group.title);
            compare(group.datablock, group.key === "@structure" || group.key === "@experiment");
            filter.variability = ParameterFilterModel.Free;
            const expected = [];
            for (let i = 0; i < rows.count; ++i)
                if (rows.get(i).free)
                    expected.push(rows.get(i).path);
            verify(paths().every(path => expected.includes(path)), group.title + " respects free filter");
            filter.nameFilter = "ONE";
            verify(paths().every(path => path.endsWith(".one")), group.title + " respects name filter");
            filter.nameFilter = "";
            filter.variability = ParameterFilterModel.All;
        });
        verify(filter.categories.includes("future_category"));
    }
    function test_subsets_must_narrow_and_follow_source_changes() {
        append("experiment", "peak", ["broad_gauss_u"]);
        append("structure", "atom_site", ["occupancy"]);
        verify(filter.categories.includes("peak"));
        verify(filter.categories.includes("@atoms"));
        verify(!filter.categories.includes("@peakBroadening"));
        verify(!filter.categories.includes("@occupancies"));
        append("experiment", "peak", ["rise_alpha_0"]);
        verify(filter.categories.includes("@peakBroadening"));
        verify(filter.categories.includes("@peakAsymmetry"));
        rows.setProperty(2, "name", "broad_lorentz_x");
        verify(!filter.categories.includes("@peakAsymmetry"));
        verify(!filter.categories.includes("@peakBroadening"));
        filter.sourceModel = null;
        compare(filter.categoryGroups.length, 1);
        compare(filter.categoryGroups[0].count, 0);
        compare(shown.count, 0);
    }
}
