// SPDX-License-Identifier: BSD-3-Clause
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_cosio-d20_scan";
    return {schema: 2, workflow: "reference", example: EXAMPLE_ID, build: function (capture) {
        const scan = capture.fixture.values.fittingMode.some(function (mode) { return mode === "sequential" || mode === "independent"; });
        const prefix = scan ? "scan" : "joint";
        const steps = [];
        function shot(id, page, description, actions, highlights, sidebar, captureImage) {
            steps.push({id: id, page: page, description: description, actions: actions,
                highlights: highlights || [], sidebar: sidebar || "", capture: captureImage !== false});
        }
        function tabs(page) {
            [["basic", "Main"], ["extras", "Extra"], ["text", "Text"], ["settings", "Settings"]].forEach(function (mode) {
                shot(prefix + "-" + page + "-" + mode[0], page, "Inspect the project's " + page + " controls",
                    ["appBar.tab." + page, "if-enabled:sideBar.tab." + mode[0], "sideBar.tab." + mode[0]],
                    ["workflow." + page + ".mainContent", "workflow." + page + ".manualSidebar"], mode[1]);
            });
        }
        function panel(id, group, description) {
            shot(id, "analysis", description,
                ["appBar.tab.analysis", "sideBar.tab.extras", "reveal:" + group, "expand:" + group], [group]);
        }
        shot(prefix + "-experiment-before", "experiment", "Select an experiment or dataset",
            ["platform:light", "theme:light", "home.start", "appBar.tab.project", "open-cli-project:" + EXAMPLE_ID,
             "pin-time:01 Jan 2026 12:00:00", "appBar.tab.experiment", "sideBar.tab.basic"],
            ["workflow.experiment.mainContent", "group.experiments"]);
        shot(prefix + "-run", "analysis", "Fit the project and close the results dialog",
            ["appBar.tab.analysis", "sideBar.tab.basic", "statusBar.fit.button", "wait-fit", "close-fit-results"], [], "", false);
        ["project", "structure", "experiment", "analysis", "report"].forEach(tabs);
        panel(prefix + "-mode", "group.fitting_mode", scan ? "Choose sequential, independent or single-dataset fitting" : "Inspect joint fitting for the project's experiments");
        if (scan) {
        panel("scan-declaration", "group.sequential_fit", "Inspect the scan's data directory, file pattern and order");
        panel("scan-extraction", "group.sequential_fit_extract", "Inspect values extracted from each dataset");
        } else {
            panel("joint-weights", "group.joint_fit", "Set the relative weights of the experiments in the joint fit");
            panel("joint-result", "group.fit_result", "Inspect the overall outcome and statistics of the completed fit");
            panel("joint-experiment-results", "group.fit_result_bank", "Compare fit statistics for the individual experiments");
            panel("joint-structure-results", "group.fit_result_phase", "Inspect the structure contributions recorded for each experiment");
        }
        ["experiment", "analysis"].forEach(function (page) {
            ["stacked", "map"].forEach(function (view) {
                shot(prefix + "-" + page + "-" + view, page, "Inspect the scan in the " + view + " view",
                    ["appBar.tab." + page, "sideBar.tab.basic", "mainArea." + page + ".tab." + view, "wait-scan:" + view],
                    ["workflow." + page + ".mainContent"]);
            });
        });
        if (scan) {
        shot("scan-evolution", "analysis", "Inspect a fitted parameter across the scan",
            ["appBar.tab.analysis", "mainArea.analysis.tab.evolution"], ["workflow.analysis.mainContent"]);
        shot("scan-progress-controls", "analysis", "Review completed datasets, Follow and reset controls",
            ["mainArea.analysis.tab.fitting", "sideBar.tab.basic"], ["statusBar"]);
        }
        shot(prefix + "-correlations", "analysis", "Inspect correlations for the selected measurement",
            ["appBar.tab.analysis", "mainArea.analysis.tab.correlations"], ["workflow.analysis.mainContent"]);
        return steps;
    }};
})();
