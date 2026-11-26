// SPDX-License-Identifier: BSD-3-Clause
import QtCore
import QtQuick
import QtTest

import edi.app

// A scan's extraction rules are edited in their table as the constraints are: text, required, append, duplicate and
// remove, each one Undo step; a bad pattern or a target another column has is refused in its cell; the rules are saved
// and read back, and the first one can be made in a scan that has none.
Item {
    id: root

    width: 600
    height: 500

    readonly property url cosio: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project")
    readonly property url latp: Qt.resolvedUrl("../../../docs/user/cli/pd-xray-cwl_latp_scan-4f/project")
    readonly property url magnetic: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-213f/project")

    SequentialExtractGroup {
        id: group
        width: root.width
        analysis: Session.project ? Session.project.analysis : null
    }

    TestCase {
        id: test

        name: "ScanExtractionRules"
        when: windowShown

        readonly property var rules: group.rules
        // As the charts and the Experiments table follow it.
        readonly property int columns: Session.project ? Session.project.scanColumns.length : -1

        function open(project) {
            verify(Session.openProject(project), Session.lastError);
            wait(300);
        }
        function cleanup() {
            Session.closeProject();
        }
        // The shown dataset is read again after an edit of the declaration, and an edit meanwhile is refused.
        function edits(row, role, text) {
            tryVerify(() => rules.setText(row, role, text), 10000, role);
            compare(rules.text(row, role), text);
        }
        function undoes(row, role, text) {
            tryVerify(() => {
                if (rules.text(row, role) !== text)
                    Session.project.undo();
                return rules.text(row, role) === text;
            }, 10000, "undo of " + role);
        }
        function refuses(row, role, text, why) {
            const before = rules.text(row, role);
            tryVerify(() => {
                rules.setText(row, role, text);
                return Session.project.lastError.indexOf(why) >= 0;
            }, 10000, `${text}: ${Session.project.lastError}`);
            compare(rules.text(row, role), before);
        }
        function counts(n, change) {
            tryVerify(() => {
                if (rules.count !== n)
                    change();
                return rules.count === n;
            }, 10000);
        }
        // Types over a cell's text and presses Return.
        function type(cell, text) {
            cell.forceActiveFocus();
            cell.selectAll();
            cell.remove(0, cell.length);
            for (const letter of text)
                keyClick(letter);
            keyClick(Qt.Key_Return);
        }

        function test_a_each_cell_is_an_edit_with_its_undo() {
            open(root.cosio);
            compare(rules.count, 1);
            compare(Session.project.canUndo, false);
            edits(0, "pattern", "^TEMP\\s+([0-9]+)");
            undoes(0, "pattern", "^TEMP\\s+([0-9.]+)");
            edits(0, "target", "diffrn.other");
            undoes(0, "target", "diffrn.ambient_temperature");
            edits(0, "id", "warmth");
            undoes(0, "id", "temperature");
            tryVerify(() => rules.setRequired(0, false), 10000);
            compare(rules.text(0, "required"), "false");
            undoes(0, "required", "true");
            tryCompare(Session.project, "canUndo", false);
        }
        function test_b_typed_in_the_cell() {
            open(root.cosio);
            const pattern = findChild(group, "sequentialExtract.pattern.0");
            verify(pattern !== null);
            wait(500);
            type(pattern, "(x");
            tryVerify(() => pattern.refusal.indexOf("regular expression") >= 0, 5000, pattern.refusal);
            compare(rules.text(0, "pattern"), "^TEMP\\s+([0-9.]+)");
            compare(pattern.text, "^TEMP\\s+([0-9.]+)");
            type(pattern, "TEMP([0-9]+)");
            tryVerify(() => rules.text(0, "pattern") === "TEMP([0-9]+)", 5000);
            compare(pattern.refusal, "");
        }
        function test_c_what_is_refused() {
            open(root.cosio);
            refuses(0, "pattern", "", "needs a pattern");
            refuses(0, "pattern", "^TEMP", "no group");
            refuses(0, "pattern", "TEMP ([0-9]+)", "space");
            refuses(0, "pattern", "[0-9]+(K)", "project file");
            refuses(0, "target", "", "needs a target");
            refuses(0, "target", "a,b", "comma");
            refuses(0, "target", "fit_result.success", "already");
            refuses(0, "target", "cosio.cell.length_a", "writes itself");
            compare(Session.project.canUndo, false);
        }
        // Columns the fit writes itself, now or after a later edit (a moment on a site that has none, a phase not linked yet,
        // a datablock not added yet): every such name has three dotted parts or more.
        function test_c_the_fit_s_own_column_names_are_refused() {
            open(root.magnetic);
            const reserved = ["cosio.atom_site_moment.Co1.spherical_modulus", "cosio.atom_site_moment.Co2.spherical_polar.uncertainty", "linked_structure.cosio.weight_fraction", "linked_structure.cosio.weight_fraction.uncertainty", "cosio.atom_site_moment.Co3.spherical_modulus", "linked_structure.later.weight_fraction", "later.cell.length_a"];
            for (const target of reserved)
                refuses(0, "target", target, "writes itself");
            counts(2, () => findChild(group, "sequentialExtract.append").clicked());
            for (const target of reserved)
                refuses(1, "target", target, "writes itself");
            edits(1, "target", "diffrn.pressure");
            edits(0, "target", "sample_temperature");
        }
        function test_d_rows_are_added_copied_and_removed() {
            open(root.cosio);
            counts(2, () => findChild(group, "sequentialExtract.append").clicked());
            compare(rules.text(1, "target"), rules.text(1, "id"));
            counts(3, () => findChild(group, "sequentialExtract.duplicate").clicked());
            verify(rules.text(2, "target") !== rules.text(0, "target"));
            refuses(2, "target", rules.text(0, "target"), "already");
            refuses(2, "id", "temperature", "already has that id");
            counts(2, () => rules.remove(0));
            compare(rules.text(0, "target").indexOf("diffrn"), -1);
            counts(3, () => Session.project.undo());
            compare(rules.text(0, "id"), "temperature");
        }
        // A copy's target comes from the source's target, two parts at most, whatever the rule's id holds.
        function test_d_a_dotted_id_is_duplicated() {
            open(root.cosio);
            edits(0, "id", "sample.run.temperature");
            counts(2, () => findChild(group, "sequentialExtract.duplicate").clicked());
            compare(rules.text(1, "target"), "diffrn.ambient_temperature_1");
            verify(rules.text(1, "id") !== rules.text(0, "id"));
        }
        function test_e_saved_and_read_back() {
            open(root.cosio);
            edits(0, "pattern", "^TEMP\\s+([0-9]+)");
            tryVerify(() => rules.setRequired(0, false), 10000);
            const row = "temperature diffrn.ambient_temperature ^TEMP\\s+([0-9]+) false";
            verify(Session.project.analysis.text.text.indexOf(row) > 0, Session.project.analysis.text.text);
            const folder = StandardPaths.writableLocation(StandardPaths.TempLocation) + `/edi-extraction-rules-${Date.now()}`;
            tryVerify(() => Session.saveAs(folder), 20000, Session.lastError);
            Session.closeProject();
            open(folder);
            compare(rules.count, 1);
            compare(rules.text(0, "pattern"), "^TEMP\\s+([0-9]+)");
            compare(rules.text(0, "required"), "false");
        }
        function test_f_the_first_rule_of_a_scan() {
            open(root.latp);
            compare(rules.count, 0);
            const ids = [];
            const categories = Session.project.analysis.categories;
            for (let i = 0; i < categories.rowCount(); ++i)
                for (let role = Qt.UserRole; role < Qt.UserRole + 12; ++role)
                    ids.push(categories.data(categories.index(i, 0), role));
            verify(ids.indexOf("sequential_fit_extract") >= 0, "the category is shown without a rule");
            counts(1, () => findChild(group, "sequentialExtract.append").clicked());
            compare(rules.text(0, "target"), "diffrn.ambient_temperature");
            compare(rules.text(0, "required"), "false");
            compare(columns, 1);
            counts(0, () => Session.project.undo());
            compare(columns, 0);
        }
        // Another rule is another template: results fitted before it are out of date, and the shown dataset stays out of
        // the template.
        function test_g_the_shown_dataset_stays_out_of_the_template() {
            open(root.cosio);
            const project = Session.project;
            project.currentExperimentIndex = 2;
            tryVerify(() => project.currentExperimentIndex === 2 && project.templateIndex !== 2, 10000);
            const template = project.templateIndex;
            edits(0, "pattern", "^TEMP\\s+([0-9]+)");
            compare(project.templateIndex, template);
            verify(project.analysis.text.text.indexOf("([0-9]+)") > 0);
        }
    }
}
