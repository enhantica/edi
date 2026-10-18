import QtQuick
import QtTest
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0

Item {
    TestCase {
        name: "ScanTemporaryAliases"
        function test_all_scan_file_helpers_detach_temporary_entries_data() {
            const cases = [];
            for (const route of ["writeRun", "putFiles", "putRunFile", "swapRunFile", "takeFiles", "restoreRunFile", "dropRunFile", "removeRunFile"])
                for (const alias of ["symbolic", "hard", "carried", "none"])
                    for (const linked of [false, true])
                        for (const late of (["restoreRunFile", "dropRunFile", "removeRunFile"].includes(route) ? [false] : [false, true]))
                            for (const which of (route === "putFiles" || route === "takeFiles" ? [0, 1, 2, 3] : [2]))
                                cases.push({
                                    tag: [route, alias, linked, late, which].join("-"),
                                    route,
                                    alias,
                                    linked,
                                    late,
                                    which
                                });
            return cases;
        }
        function test_all_scan_file_helpers_detach_temporary_entries(data) {
            const location = SettingsProof.emptyDirectory(), outside = SettingsProof.emptyDirectory();
            const facts = BoundaryProof.scanTemporary(location, outside, data.route, data.alias, data.linked, data.which, data.late);
            verify(facts.setupError === undefined, "The independent scan alias fixture reaches the actual helper: " + facts.setupError);
            compare(JSON.stringify(facts.after), JSON.stringify(facts.before), "Every scan writer preserves outside inode bytes, including aliases created while detaching a linked analysis folder");
            verify(facts.kept, "A failed restore preserves every file already retained by takeFiles");
            verify(facts.carried, "All scan take, restore, swap, drop and write helpers preserve carried artifacts");
            if (data.late) {
                verify(facts.receipt, "The late scan refusal reaches a real rename after writing its temporary output");
                verify(facts.refusal.length > 0, "The scan helper reports the actual later publication failure");
                compare(JSON.stringify(facts.publishedAfter), JSON.stringify(facts.publishedBefore), "A failed scan publication preserves all previously published file bytes");
            } else if (data.alias === "none")
                compare(facts.refusal, "", "The same scan helper succeeds with an unaliased temporary entry");
        }
    }
}
