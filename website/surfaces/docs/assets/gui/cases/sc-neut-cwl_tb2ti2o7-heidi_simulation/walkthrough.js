// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of sc-neut-cwl_tb2ti2o7-heidi_simulation, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "sc-neut-cwl_tb2ti2o7-heidi_simulation";
    const STEPS = [
 {
  "id": "home",
  "page": "home",
  "description": "Start a new analysis",
  "actions": [
   "platform:light",
   "theme:light"
  ],
  "highlights": [
   "home.start"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "example-open",
  "page": "project",
  "description": "Open the example from Examples",
  "actions": [
   "home.start",
   "sideBar.tab.basic",
   "reveal:group.examples",
   "expand:group.examples",
   "reveal:examples.search",
   "fill:examples.search=sc-neut-cwl_tb2ti2o7-heidi_simulation",
   "reveal:examples.open.sc-neut-cwl_tb2ti2o7-heidi_simulation",
   "examples.open.sc-neut-cwl_tb2ti2o7-heidi_simulation",
   "pin-time:01 Jan 2026 12:00:00"
  ],
  "highlights": [
   "workflow.project.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "calculated",
  "page": "analysis",
  "description": "See the calculated pattern",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "mainArea.tab.pattern"
  ],
  "highlights": [
   "workflow.analysis.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "report",
  "page": "report",
  "description": "Review the report",
  "actions": [
   "appBar.tab.report",
   "sideBar.tab.basic"
  ],
  "highlights": [
   "workflow.report.mainContent"
  ],
  "sidebar": "Main",
  "capture": true
 }
];
    return {schema: 2, workflow: "tutorial", example: EXAMPLE_ID, build: function (capture) {
        return STEPS.map(function (step) {
            const actions = step.actions.map(function (action) {
                return action.replace("@title", capture.title)
                    .replace("@projectDirectory", capture.projectDirectory);
            });
            return Object.assign({}, step, {actions: actions});
        });
    }};
})();
