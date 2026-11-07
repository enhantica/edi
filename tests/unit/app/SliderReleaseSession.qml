// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

ExperimentWorkflowSession {
    SignalSpy { id: texts; target: Session.project ? Session.project.projectText : null; signalName: "inputTextChanged" }
    SignalSpy { id: experimentTexts; target: Session.project && Session.project.currentExperiment ? Session.project.currentExperiment.text : null; signalName: "inputTextChanged" }
    SignalSpy { id: reports; target: Session.project ? Session.project.reportText : null; signalName: "textChanged" }
    SignalSpy { id: edits; target: Session.project; signalName: "projectEdited" }
    SignalSpy { id: curves; target: Session.project; signalName: "recalculated" }
    function dragSetup() {
        resetProject(false);
        const project = Session.project;
        verify(project.loadStructure(fixture({file:"easydiffraction/structures/lbco.cif"})), "Drag gates use the independently saved LBCO structure");
        verify(project.loadExperiments([fixture({file:"easydiffraction/experiments/lbco_hrpt.edi"})]), "Drag gates use an independently saved measured experiment");
        tryVerify(() => !project.calculating, 10000, "The reference calculation settles before the adjustment begins");
        settle();
        return project;
    }
    function check_deferred_data() { return ["cell", "wavelength", "profile"].map(tag => ({tag:tag})); }
    function check_deferred(data) {
        const project = dragSetup();
        const parameter = data.tag === "cell" ? project.currentStructure.cell.lengthA :
                          data.tag === "wavelength" ? project.currentExperiment.instrument.parameterNamed("setup_wavelength") :
                          project.currentExperiment.peak.parameterNamed("broad_gauss_u");
        verify(parameter !== null && parameter !== undefined, "Each category adjustment reaches its actual public parameter");
        const before = parameter.value;
        const beforeInput = project.currentExperiment.text.inputText;
        texts.clear(); experimentTexts.clear(); reports.clear(); edits.clear(); curves.clear();
        project.adjusting = true;
        try {
            for (const factor of [1.01, 1.02, 1.03]) {
                const oldCurveCount = curves.count;
                parameter.value = before * factor + (data.tag === "profile" ? 0.01 : 0);
                tryVerify(() => curves.count > oldCurveCount && !project.calculating, 10000, "Every held step publishes a fresh calculated curve before release");
                compare(texts.count + experimentTexts.count, 0, "Project and experiment input spelling wait throughout the held adjustment");
                compare(reports.count, 0, "Report generation waits throughout the held adjustment");
                compare(edits.count, 0, "Save and assistant project-edit publication wait throughout the held adjustment");
            }
        } finally { project.adjusting = false; }
        const finalValue = parameter.value;
        verify(finalValue !== before, "The deferred publication witness ends at a changed numerical value");
        tryVerify(() => edits.count === 1, 5000, "Exactly one full project-edit publication occurs when the adjustment ends");
        verify(texts.count <= 1 && reports.count <= 1, "Release derives project and report texts at most once");
        project.undo();
        compare(parameter.value, before, "One Undo restores the value before the entire held adjustment");
        compare(project.currentExperiment.text.inputText, beforeInput, "Undo restores the prior persisted experiment inputs");
    }
    function check_real_slider() {
        const project = dragSetup();
        AppState.open(AppState.Page.Analysis);
        settle();
        const parameters = pageControl("group.parameters");
        if (parameters.collapsed) click(parameters.titleArea);
        const slider = pageControl("parameters.slider");
        const group = pageControl("group.parameters");
        const parameter = group.selected;
        verify(parameter !== null && slider.enabled, "The actual Analysis slider has an editable selected parameter");
        const before = parameter.value;
        const x = slider.leftPadding + slider.availableWidth * slider.visualPosition;
        texts.clear(); edits.clear();
        mousePress(slider, x, slider.height/2);
        try {
            verify(project.adjusting, "Pressing the actual slider enters the shared adjustment boundary");
            for (const fraction of [0.4, 0.55, 0.65]) {
                mouseMove(slider, slider.leftPadding + slider.availableWidth*fraction, slider.height/2);
                tryVerify(() => !project.calculating, 10000, "The real held slider lets its calculation complete");
                compare(edits.count, 0, "Pointer-held movement does not publish save or assistant context work");
            }
        } finally { mouseRelease(slider, slider.leftPadding + slider.availableWidth*0.65, slider.height/2); }
        verify(!project.adjusting, "Releasing the actual slider closes the shared adjustment boundary");
        verify(parameter.value !== before, "The pointer drag changes the actual selected parameter");
        project.undo();
        compare(parameter.value, before, "One actual pointer drag is exactly one undoable change");
    }
}
