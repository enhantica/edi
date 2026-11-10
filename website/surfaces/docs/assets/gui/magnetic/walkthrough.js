// SPDX-License-Identifier: BSD-3-Clause
// Sidebar groups only some projects show. Change EXAMPLE_ID and GROUPS together.
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_cosio-d20_2k";
    // Each row: scene id, app page, sidebar tab, group name, what the scene teaches.
    const GROUPS = [["group-space-group-magn","structure","basic","group.space_group_magn","Read the magnetic space group"],["group-propagation","structure","basic","group.parent_propagation_vector","Edit the propagation vectors"],["group-moments","structure","basic","group.atom_site_moment","Set the magnetic moments"],["group-symop","structure","extras","group.space_group_symop","Read the symmetry operators"],["group-magn-operators","structure","extras","group.space_group_symop_magn_operation","Read the magnetic operators"],["group-expanded-atoms","structure","extras","group.expanded_atom_site","Read every atom in the cell"],["group-expanded-moments","structure","extras","group.expanded_atom_site_moment","Read every moment in the cell"],["group-bonds","structure","extras","group.geom_bond","Read the bonds"],["group-form-factors","structure","extras","group.magnetic_form_factor","Set the magnetic form factors"]];
    return {schema: 2, workflow: "reference", example: EXAMPLE_ID, build: function () {
        const steps = [{id: "group-open", page: "project", description: "Open the example project",
            actions: ["platform:light", "theme:light", "home.start", "appBar.tab.project",
                "open-cli-project:" + EXAMPLE_ID, "pin-time:01 Jan 2026 12:00:00"],
            highlights: [], sidebar: "", capture: true}];
        GROUPS.forEach(function (row) {
            const step = {id: row[0], page: row[1], description: row[4],
                actions: ["appBar.tab." + row[1], "sideBar.tab." + row[2], "reveal:" + row[3], "expand:" + row[3]],
                highlights: [row[3]], sidebar: "", capture: true};
            if (row[1] === "analysis") {
                step.fitPhase = "setup";
            }
            steps.push(step);
        });
        return steps;
    }};
})();
