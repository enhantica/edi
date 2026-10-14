// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    name: "ReportCorrelationTies"
    when: windowShown
    function cleanup() {
        Session.closeProject();
    }
    function test_count_threshold_ties_restore_the_same_project_filter_data() {
        return [
            {
                tag: "pairs-auto",
                graph: "pairs",
                count: -1,
                level: 0.95,
                names: ["P1", "P2", "P3", "P4"]
            },
            {
                tag: "pairs-five",
                graph: "pairs",
                count: 5,
                level: 0.95,
                names: ["P1", "P2", "P3", "P4"]
            },
            {
                tag: "pairs-two",
                graph: "pairs",
                count: 2,
                level: 0.99,
                names: ["P1", "P2"]
            },
            {
                tag: "pairs-one",
                graph: "pairs",
                count: 1,
                level: 0.99,
                names: ["P1", "P2"]
            },
            {
                tag: "clique-two",
                graph: "clique",
                count: 2,
                level: 0.9,
                names: ["A", "B", "C"]
            }
        ];
    }
    function names(model) {
        return model.labels.map(name => name.split(".").slice(-2)[0]);
    }
    function test_count_threshold_ties_restore_the_same_project_filter(data) {
        const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_options/" + data.graph));
        verify(String(url) !== "" && Session.openProject(url), "The independently declared pair-strength or clique fixture opens as a real fitted project");
        const filter = Session.project.correlations;
        compare(filter.available, data.graph === "pairs" ? 6 : 4, "The tie gate reaches every declared correlated parameter before testing selection");
        if (data.count >= 0)
            filter.maxParameters = data.count;
        compare(JSON.stringify(names(filter)), JSON.stringify(data.names), "The tab's shared count-to-threshold rule keeps complete boundary ties in fit order");
        fuzzyCompare(filter.level, data.level, 1e-14, "The shared filter chooses the independently derived coefficient threshold");
        compare(filter.maxParameters, data.names.length, "The count field shows the actual tie-preserving number kept");
        if (data.count >= 0) {
            compare(Session.project.modified, true, "A count edit writes its project-owned threshold through an undoable edit");
            verify(Session.save(), "The actual project writer saves the selected correlation threshold");
            const text = SettingsProof.text(url, "analysis/analysis.edi");
            const item = text.match(/^_correlation_chart\.threshold\s+(\S+)/m);
            verify(item !== null, "Only the correlation threshold is persisted in the Analysis correlation-chart category");
            fuzzyCompare(Number(item[1]), data.level, 1e-14, "The saved item holds the independently derived threshold");
            verify(!/^_correlation_chart\.(?:count|max_parameters)\s/m.test(text), "The derived count is never serialized as another project option");
            Session.closeProject();
            verify(Session.openProject(url), "The threshold restores through the actual project reader");
            compare(JSON.stringify(names(Session.project.correlations)), JSON.stringify(data.names), "Reopening restores exactly the same parameters and complete ties in the live tab");
        }
    }
}
