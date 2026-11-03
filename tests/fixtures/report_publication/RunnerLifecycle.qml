// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import ReportBoundaryAcceptance 1.0

TestCase {
    name: "ReportRunnerCleanup"
    when: windowShown
    function test_exit_data() {
        return [{tag: "success", fail: false}, {tag: "failure", fail: true}];
    }
    function test_exit(data) {
        const files = BoundaryProof.inventory(Qt.resolvedUrl("."));
        const libraries = Object.keys(files).filter(name => /^edi-report-faults-[^/]+\/faults\.so$/.test(name));
        verify(libraries.length === 1, "The lifecycle witness reaches one actual compiled preload library before exit");
        console.log("REPORT_FAULTS_LIVE " + JSON.stringify(libraries));
        verify(!data.fail, "The failing-exit lifecycle control intentionally returns a failed Qt Test result");
    }
}
