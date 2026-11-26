// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Item {
    id: host
    width: 1100
    height: 700
    Component { id: chartFactory; EvolutionChart { shown: true } }

    TestCase {
        name: "EvolutionParameterGroups"
        when: windowShown

        function cleanup() { Session.closeProject(); }

        function test_group_headings_and_selection() {
            const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_evolution/project"));
            const file = "analysis/results.csv";
            const rows = SettingsProof.text(root, file).trim().split(/\r?\n/);
            const cell = "phase.cell.length_a";
            const weight = "bank.linked_structure.phase.weight_fraction";
            rows[0] = rows[0].split(",").slice(0, 7).join(",")
                + `,${cell},${cell}.uncertainty,${weight},${weight}.uncertainty,fit_result.r_wp`;
            for (let row = 1; row < rows.length; ++row)
                rows[row] = rows[row].split(",").slice(0, 7).join(",")
                    + `,4.${row},0.01,0.${row + 3},0.02,0.0${row + 4}`;
            const experimentFile = "experiments/bank.edi";
            const experiment = SettingsProof.text(root, experimentFile).replace(/^(P[2-6] .*)\(\)$/gm, "$1");
            verify(SettingsProof.write(root, experimentFile, experiment),
                   "Keep the public scan fixture's first free background term for a short selector");
            verify(SettingsProof.write(root, file, rows.join("\n") + "\n"),
                   "Plant independently chosen cell, derived and fit-quality results in the scan");
            verify(Session.openProject(root), "Open a real saved scan with results in the Evolution chart");
            const project = Session.project;
            const chart = createTemporaryObject(chartFactory, host, {project, width: host.width, height: host.height});
            verify(chart !== null, "The production Evolution chart must be loaded");
            const selector = findChild(chart, "evolution.parameters.box");
            verify(selector !== null, "The real Evolution parameter selector is present");
            tryVerify(() => selector.enabled && selector.count >= 4, 5000,
                      "The selector offers datablock parameters, derived values and fit-quality results");
            for (const rawName of ["bank.background.P1.intensity", "phase.cell.length_a",
                                   "bank.linked_structure.phase.weight_fraction", "fit_result.r_wp"])
                verify(Array.from({length: project.evolution.parameters.count},
                                  (_, index) => project.evolution.parameters.text(index, "name")).includes(rawName),
                       "The project fixture contributes the saved Evolution series " + rawName);
            mouseClick(selector);
            tryCompare(selector.popup, "opened", true, 2000, "Clicking the parameter selector opens its real list");
            const labels = Render.texts(selector.popup.contentItem).map(item => item.text);
            const bank = labels.findIndex(text => /^bank$/i.test(text.trim()));
            const phase = labels.findIndex(text => /^phase$/i.test(text.trim()));
            const derived = labels.findIndex(text => /^derived(?: values)?$/i.test(text.trim()));
            const quality = labels.findIndex(text => /^fit quality(?: values)?$/i.test(text.trim()));
            verify(bank >= 0 && phase >= 0 && bank < derived && phase < derived && derived < quality,
                   "Evolution needs a visible heading per datablock followed by Derived values and Fit quality: " + JSON.stringify(labels));
            verify(labels.some(text => /weight fraction/i.test(text)) && !labels.includes("weight_fraction"),
                   "The derived weight fraction has a human label in its group");
            const item = Render.descendants(selector.popup.contentItem).find(candidate =>
                candidate.visible && candidate.enabled && typeof candidate.clicked === "function"
                && typeof candidate.index === "number"
                && Render.texts(candidate).some(label => /weight fraction/i.test(label.text)));
            verify(item !== undefined, "The human-labelled derived column remains selectable");
            mouseClick(item);
            tryCompare(project.evolution, "yTitle", "bank.linked_structure.phase.weight_fraction", 2000,
                       "The selected row still draws the saved column after adding headings");
        }
    }
}
