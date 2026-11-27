// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtCore
import QtTest

import edi.app

// A typed wavelength the calculation cannot hold is refused at its field before it is written: the project keeps the
// value before it, no Undo step is made and no calculation is started.
TestCase {
    id: test

    name: "TypedWavelength"

    readonly property string examples: "../../../docs/user/cli/"
    readonly property string refusal: "The calculation cannot hold this wavelength: "

    function open(example) {
        verify(Session.openProject(Qt.resolvedUrl(examples + example + "/project")), Session.lastError);
        tryVerify(() => !Session.project.calculating, 30000);
        const item = Session.project.currentExperiment.instrument.parameterNamed("setup_wavelength");
        verify(item !== null);
        compare(item.lastError, "");
        return item;
    }
    function cleanup() {
        Session.closeProject();
    }
    function refused(item, typed, before) {
        item.value = typed;
        verify(item.lastError.startsWith(refusal), item.lastError);
        compare(item.value, before);
        compare(Session.project.calculating, false, "nothing was written, so nothing is calculated");
    }

    function test_zero_and_below_are_refused_before_they_are_written() {
        const item = open("pd-neut-cwl_lbco-hrpt");
        const before = item.value;
        for (const typed of [0, -1.5]) {
            item.value = typed;
            compare(item.lastError, "A wavelength must be above 0 Å");
            compare(item.value, before);
            verify(!Session.project.canUndo);
        }
        item.value = 1.5;
        compare(item.lastError, "");
        compare(item.value, 1.5);
        tryVerify(() => !Session.project.calculating, 30000);
        compare(item.value, 1.5, "a wavelength the calculation holds stays");
    }

    function test_the_second_wavelength_may_be_zero() {
        open("pd-xray-cwl_pbso4-lab");
        const second = Session.project.currentExperiment.instrument.parameterNamed("setup_wavelength_2");
        verify(second !== null);
        const original = second.value;
        verify(original > 0);
        second.value = 0;
        compare(second.lastError, "");
        compare(second.value, 0);
        tryVerify(() => !Session.project.calculating, 30000);
        compare(second.value, 0);
        second.value = original * 1.001;
        compare(second.lastError, "");
        fuzzyCompare(second.value, original * 1.001, 1e-12);
        tryVerify(() => !Session.project.calculating, 30000);
    }

    // The simulation lists reflections up to sin(theta)/lambda 0.95, which a wavelength above 1/0.95 Å cannot reach.
    function test_a_refused_value_is_refused_at_once_and_saves_work() {
        const item = open("sc-neut-cwl_tb2ti2o7-heidi_simulation");
        const before = item.value;
        refused(item, 5, before);
        verify(item.lastError.indexOf("beyond the reach of the wavelength") >= 0, item.lastError);
        verify(!Session.project.canUndo);
        const folder = StandardPaths.writableLocation(StandardPaths.TempLocation) + `/edi-typed-wavelength-${Date.now()}`;
        verify(Session.saveAs(folder), Session.lastError);
        compare(item.value, before);
    }

    function test_a_later_edit_and_its_undo_leave_no_refused_value() {
        const item = open("sc-neut-cwl_tb2ti2o7-heidi_simulation");
        const before = item.value;
        const cell = Session.project.parameterNamed("tb2ti2o7.cell.length_a");
        verify(cell !== null);
        const cellBefore = cell.value;
        refused(item, 5, before);
        cell.value = cellBefore * 1.001;
        compare(cell.lastError, "");
        fuzzyCompare(cell.value, cellBefore * 1.001, 1e-12);
        compare(item.value, before);
        tryVerify(() => !Session.project.calculating, 30000);
        verify(Session.project.canUndo);
        Session.project.undo();
        tryCompare(Session.project, "canUndo", false);
        fuzzyCompare(cell.value, cellBefore, 1e-12);
        compare(item.value, before);
        tryVerify(() => !Session.project.calculating, 30000);
        compare(item.value, before);
    }

    function test_two_typed_values_in_a_row() {
        const item = open("sc-neut-cwl_tb2ti2o7-heidi_simulation");
        const before = item.value;
        refused(item, 5, before);
        item.value = 1.0;
        compare(item.lastError, "");
        compare(item.value, 1.0);
        tryVerify(() => !Session.project.calculating, 30000);
        refused(item, 3, 1.0);
        tryVerify(() => !Session.project.calculating, 30000);
        compare(item.value, 1.0);
        Session.project.undo();
        tryCompare(Session.project, "canUndo", false);
        compare(item.value, before, "the one Undo step is the accepted value's");
    }
}
