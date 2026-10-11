// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import TableIdTests 1.0

Item {
    width: 1000
    height: 900
    TableIdFiles {
        id: files
    }
    TestCase {
        name: "StoredTableIds"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
        }
        function cleanup() {
            Session.closeProject();
        }
        function test_background_identity_delete_and_roundtrip() {
            let points = Session.project.currentExperiment.background;
            verify(points.count >= 2);
            const position = Number(points.text(0, "position"));
            verify(points.setId(0, 'low "angle"'), Session.project.lastError);
            verify(points.setId(1, "high angle"), Session.project.lastError);
            verify(!points.setId(1, 'low "angle"'));
            compare(points.text(1, "id"), "high angle");
            verify(!points.setId(0, ""));
            compare(points.text(0, "id"), 'low "angle"');
            const count = points.count;
            points.remove(1);
            compare(points.count, count - 1);
            compare(points.text(0, "id"), 'low "angle"');
            verify(Session.saveAs(files.directory()), Session.lastError);
            verify(Session.openProject(files.directory()), Session.lastError);
            points = Session.project.currentExperiment.background;
            compare(points.text(0, "id"), 'low "angle"');
            compare(points.count, count - 1);
            compare(Number(points.text(0, "position")), position);
        }
        function test_exclusion_identity_bounds_delete_and_roundtrip() {
            let regions = Session.project.currentExperiment.excludedRegions;
            const before = regions.count;
            regions.append();
            regions.append();
            verify(regions.setId(before, "left edge"));
            verify(regions.setId(before + 1, "right"));
            verify(regions.setStart(before, 15));
            verify(regions.setEnd(before, 12));
            verify(!regions.setId(before + 1, "left edge"));
            verify(!regions.setId(before, ""));
            regions.remove(before + 1);
            compare(regions.count, before + 1);
            compare(regions.text(before, "id"), "left edge");
            verify(Session.saveAs(files.directory()), Session.lastError);
            verify(Session.openProject(files.directory()), Session.lastError);
            regions = Session.project.currentExperiment.excludedRegions;
            compare(regions.text(before, "id"), "left edge");
            compare(regions.count, before + 1);
            compare(Number(regions.text(before, "start")), 15);
            compare(Number(regions.text(before, "end")), 12);
        }
    }
}
