// SPDX-License-Identifier: BSD-3-Clause
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_cosio-d20_scan";
    return {schema: 2, workflow: "reference", example: EXAMPLE_ID, build: function () {
        const steps = [];
        function shot(id, page, description, actions, highlights, sidebar, captureImage) {
            steps.push({id: id, page: page, description: description, actions: actions,
                highlights: highlights || [], sidebar: sidebar || "", capture: captureImage !== false});
        }
        function tabs(page) {
            [["basic", "Main"], ["extras", "Extra"], ["text", "Text"], ["settings", "Settings"]].forEach(function (mode) {
                shot("scan-" + page + "-" + mode[0], page, "Inspect the scan's " + page + " controls",
                    ["appBar.tab." + page, "if-enabled:sideBar.tab." + mode[0], "sideBar.tab." + mode[0]],
                    ["workflow." + page + ".mainContent", "workflow." + page + ".manualSidebar"], mode[1]);
            });
        }
        function panel(id, group, description) {
            shot(id, "analysis", description,
                ["appBar.tab.analysis", "sideBar.tab.extras", "reveal:" + group, "expand:" + group], [group]);
        }
        shot("scan-experiment-before", "experiment", "Select a measurement from the cooling scan",
            ["platform:light", "theme:light", "appBar.tab.project", "open-cli-project:" + EXAMPLE_ID,
             "pin-time:01 Jan 2026 12:00:00", "appBar.tab.experiment", "sideBar.tab.basic"],
            ["workflow.experiment.mainContent", "group.experiments"]);
        shot("scan-run", "analysis", "Fit the scan and close the results dialog",
            ["appBar.tab.analysis", "sideBar.tab.basic", "statusBar.fit.button", "wait-fit", "close-fit-results"], [], "", false);
        ["project", "structure", "experiment", "analysis", "report"].forEach(tabs);
        panel("scan-mode", "group.fitting_mode", "Choose sequential, independent or single-dataset fitting");
        panel("scan-declaration", "group.sequential_fit", "Inspect the scan's data directory, file pattern and order");
        panel("scan-extraction", "group.sequential_fit_extract", "Inspect values extracted from each dataset");
        ["experiment", "analysis"].forEach(function (page) {
            ["stacked", "map"].forEach(function (view) {
                shot("scan-" + page + "-" + view, page, "Inspect the scan in the " + view + " view",
                    ["appBar.tab." + page, "sideBar.tab.basic", "mainArea." + page + ".tab." + view, "wait-scan:" + view],
                    ["workflow." + page + ".mainContent"]);
            });
        });
        shot("scan-evolution", "analysis", "Inspect a fitted parameter across the scan",
            ["appBar.tab.analysis", "mainArea.analysis.tab.evolution"], ["workflow.analysis.mainContent"]);
        shot("scan-correlations", "analysis", "Inspect correlations for the selected dataset",
            ["mainArea.analysis.tab.correlations"], ["workflow.analysis.mainContent"]);
        shot("scan-progress-controls", "analysis", "Review completed datasets, Follow and reset controls",
            ["mainArea.analysis.tab.fitting", "sideBar.tab.basic"], ["statusBar"]);
        return steps;
    }};
})();
