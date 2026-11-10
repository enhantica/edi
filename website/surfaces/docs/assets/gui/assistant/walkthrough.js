// SPDX-License-Identifier: BSD-3-Clause
// The Application's AI assistant tutorial on La0.5Ba0.5CoO3 HRPT: the built-in assistant gets the
// collection's tutorial-lbco.cif and tutorial-hrpt.xye and is asked to fit the crystal structure.
// tools/docs/capture_assistant.sh copies the two files to INPUTS before the run. Show actions stays off.
(function () {
    const INPUTS = "/tmp/edi-assistant-tutorial/";
    function shot(id, page, description, actions, highlights) {
        return {id: id, page: page, description: description, actions: actions,
            highlights: highlights || [], sidebar: "", capture: true};
    }
    return {schema: 2, workflow: "tutorial", example: "pd-neut-cwl_lbco-hrpt", build: function (capture) {
        return [
            shot("assistant-panel", "project", "Open the assistant from the toolbar",
                ["platform:light", "theme:light", "home.start", "assistant.toggle"], ["assistant.connection"]),
            shot("assistant-connect", "project", "Connect ChatGPT", ["assistant.connection"], []),
            shot("assistant-ready", "project", "The assistant is connected; Show actions is off",
                ["choose:Connect ChatGPT", "wait-assistant"], ["assistant.showActions"]),
            shot("assistant-ask", "project", "Attach the two files and ask for the fit",
                ["assistant-attach:" + INPUTS + "tutorial-lbco.cif|" + INPUTS + "tutorial-hrpt.xye",
                 "fill:assistant.composer=Fit the crystal structure to this measured pattern."],
                ["assistant.composer"]),
            shot("assistant-approve", "project", "Approve sharing the project information and the files",
                ["assistant.send"], []),
            shot("assistant-question", "auto", "The assistant asks what the files do not say",
                ["choose:Share project information", "wait-assistant"], ["assistant.messages"]),
            shot("assistant-fitted", "auto", "Answer, and the assistant fits the structure",
                ["fill:assistant.composer=Neutrons, constant wavelength, measured on HRPT at PSI. The wavelength is 1.494 Å.",
                 "assistant.send", "wait-assistant"], ["assistant.messages"]),
            shot("assistant-result", "analysis", "The fitted pattern on Analysis",
                ["appBar.tab.analysis", "sideBar.tab.basic"], ["workflow.analysis.mainContent"]),
        ];
    }};
})();
