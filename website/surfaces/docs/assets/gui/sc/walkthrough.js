// SPDX-License-Identifier: BSD-3-Clause
// Sidebar groups only some projects show. Change EXAMPLE_ID and GROUPS together.
(function () {
    const EXAMPLE_ID = "sc-neut-cwl_tb2ti2o7-heidi";
    // Each row: scene id, app page, sidebar tab, group name, what the scene teaches.
    const GROUPS = [["group-extinction","experiment","basic","group.extinction","Set the extinction correction"],["group-reflns","experiment","extras","group.reflns","Set which reflections count as observed"],["group-refln","experiment","extras","group.refln","Read the Bragg reflections"],["group-refine-ls","analysis","extras","group.refine_ls","Set which reflections a fit uses"]];
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
