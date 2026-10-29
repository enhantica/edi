import QtQuick
import QtTest
import SaveNumericAcceptance 1.0

// C++ exercises FIRST formatter, normal native Open/SaveAs/Save and real files.
// QML carries no formatter, expected number, native state or alternative writer.
TestCase {
    name: "E11T5SaveNumericFixedPoint"
    when: windowShown
    function test_numeric_pair_fixed_point() {
        const result=SaveNumericProof.pairFixedPoint();
        verify(result.ok, "Native serialization must stabilize value and SU meaning after parse: " + (result.error || ""));
    }
    function test_ordinary_save_current_disk_text_and_calculation_agree() {
        const result=SaveNumericProof.ordinarySaveAgreement();
        verify(result.ok, "Successful ordinary SaveAs/Save must agree with current values, literal disk, Text, file spelling and native recalculation: " + (result.error || ""));
    }
}
