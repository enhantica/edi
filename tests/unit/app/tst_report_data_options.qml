// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Rectangle {
    width: 1200
    height: 900
    Component {
        id: pageFactory
        ReportPage {}
    }
    TestCase {
        name: "ReportDataOptions"
        when: windowShown
        function cleanup() {
            Session.closeProject();
        }
        function test_optional_groups_and_data_defaults_data() {
            return [
                {
                    tag: "absent",
                    empty: false
                },
                {
                    tag: "explicit-empty",
                    empty: true
                }
            ];
        }
        function test_optional_groups_and_data_defaults(data) {
            const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            if (data.empty)
                verify(SettingsProof.write(url, "project.edi", SettingsProof.text(url, "project.edi") + "\n_report.excluded ''\n"), "The explicit-empty witness declares include-all independently of the absent default");
            verify(Session.openProject(url), "The Data option witness opens a real project through Session");
            tryCompare(Session.project, "calculating", false, 10000, "The Data option witness finishes loading its experiment");
            const page = createTemporaryObject(pageFactory, parent, {
                width: 1200,
                height: 900,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page lays out its optional groups");
            const group = findChild(page, "group.reportContents");
            verify(group !== null, "The actual Contents group exists in the Report sidebar");
            group.collapsed = false;
            verify(waitForPolish(group), "The Contents boxes are laid out before pointer input");
            const expected = ["Charts", "Correlations", "Reflections", "Data"];
            const boxes = Render.descendants(group).filter(item => typeof item.checked === "boolean" && expected.includes(item.text));
            compare(JSON.stringify(boxes.map(item => item.text).sort()), JSON.stringify(expected.slice().sort()), "Single-project Contents is the flat list of four optional groups, including Data");
            verify(!Render.texts(group).some(item => item.text === "Measured data"), "The old Measured data label is replaced by Data");
            const box = boxes.find(item => item.text === "Data");
            compare(box.checked, data.empty, "Data is omitted for an absent excluded item and included for an explicit empty item");
            for (const other of boxes.filter(item => item !== box))
                compare(other.checked, true, "Every other optional group stays included by default");
            mouseClick(box, box.width / 2, box.height / 2);
            tryCompare(box, "checked", !data.empty, 1000, "The Data group accepts actual pointer input");
            compare(Session.project.modified, true, "Changing Data is an undoable project-owned report edit");
            verify(Session.save(), "The actual project writer saves the new Data inclusion choice");
            const text = SettingsProof.text(url, "project.edi");
            const match = text.match(/^_report\.excluded\s+([^\n]*)/m);
            verify(match !== null, "A user-edited Data choice is persisted as an explicit report exclusion item");
            const token = match[1].trim().replace(/^(['"])(.*)\1$/, "$2");
            compare(token, data.empty ? "data" : "", "The writer preserves the final data key or an explicit empty include-all value");
            Session.project.undo();
            tryCompare(box, "checked", data.empty, 1000, "Undo restores the original Data checkbox state");
            Session.closeProject();
            verify(Session.openProject(url), "The saved Data choice reopens through the real reader");
            const contents = Session.project.report.model.contents;
            const restored = contents.find(item => item.key === "data");
            verify(restored !== undefined, "The reloaded report retains the Data optional group");
            compare(restored.included, !data.empty, "The saved Data choice restores identically in the preview model");
        }
    }
}
